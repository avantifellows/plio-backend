"""HTTP-seam assertions on the ``download_data`` report CSV *content*.

``GET /api/v1/plios/{uuid}/download_data/`` streams a zip of CSVs built by a
raw-SQL + pandas pipeline. The existing ``APITestCase`` tests for this endpoint
check only the HTTP status code, so a Django/psycopg/pandas bump could silently
corrupt every creator's report while CI stays green. Each spec here constructs a
deliberately tiny timeline with the shared factories, downloads the report over
the real HTTP seam (selecting the workspace through the ``Organization`` header
only -- never ``connection.set_schema()``), and asserts the zip's member list,
each CSV's exact column set, answer re-indexing, skip serialization, and the
masked-identifier path against literals worked out by hand from that timeline --
never recomputed by re-running the app's own aggregation.

The masked-identifier path is pinned via a personal-workspace owner downloading
their own plio: the personal workspace has no organization, so the org-admin
check is false and identifiers are masked. Masked values are checked against
Python ``hashlib.md5`` as an oracle independent of Postgres's ``MD5``.

This module complements -- does not duplicate -- the integration report journey
(``tests/integration/creator/test_report_contents.py``), which owns the unmasked
org-admin mcq path end-to-end and watch-time rounding. It lives outside
``tests/integration/`` so the unit lane collects it. Its zip/CSV readers and
dump-dir cleanup fixture are kept local on purpose; nothing here belongs in the
shared harness until a second consumer appears.

Pre-existing bug pinned here: ``download_data`` returns HTTP 500 for *any* plio
that contains a subjective question, because the interaction-details step
(``plio/views.py``) runs ``question_correct_answer.apply(json.loads)`` with no
null guard, while a subjective question stores ``correct_answer`` as SQL NULL
(``None`` from the raw cursor). The existing status-only download tests never hit
this -- their plio has no questions. Rather than change product code (out of
scope for this slice), the subjective AC is encoded as a ``strict`` xfail that
documents the desired behaviour and turns the build red the moment an upgrade or
fix changes it.
"""

import csv
import hashlib
import io
import shutil
import zipfile
from types import SimpleNamespace

import pytest

from tests.factories import (
    EventFactory,
    ItemFactory,
    PlioFactory,
    QuestionFactory,
    SessionAnswerFactory,
    SessionFactory,
    UserFactory,
)


def _read_csv(archive, name):
    with archive.open(name) as handle:
        return list(csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8")))


def _columns(archive, name):
    with archive.open(name) as handle:
        return csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8")).fieldnames


def _masked(user):
    """The independent oracle for a masked identifier: Python's md5 of the user
    id's text form, matching the query's ``MD5(session.user_id::varchar(255))``
    without reusing Postgres to compute the expectation."""
    return hashlib.md5(str(user.id).encode()).hexdigest()


@pytest.fixture
def report_dump_cleanup():
    """download_data writes its dump under /tmp/plio-<uuid> and only cleans it
    on the *next* download of the same plio -- remove what this test generated
    so repeated local runs don't accumulate archive trees in the container."""
    uuids = []
    yield uuids
    for plio_uuid in uuids:
        shutil.rmtree("/tmp/plio-{}".format(plio_uuid), ignore_errors=True)


def _seed_report_scenario(owner):
    """Build one tiny personal-workspace report timeline plus a decoy plio.

    Personal workspace => no ``in_workspace``; objects land in the public schema,
    which is where a header-less download queries. Two learners each get one
    session, one answer, and one event: a checkbox answer (correct) and a skip
    (null answer on an mcq question). The plio deliberately has no subjective
    question so the download succeeds -- see the module docstring and the
    subjective xfail below. The decoy plio carries its own session, answer, and
    event so every assertion doubles as proof the dump queries keep their
    per-plio predicate.
    """
    plio = PlioFactory(
        created_by=owner.user,
        name="Report CSV plio",
        published=True,
        video__url="https://www.youtube.com/watch?v=reportcsv1",
        video__duration=120,
    )

    checkbox_item = ItemFactory(plio=plio, time=5)
    QuestionFactory(
        item=checkbox_item,
        type="checkbox",
        text="Pick all that apply",
        options=["A", "B", "C"],
        correct_answer=[0, 2],  # 0-based; re-indexed to [1, 3]
    )
    skipped_item = ItemFactory(plio=plio, time=15)
    QuestionFactory(
        item=skipped_item,
        type="mcq",
        text="Skipped question",
        options=["X", "Y"],
        correct_answer=0,
    )

    checkbox_learner = UserFactory()
    checkbox_session = SessionFactory(plio=plio, user=checkbox_learner, watch_time=10)
    SessionAnswerFactory(session=checkbox_session, item=checkbox_item, answer=[0, 2])
    EventFactory(session=checkbox_session, type="played", player_time=1)

    skip_learner = UserFactory()
    skip_session = SessionFactory(plio=plio, user=skip_learner, watch_time=30)
    SessionAnswerFactory(session=skip_session, item=skipped_item, answer=None)
    EventFactory(session=skip_session, type="played", player_time=3)

    decoy_question_text = "Decoy question"
    decoy = PlioFactory(created_by=owner.user, name="Decoy plio", published=True)
    decoy_item = ItemFactory(plio=decoy, time=7)
    QuestionFactory(item=decoy_item, mcq=True, text=decoy_question_text)
    decoy_learner = UserFactory()
    decoy_session = SessionFactory(plio=decoy, user=decoy_learner, watch_time=99)
    SessionAnswerFactory(session=decoy_session, item=decoy_item, answer=0)
    EventFactory(session=decoy_session, type="paused", player_time=99)

    return SimpleNamespace(
        plio=plio,
        checkbox_learner=checkbox_learner,
        skip_learner=skip_learner,
        decoy_learner=decoy_learner,
        decoy_question_text=decoy_question_text,
    )


def _download_report(owner, plio, report_dump_cleanup):
    """Download the report over the HTTP seam (no Organization header -> personal
    workspace) and return the opened zip archive."""
    report_dump_cleanup.append(plio.uuid)
    response = owner.get("/api/v1/plios/{}/download_data/".format(plio.uuid))
    assert response.status_code == 200
    return zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content)))


