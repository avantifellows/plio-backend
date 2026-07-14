"""Direct result-set assertions on the plio app's raw-SQL query builders.

The builders in ``plio/queries.py`` hand-write the SQL that feeds the metrics
endpoint and the ``download_data`` CSV report. Existing tests execute this SQL
but never check its output, so a Django/psycopg bump that changed a result set
would keep CI green. Each spec here constructs a deliberately tiny timeline with
the shared factories inside ``in_workspace(org_a)``, calls a builder, executes
the returned SQL on a raw database cursor (passing the workspace's schema name
explicitly, so the schema-qualification behaviour is pinned without any
``connection.set_schema()``), and asserts the exact rows against literals worked
out by hand from that timeline -- never recomputed by re-running the app's own
aggregation.

jsonb columns (``answer``, ``options``, ``correct_answer``) come back from the
raw cursor as their Postgres jsonb *text* form -- a scalar ``0`` reads as the
string ``"0"``, a list ``["A", "B"]`` as ``'["A", "B"]'``, and a stored NULL as
``None``. The expected literals below use that documented text form.

This module is the shared home for every query-builder test in the plio unit
fill; the follow-up slices append the masking-carrying builders here. It lives
outside ``tests/integration/`` so the unit lane collects it.
"""

from django.db import connection

from plio.queries import (
    get_plio_details_query,
    get_plio_latest_responses_query,
    get_plio_latest_sessions_query,
)
from tests.builders import in_workspace
from tests.factories import (
    ItemFactory,
    PlioFactory,
    QuestionFactory,
    SessionAnswerFactory,
    SessionFactory,
    UserFactory,
)


def _run(query):
    """Execute a builder's SQL on a raw cursor and return the rows.

    Slice-local on purpose -- nothing here belongs in the shared harness until a
    second module needs it.
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()


def test_latest_sessions_returns_one_row_per_learner_newest_session(db, org_a):
    with in_workspace(org_a):
        plio = PlioFactory()
        learner_a = UserFactory()
        learner_b = UserFactory()
        # learner A rewatched: two sessions on the same plio. The builder ranks
        # by descending session id, so only the newer (higher-id) session wins.
        SessionFactory(plio=plio, user=learner_a, watch_time=10, retention="early-a")
        newer_a = SessionFactory(
            plio=plio, user=learner_a, watch_time=30, retention="late-a"
        )
        # learner B watched once
        session_b = SessionFactory(
            plio=plio, user=learner_b, watch_time=50, retention="only-b"
        )
        # decoy plio in the same workspace with its own session -- a lost
        # per-plio predicate would pull this row into the result set
        decoy = PlioFactory()
        SessionFactory(
            plio=decoy, user=UserFactory(), watch_time=999, retention="decoy"
        )

    rows = _run(get_plio_latest_sessions_query(plio.uuid, org_a.schema_name))

    # exactly one row per learner: A's earlier 10s session is superseded by the
    # newer 30s one; learner B's single session stands; the decoy is absent.
    # No ORDER BY in this builder -> compare order-insensitively.
    assert set(rows) == {
        (newer_a.id, 30.0, "late-a"),
        (session_b.id, 50.0, "only-b"),
    }


def test_latest_responses_single_session_uses_equality_branch(db, org_a):
    with in_workspace(org_a):
        plio = PlioFactory()
        item = ItemFactory(plio=plio, time=10)
        QuestionFactory(item=item, type="mcq", options=["A", "B"], correct_answer=0)
        learner = UserFactory()
        session = SessionFactory(plio=plio, user=learner)
        answer = SessionAnswerFactory(session=session, item=item, answer=0)
        # decoy: another plio's session + answer, whose id is not queried; the
        # builder filters purely on session id, so passing only this plio's
        # session must exclude it
        decoy = PlioFactory()
        decoy_item = ItemFactory(plio=decoy, time=5)
        QuestionFactory(item=decoy_item, mcq=True)
        decoy_session = SessionFactory(plio=decoy, user=UserFactory())
        SessionAnswerFactory(session=decoy_session, item=decoy_item, answer=1)

    query = get_plio_latest_responses_query(org_a.schema_name, (session.id,))
    # a single id takes the equality form, not the IN tuple form
    assert "session.id IN" not in query

    rows = _run(query)

    # one row for the queried session; the decoy session's answer is excluded.
    # answer 0 and correct answer 0 read back as their jsonb text "0"; the
    # learner did not log in via SSO, so the survey flag is boolean False.
    assert set(rows) == {
        (answer.id, learner.id, "0", "question", "mcq", "0", False),
    }


def test_latest_responses_multiple_sessions_use_in_tuple_branch(db, org_a):
    with in_workspace(org_a):
        plio = PlioFactory()
        item = ItemFactory(plio=plio, time=10)
        QuestionFactory(item=item, type="mcq", options=["A", "B"], correct_answer=0)
        learner_a = UserFactory()
        learner_b = UserFactory()
        session_a = SessionFactory(plio=plio, user=learner_a)
        answer_a = SessionAnswerFactory(session=session_a, item=item, answer=0)  # right
        session_b = SessionFactory(plio=plio, user=learner_b)
        answer_b = SessionAnswerFactory(session=session_b, item=item, answer=1)  # wrong
        # decoy: a third session whose id is not queried
        decoy = PlioFactory()
        decoy_item = ItemFactory(plio=decoy, time=5)
        QuestionFactory(item=decoy_item, mcq=True)
        decoy_session = SessionFactory(plio=decoy, user=UserFactory())
        SessionAnswerFactory(session=decoy_session, item=decoy_item, answer=0)

    query = get_plio_latest_responses_query(
        org_a.schema_name, (session_a.id, session_b.id)
    )
    # two ids take the IN tuple form
    assert "session.id IN" in query

    rows = _run(query)

    # one row per queried session; the decoy session's answer is excluded.
    # answers 0 and 1 read back as their jsonb text; the correct answer is "0".
    assert set(rows) == {
        (answer_a.id, learner_a.id, "0", "question", "mcq", "0", False),
        (answer_b.id, learner_b.id, "1", "question", "mcq", "0", False),
    }


def test_plio_details_returns_item_and_question_rows(db, org_a):
    with in_workspace(org_a):
        plio = PlioFactory()
        mcq_item = ItemFactory(plio=plio, time=10)
        QuestionFactory(
            item=mcq_item,
            type="mcq",
            text="Pick one",
            options=["A", "B"],
            correct_answer=0,
        )
        subjective_item = ItemFactory(plio=plio, time=20)
        QuestionFactory(
            item=subjective_item,
            type="subjective",
            text="Explain",
            options=None,
            correct_answer=None,
        )
        # decoy plio with its own item + question -- a lost per-plio predicate
        # would surface its row here
        decoy = PlioFactory()
        decoy_item = ItemFactory(plio=decoy, time=99)
        QuestionFactory(item=decoy_item, mcq=True, text="Decoy")

    rows = _run(get_plio_details_query(plio.uuid, org_a.schema_name))

    # exact detail row per item; times are floats, options/correct answer read
    # back as their jsonb text ("0", '["A", "B"]') with NULLs as None; the decoy
    # item is absent. No ORDER BY -> compare order-insensitively.
    assert set(rows) == {
        (mcq_item.id, "question", 10.0, "mcq", "Pick one", '["A", "B"]', "0"),
        (subjective_item.id, "question", 20.0, "subjective", "Explain", None, None),
    }
