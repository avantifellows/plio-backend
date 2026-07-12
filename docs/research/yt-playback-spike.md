# YouTube Playback Spike — Real Playback on GitHub Actions Runners

**Date:** 2026-07-13 · **Resolves:** [wayfinder ticket #371](https://github.com/avantifellows/plio-backend/issues/371) · **Feeds:** the e2e workstream decision issue (amends the playback strategy from [#369](https://github.com/avantifellows/plio-backend/issues/369))

## Question

Is real YouTube playback reliable in headless browsers on GitHub-hosted runners — the default the E2E stack decision (#369) adopted pending this spike?

## Verdict: hard-blocked, not flaky. 0/20 runs played a single frame on GHA.

Every one of 20 jobs — 10 × Playwright's bundled Chromium, 10 × the runner's preinstalled Google Chrome (`channel: 'chrome'`) — failed identically: the YouTube embed threw **error 150 with "Sign in to confirm you're not a bot"** within ~0.3–1.5s of play being issued. No `playing` event ever fired on any run.

The control experiment pins the cause: the **identical harness, identical Playwright version, identical flags** run from a residential IP played flawlessly — `ready` in 598ms, `playing` in 338ms, the 5s popup-marker observed, 60s of media played in ~61.5s wall-clock. The blocker is **YouTube's datacenter-IP bot wall** (GitHub-hosted runners egress from Azure ranges), not headless mode, not Playwright automation signals, not codecs, not the video.

| Datum | CI (GHA, 20 runs) | Local control (residential IP) |
|---|---|---|
| Plyr `ready` | ✅ 547–3817 ms (20/20) | ✅ 598 ms |
| `playing` event | ❌ never (0/20) | ✅ 338 ms |
| Failure class | `bot_wall` 20/20, YT error 150 | — (playback succeeded) |
| 5s popup-marker seen | ❌ | ✅ |
| 60s of media played | ❌ | ✅ (60.4s reached) |
| Codec probe (h264/vp9/aac) | all `true`, both browser legs | all `true` |
| Ad interference | none observed (`duration_at_ready` = 635s everywhere) | none |
| Chromium vs Chrome channel | no difference — blocked identically | — |

Notes: the local control run technically reported "failed" on a strict monotonically-non-decreasing `currentTime` assertion — float jitter between `timeupdate` events, a harness-strictness artifact; the playback data above is unambiguous. A public video (Big Buck Bunny, `aqz-KE-bpKQ`) was used rather than a Plio-owned unlisted one; the bot wall is IP-based, so video ownership/visibility would not change the outcome.

## Method

Throwaway branch [`spike/yt-playback-ci` on plio-frontend](https://github.com/avantifellows/plio-frontend/tree/spike/yt-playback-ci) (never merged): a minimal harness mirroring `VideoPlayer.vue` (bare `data-plyr-provider="youtube"` div, Plyr 3.7.8 — the app lockfile's resolved version — served over `http://localhost`, no restrictive Referrer-Policy), a Playwright spec asserting ready → playing → popup-marker at 5s → 60s of monotonic progress (retries 0, `--autoplay-policy=no-user-gesture-required`), instrumented with a failure classifier (`bot_wall` / `error_153` / `timeout` / `other` via iframe body-text scan), a codec probe, and ad-tolerant timing capture. Run as a 10-attempt × 2-browser matrix: [workflow run 29206365523](https://github.com/avantifellows/plio-frontend/actions/runs/29206365523), all 20 result artifacts uploaded. Design informed by a parallel research sweep of 2024–26 failure modes (bot walls on datacenter IPs, the Nov-2025 Error-153 referrer enforcement, Playwright-Chromium codec gaps, embed ads, Plyr iframe_api init races).

Deviation from the ticket: 20 parallel matrix jobs (20 independent runner VMs) instead of 20 consecutive re-runs — a wider environment sample; with a deterministic 20/20 outcome the distinction is moot.

## Implications for the e2e workstream (recommended, to be ratified in its decision issue)

The #369 fallback assumed "shaky"; reality is "impossible on GHA-hosted runners". The operative strategy:

1. **CI keeps every non-playback assertion.** The embed *loads* fine on GHA (`ready` fired 20/20) — so "player renders" asserts (golden creator path's final step) stay in CI unchanged.
2. **Playback-dependent journeys (golden playback, resume) run playback-stubbed in CI** — drive Plyr/app state programmatically to exercise the popup, answer, scorecard, and resume logic without real YouTube media (survey option c).
3. **Real playback stays in the suite behind a `@real-playback` tag, excluded on GHA and run locally** — residential IPs work (proven by the control). Under the local-first decision this is a natural lane: a human or agent runs the full real-playback pass locally before releases.
4. **If real-playback-in-CI ever becomes mandatory:** a self-hosted runner with non-datacenter egress is the only path surfaced by this spike. Not recommended now.

Boot-timing footnote for shard-count: browser install + boot on the runner was ~50–80s per job (from job logs); docker-compose stack boot wasn't measured here (the harness doesn't need it) and historical e2e-workflow step data has expired — measure it when the real workflow is built.