def test_report_zip_contains_six_csvs_and_readme(authed_client, report_dump_cleanup):
    owner = authed_client()
    scenario = _seed_report_scenario(owner)

    archive = _download_report(owner, scenario.plio, report_dump_cleanup)

    # exactly the six named CSVs plus the README PDF -- nothing more, nothing less
    assert set(archive.namelist()) == {
        "sessions.csv",
        "user-level-metrics.csv",
        "responses.csv",
        "plio-interaction-details.csv",
        "events.csv",
        "plio-meta-details.csv",
        "READ-ME-FIRST.pdf",
    }


def test_report_csv_column_sets_are_exact(authed_client, report_dump_cleanup):
    owner = authed_client()
    scenario = _seed_report_scenario(owner)

    archive = _download_report(owner, scenario.plio, report_dump_cleanup)

    assert _columns(archive, "sessions.csv") == [
        "session_id",
        "watch_time",
        "user_identifier",
        "has_user_logged_in_via_sso",
        "created_at",
        "last_updated_at",
    ]
    assert _columns(archive, "user-level-metrics.csv") == [
        "user_identifier",
        "has_user_logged_in_via_sso",
        "num_questions_attempted",
        "num_questions_answered_correctly",
        "are_all_questions_attempted",
    ]
    # the view drops the raw ``answer`` column and re-appends the re-indexed one
    # last, so ``answer`` is the final column of responses.csv
    assert _columns(archive, "responses.csv") == [
        "session_id",
        "user_identifier",
        "has_user_logged_in_via_sso",
        "item_id",
        "question_type",
        "correct_answer",
        "is_answer_correct",
        "answered_at",
        "answer",
    ]
    assert _columns(archive, "plio-interaction-details.csv") == [
        "item_id",
        "item_type",
        "item_time",
        "question_type",
        "question_text",
        "question_options",
        "question_correct_answer",
    ]
    assert _columns(archive, "events.csv") == [
        "session_id",
        "user_identifier",
        "has_user_logged_in_via_sso",
        "event_type",
        "event_player_time",
        "event_details",
        "event_global_time",
    ]
    assert _columns(archive, "plio-meta-details.csv") == ["id", "name", "video"]


def test_checkbox_answers_are_reindexed_one_based(authed_client, report_dump_cleanup):
    owner = authed_client()
    scenario = _seed_report_scenario(owner)

    archive = _download_report(owner, scenario.plio, report_dump_cleanup)

    # responses.csv: the submitted checkbox answer, stored 0-based as [0, 2],
    # is serialized 1-based as [1, 3]
    responses = _read_csv(archive, "responses.csv")
    checkbox_rows = [r for r in responses if r["question_type"] == "checkbox"]
    assert len(checkbox_rows) == 1
    assert checkbox_rows[0]["answer"] == "[1, 3]"
    # ...and the matching checkbox answer is graded correct: a grading CASE
    # narrowed to mcq-only would mark this row false while every other
    # assertion stayed green
    assert checkbox_rows[0]["is_answer_correct"] == "true"

    # plio-interaction-details.csv: the checkbox correct answer, stored 0-based
    # as [0, 2], is serialized 1-based as [1, 3]
    interactions = _read_csv(archive, "plio-interaction-details.csv")
    checkbox_questions = [r for r in interactions if r["question_type"] == "checkbox"]
    assert len(checkbox_questions) == 1
    assert checkbox_questions[0]["question_correct_answer"] == "[1, 3]"


