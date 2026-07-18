#!/usr/bin/env bash
# Gather last week's merged work into a digest for the release-notes LLM.
#
# Walks: merged PRs -> closingIssuesReferences -> native sub-issue parent
# (the PRD issue), deduping parents. PRs with no linked issues contribute
# their body alone. Falls back to raw commits when no PRs merged; skips
# the release entirely when there are neither.
#
# Env:   GITHUB_TOKEN (required), GH_REPO (owner/repo), WINDOW_DAYS (default 7),
#        DEFAULT_BRANCH (default main), OUT_DIR (default out)
# Writes: $OUT_DIR/context.md
# Outputs (GITHUB_OUTPUT): skip=true|false, mode=prs|commits, tag=vYYYY.MM.DD

set -euo pipefail

REPO="${GH_REPO:?GH_REPO required (owner/repo)}"
WINDOW_DAYS="${WINDOW_DAYS:-7}"
DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"
OUT_DIR="${OUT_DIR:-out}"
GITHUB_OUTPUT="${GITHUB_OUTPUT:-/dev/null}"

PR_BODY_LIMIT=2000
PARENT_BODY_LIMIT=3000

mkdir -p "$OUT_DIR"
CONTEXT="$OUT_DIR/context.md"

# GNU date (CI) with BSD/macOS fallback for local runs outside a container.
SINCE_DATE=$(date -u -d "-${WINDOW_DAYS} days" +%Y-%m-%d 2>/dev/null || date -u -v-"${WINDOW_DAYS}"d +%Y-%m-%d)
SINCE_ISO="${SINCE_DATE}T00:00:00Z"
TAG="v$(date -u +%Y.%m.%d)"

# Human-readable window label for release/post titles, e.g. "Jul 4 – Jul 18, 2026"
fmt_day() { { date -u -d "$1" "+%b %d" 2>/dev/null || date -ju -f %Y-%m-%d "$1" "+%b %d"; } | sed 's/ 0/ /'; }
RANGE="$(fmt_day "$SINCE_DATE") – $(date -u "+%b %d, %Y" | sed 's/ 0/ /')"

echo "tag=$TAG" >> "$GITHUB_OUTPUT"
echo "range=$RANGE" >> "$GITHUB_OUTPUT"

prs=$(gh pr list --repo "$REPO" --state merged \
  --search "merged:>=$SINCE_DATE base:$DEFAULT_BRANCH" \
  --json number,title,url,body,mergedAt,author --limit 100)

pr_count=$(jq 'length' <<<"$prs")

if [ "$pr_count" -gt 0 ]; then
  echo "Found $pr_count merged PRs since $SINCE_DATE" >&2

  # Deterministic changelog appended verbatim after the LLM's narrative notes.
  {
    echo "## 📋 Changelog"
    echo
    jq -r 'sort_by(.mergedAt) | reverse | .[] |
      "- [#\(.number)](\(.url)) \(.title) — @\(.author.login)"' <<<"$prs"
  } > "$OUT_DIR/changelog.md"

  {
    echo "# Work merged into $REPO ($DEFAULT_BRANCH) since $SINCE_DATE"
    echo
    echo "## Merged pull requests"
  } > "$CONTEXT"

  owner="${REPO%/*}"; name="${REPO#*/}"
  parents="$OUT_DIR/parents.jsonl"; : > "$parents"

  for pr in $(jq -r '.[].number' <<<"$prs"); do
    jq -r --argjson n "$pr" --argjson limit "$PR_BODY_LIMIT" '
      .[] | select(.number == $n) |
      "\n### PR #\(.number): \(.title)\nAuthor: @\(.author.login) · Merged: \(.mergedAt) · \(.url)\n\n\(.body // "" | .[0:$limit])\n"
    ' <<<"$prs" >> "$CONTEXT"

    linked=$(gh api graphql \
      -f query='query($owner:String!,$name:String!,$pr:Int!){
        repository(owner:$owner,name:$name){
          pullRequest(number:$pr){
            closingIssuesReferences(first:10){
              nodes{ number title parent{ number title body } }
            }}}}' \
      -f owner="$owner" -f name="$name" -F pr="$pr" \
      --jq '.data.repository.pullRequest.closingIssuesReferences.nodes')

    if [ "$(jq 'length' <<<"$linked")" -gt 0 ]; then
      echo "Closes issues:" >> "$CONTEXT"
      jq -r '.[] | "- #\(.number) \(.title)\(if .parent then " (part of initiative #\(.parent.number): \(.parent.title))" else "" end)"' \
        <<<"$linked" >> "$CONTEXT"
      jq -c '.[] | select(.parent) | .parent' <<<"$linked" >> "$parents"
    fi
  done

  if [ -s "$parents" ]; then
    {
      echo
      echo "## Parent initiatives (the why behind the PRs)"
    } >> "$CONTEXT"
    jq -rs --argjson limit "$PARENT_BODY_LIMIT" '
      unique_by(.number) | .[] |
      "\n### Initiative #\(.number): \(.title)\n\n\(.body // "" | .[0:$limit])\n"
    ' "$parents" >> "$CONTEXT"
  fi

  echo "mode=prs" >> "$GITHUB_OUTPUT"
  echo "skip=false" >> "$GITHUB_OUTPUT"
  exit 0
fi

echo "No merged PRs since $SINCE_DATE; checking commits on $DEFAULT_BRANCH" >&2
commits=$(gh api "repos/$REPO/commits?since=$SINCE_ISO&sha=$DEFAULT_BRANCH&per_page=100" \
  --jq '[.[] | select(.commit.message | startswith("Merge pull request") | not)]')

commit_count=$(jq 'length' <<<"$commits")

if [ "$commit_count" -eq 0 ]; then
  echo "Quiet week: no PRs, no commits. Skipping release." >&2
  echo "mode=none" >> "$GITHUB_OUTPUT"
  echo "skip=true" >> "$GITHUB_OUTPUT"
  exit 0
fi

echo "Found $commit_count commits since $SINCE_DATE" >&2
{
  echo "## 📋 Changelog"
  echo
  jq -r '.[] | "- [`\(.sha[0:7])`](\(.html_url)) \(.commit.message | split("\n")[0]) — @\(.author.login // .commit.author.name)"' <<<"$commits"
} > "$OUT_DIR/changelog.md"
{
  echo "# Work committed to $REPO ($DEFAULT_BRANCH) since $SINCE_DATE"
  echo
  echo "No pull requests were merged this week; these are direct commits."
  echo
  jq -r '.[] | "- \(.commit.message | split("\n")[0]) — @\(.author.login // .commit.author.name) (\(.html_url))"' <<<"$commits"
} > "$CONTEXT"

echo "mode=commits" >> "$GITHUB_OUTPUT"
echo "skip=false" >> "$GITHUB_OUTPUT"