def test_skipped_answer_serialized_empty_and_incorrect(
    authed_client, report_dump_cleanup
):
    owner = authed_client()
    scenario = _seed_report_scenario(owner)

    archive = _download_report(owner, scenario.plio, report_dump_cleanup)

    responses = _read_csv(archive, "responses.csv")
    # the skip landed on the mcq question as a null answer
    skipped_rows = [r for r in responses if r["question_type"] == "mcq"]
    assert len(skipped_rows) == 1
    # a null answer serializes as an empty cell -- distinguishable from a wrong
    # answer -- and is graded incorrect
    assert skipped_rows[0]["answer"] == ""
    assert skipped_rows[0]["is_answer_correct"] == "false"


def test_personal_workspace_download_masks_identifiers(
    authed_client, report_dump_cleanup
):
    owner = authed_client()
    scenario = _seed_report_scenario(owner)

    archive = _download_report(owner, scenario.plio, report_dump_cleanup)

    # a personal-workspace owner is not an org admin, so every user-carrying CSV
    # masks the identifier to the MD5 of the user id (independent hashlib oracle)
    expected = {
        _masked(scenario.checkbox_learner),
        _masked(scenario.skip_learner),
    }
    for name in (
        "sessions.csv",
        "user-level-metrics.csv",
        "responses.csv",
        "events.csv",
    ):
        rows = _read_csv(archive, name)
        assert {row["user_identifier"] for row in rows} == expected, name


def test_decoy_plio_rows_absent_from_every_csv(authed_client, report_dump_cleanup):
    owner = authed_client()
    scenario = _seed_report_scenario(owner)

    archive = _download_report(owner, scenario.plio, report_dump_cleanup)

    decoy_masked = _masked(scenario.decoy_learner)
    for name in (
        "sessions.csv",
        "user-level-metrics.csv",
        "responses.csv",
        "events.csv",
    ):
        rows = _read_csv(archive, name)
        assert decoy_masked not in {row["user_identifier"] for row in rows}, name

    # the decoy's question is absent from interaction-details; the report plio's
    # own question is present
    interactions = _read_csv(archive, "plio-interaction-details.csv")
    question_texts = {row["question_text"] for row in interactions}
    assert scenario.decoy_question_text not in question_texts
    assert "Pick all that apply" in question_texts

    # plio-meta-details names the report plio, not the decoy
    meta = _read_csv(archive, "plio-meta-details.csv")
    assert len(meta) == 1
    assert meta[0]["id"] == scenario.plio.uuid
    assert meta[0]["name"] == "Report CSV plio"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "pre-existing bug: download_data returns HTTP 500 for a plio with a "
        "subjective question -- the interaction-details step in plio/views.py "
        "runs question_correct_answer.apply(json.loads) with no null guard, but "
        "a subjective question stores correct_answer as SQL NULL. Fixing the "
        "endpoint is out of scope for this test-wall slice; this strict xfail "
        "encodes the desired behaviour and will fail the build if an upgrade or "
        "fix changes it."
    ),
)
def test_subjective_answer_verbatim_and_graded_correct(
    authed_client, report_dump_cleanup
):
    owner = authed_client()
    plio = PlioFactory(
        created_by=owner.user, name="Subjective report plio", published=True
    )
    subjective_item = ItemFactory(plio=plio, time=10)
    QuestionFactory(
        item=subjective_item,
        type="subjective",
        text="Explain your reasoning",
        options=None,
        correct_answer=None,
    )
    learner = UserFactory()
    session = SessionFactory(plio=plio, user=learner, watch_time=20)
    SessionAnswerFactory(
        session=session, item=subjective_item, answer="My essay answer"
    )

    archive = _download_report(owner, plio, report_dump_cleanup)

    # desired behaviour once the endpoint tolerates subjective questions: a
    # non-empty subjective answer appears verbatim and is graded correct
    responses = _read_csv(archive, "responses.csv")
    subjective_rows = [r for r in responses if r["question_type"] == "subjective"]
    assert len(subjective_rows) == 1
    assert subjective_rows[0]["answer"] == "My essay answer"
    assert subjective_rows[0]["is_answer_correct"] == "true"
