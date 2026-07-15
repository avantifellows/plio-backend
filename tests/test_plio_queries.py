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
fill: the latest-sessions, latest-responses and plio-details builders (#400), the
sessions-dump and events builders (#402), and the responses-dump and
user-level-metrics "grading" builders (#403). It lives outside
``tests/integration/`` so the unit lane collects it.
"""

import hashlib
from collections import Counter
from types import SimpleNamespace

from django.db import connection

from plio.queries import (
    get_events_query,
    get_plio_details_query,
    get_plio_latest_responses_query,
    get_plio_latest_sessions_query,
    get_responses_dump_query,
    get_sessions_dump_query,
    get_user_level_metrics_query,
)
from tests.builders import in_workspace
from tests.factories import (
    EventFactory,
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


def _masked_identifier(user_id):
    """The independent oracle for the masked ``user_identifier``.

    The builders emit ``MD5(session.user_id::varchar(255))``; this recomputes
    the same value in Python from the stringified user id, so the assertion
    disagrees with the SQL the moment the masking expression drifts. Computed
    with ``hashlib`` rather than a second ``MD5()`` query so it is not a
    tautology.
    """
    return hashlib.md5(str(user_id).encode()).hexdigest()


def _seed_identity_learners(org):
    """Create the four-learner identity matrix shared by the masking specs.

    Each learner exercises one branch of the unmasked ``user_identifier``
    coalesce (email -> mobile -> unique_id) and, together, the SSO CASE's full
    truth table (the flag requires unique_id AND auth_org):

    - ``email`` learner: has an email (and a mobile) but no unique_id -> SSO
      flag ``'false'``.
    - ``mobile`` learner: no email, so the identifier falls back to the mobile;
      carries both a unique_id and an ``auth_org`` -> SSO flag ``'true'`` (and
      proves the mobile wins over the unique_id in the coalesce).
    - ``unique`` learner: no email and no mobile, so the identifier falls back to
      the unique_id; has a unique_id but no ``auth_org`` -> SSO flag ``'false'``
      (pins the auth_org half of the AND).
    - ``authorg`` learner: has an email and an ``auth_org`` but *no* unique_id ->
      SSO flag ``'false'`` (pins the unique_id half of the AND -- a predicate
      that dropped the unique_id requirement would flag this learner 'true').
    """
    learner_email = UserFactory()
    learner_mobile = UserFactory(email=None, unique_id="sso-mobile", auth_org=org)
    learner_unique = UserFactory(
        email=None, mobile=None, unique_id="sso-unique", auth_org=None
    )
    learner_authorg = UserFactory(unique_id=None, auth_org=org)
    return learner_email, learner_mobile, learner_unique, learner_authorg


def test_latest_sessions_returns_one_row_per_learner_newest_session(db, org_a):
    with in_workspace(org_a):
        plio = PlioFactory()
        learner_a = UserFactory()
        learner_b = UserFactory()
        # learner A rewatched: two sessions on the same plio. The builder ranks
        # by descending session id, so only the newer (higher-id) session wins.
        # The newer session deliberately has the *smaller* watch time, so a
        # ranking that switched to watch_time DESC would pick the older session
        # and fail here.
        SessionFactory(plio=plio, user=learner_a, watch_time=30, retention="early-a")
        newer_a = SessionFactory(
            plio=plio, user=learner_a, watch_time=7, retention="late-a"
        )
        # learner B watched once
        session_b = SessionFactory(
            plio=plio, user=learner_b, watch_time=50, retention="only-b"
        )
        # decoy plio watched by *learner A* (not a fresh user), created after
        # A's target sessions so it holds A's globally-highest session id: the
        # ranking window partitions by (user_id, plio_id), and dropping the
        # plio_id from the partition would let this decoy session take A's
        # rank 1 and evict A's target row -- a fresh-user decoy cannot catch
        # that mutation
        decoy = PlioFactory()
        SessionFactory(plio=decoy, user=learner_a, watch_time=999, retention="decoy")

    rows = _run(get_plio_latest_sessions_query(plio.uuid, org_a.schema_name))

    # exactly one row per learner: A's earlier 30s session is superseded by the
    # newer 7s one (newest-by-id, not biggest-by-watch-time); learner B's single
    # session stands; the decoy is absent. No ORDER BY in this builder ->
    # compare order-insensitively but preserve row multiplicity (a set would
    # hide join fan-out duplicates).
    assert Counter(rows) == Counter(
        [
            (newer_a.id, 7.0, "late-a"),
            (session_b.id, 50.0, "only-b"),
        ]
    )


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
    # trailing False is question.survey (the factory default -- this is not a
    # survey question). Multiset comparison preserves row multiplicity.
    assert Counter(rows) == Counter(
        [
            (answer.id, learner.id, "0", "question", "mcq", "0", False),
        ]
    )


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
    assert Counter(rows) == Counter(
        [
            (answer_a.id, learner_a.id, "0", "question", "mcq", "0", False),
            (answer_b.id, learner_b.id, "1", "question", "mcq", "0", False),
        ]
    )


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
    # item is absent. No ORDER BY -> compare order-insensitively, multiset.
    assert Counter(rows) == Counter(
        [
            (mcq_item.id, "question", 10.0, "mcq", "Pick one", '["A", "B"]', "0"),
            (
                subjective_item.id,
                "question",
                20.0,
                "subjective",
                "Explain",
                None,
                None,
            ),
        ]
    )


def test_sessions_dump_unmasked_identifier_fallback_and_sso_flag(db, org_a):
    with in_workspace(org_a):
        plio = PlioFactory()
        (
            learner_email,
            learner_mobile,
            learner_unique,
            learner_authorg,
        ) = _seed_identity_learners(org_a)
        # the email learner rewatched: two sessions on the same plio. The
        # sessions dump has no latest-only filter, so both rows must appear.
        email_s1 = SessionFactory(plio=plio, user=learner_email, watch_time=10)
        email_s2 = SessionFactory(plio=plio, user=learner_email, watch_time=25)
        mobile_s = SessionFactory(plio=plio, user=learner_mobile, watch_time=40)
        unique_s = SessionFactory(plio=plio, user=learner_unique, watch_time=55)
        authorg_s = SessionFactory(plio=plio, user=learner_authorg, watch_time=70)
        # decoy plio in the same workspace with its own session -- a lost
        # per-plio predicate would pull this row into the result set
        decoy = PlioFactory()
        SessionFactory(plio=decoy, user=UserFactory(), watch_time=999)
        # touch one session after creation so its updated_at is measurably
        # later than its created_at -- the two timestamp columns become
        # distinguishable, so a builder swapping them fails below
        email_s1.save()
        email_s1.refresh_from_db()

    rows = _run(
        get_sessions_dump_query(
            plio.uuid, org_a.schema_name, show_unmasked_user_id=True
        )
    )

    # (session_id, watch_time, user_identifier, sso_flag) per row. The unmasked
    # identifier coalesces email -> mobile -> unique_id; the mobile learner
    # carries unique_id+auth_org so its SSO flag is 'true', while the authorg
    # learner (auth_org without unique_id) stays 'false'. Both of the email
    # learner's sessions appear (no latest-only filter); the decoy session is
    # absent. No ORDER BY -> order-insensitive, multiset.
    projected = [(row[0], row[1], row[2], row[3]) for row in rows]
    assert Counter(projected) == Counter(
        [
            (email_s1.id, 10.0, learner_email.email, "false"),
            (email_s2.id, 25.0, learner_email.email, "false"),
            (mobile_s.id, 40.0, learner_mobile.mobile, "true"),
            (unique_s.id, 55.0, learner_unique.unique_id, "false"),
            (authorg_s.id, 70.0, learner_authorg.email, "false"),
        ]
    )
    # the timestamp *values* come from the session row itself: a builder that
    # selected the wrong datetime source (or swapped created/updated) fails
    # these equality checks against the model fields
    by_id = {row[0]: row for row in rows}
    for sess in (email_s1, email_s2, mobile_s, unique_s, authorg_s):
        assert by_id[sess.id][4] == sess.created_at
        assert by_id[sess.id][5] == sess.updated_at
    assert email_s1.updated_at > email_s1.created_at


def test_sessions_dump_masked_identifier_is_md5_of_user_id(db, org_a):
    with in_workspace(org_a):
        plio = PlioFactory()
        (
            learner_email,
            learner_mobile,
            learner_unique,
            learner_authorg,
        ) = _seed_identity_learners(org_a)
        email_s = SessionFactory(plio=plio, user=learner_email, watch_time=10)
        mobile_s = SessionFactory(plio=plio, user=learner_mobile, watch_time=40)
        unique_s = SessionFactory(plio=plio, user=learner_unique, watch_time=55)
        authorg_s = SessionFactory(plio=plio, user=learner_authorg, watch_time=70)
        # decoy plio in the same workspace with its own session
        decoy = PlioFactory()
        SessionFactory(plio=decoy, user=UserFactory(), watch_time=999)

    rows = _run(
        get_sessions_dump_query(
            plio.uuid, org_a.schema_name, show_unmasked_user_id=False
        )
    )

    # with masking on, user_identifier is the MD5 of the (stringified) user id,
    # checked against the independent Python hashlib oracle. The SSO flag is
    # unaffected by masking. Decoy absent; order-insensitive, multiset.
    projected = [(row[0], row[1], row[2], row[3]) for row in rows]
    assert Counter(projected) == Counter(
        [
            (email_s.id, 10.0, _masked_identifier(learner_email.id), "false"),
            (mobile_s.id, 40.0, _masked_identifier(learner_mobile.id), "true"),
            (unique_s.id, 55.0, _masked_identifier(learner_unique.id), "false"),
            (authorg_s.id, 70.0, _masked_identifier(learner_authorg.id), "false"),
        ]
    )


def test_events_unmasked_identifier_fallback_sso_flag_and_content(db, org_a):
    with in_workspace(org_a):
        plio = PlioFactory()
        (
            learner_email,
            learner_mobile,
            learner_unique,
            learner_authorg,
        ) = _seed_identity_learners(org_a)
        email_s = SessionFactory(plio=plio, user=learner_email)
        mobile_s = SessionFactory(plio=plio, user=learner_mobile)
        unique_s = SessionFactory(plio=plio, user=learner_unique)
        # the email learner's session records *two* events: the builder must
        # return every event of a session, so a regression that collapses to
        # one row per session (e.g. DISTINCT ON) fails here
        played_e = EventFactory(
            session=email_s, type="played", player_time=5, details={}
        )
        paused_email_e = EventFactory(
            session=email_s, type="paused", player_time=8, details={}
        )
        paused_mobile_e = EventFactory(
            session=mobile_s,
            type="paused",
            player_time=12.5,
            details={"reason": "buffering"},
        )
        answered_e = EventFactory(
            session=unique_s, type="question_answered", player_time=20, details={}
        )
        authorg_s = SessionFactory(plio=plio, user=learner_authorg)
        authorg_e = EventFactory(
            session=authorg_s, type="played", player_time=30, details={}
        )
        # decoy plio in the same workspace with its own session + event
        decoy = PlioFactory()
        decoy_s = SessionFactory(plio=decoy, user=UserFactory())
        EventFactory(session=decoy_s, type="played", player_time=99, details={})

    rows = _run(
        get_events_query(plio.uuid, org_a.schema_name, show_unmasked_user_id=True)
    )

    # (session_id, user_identifier, sso_flag, event_type, player_time, details).
    # The unmasked identifier coalesces email -> mobile -> unique_id; the mobile
    # learner's unique_id+auth_org make its SSO flag 'true'. details is jsonb,
    # read back as its Postgres text form ('{}' or '{"reason": "buffering"}').
    # Both of the email session's events appear. The decoy event is absent. No
    # ORDER BY -> order-insensitive, multiset.
    projected = [(row[0], row[1], row[2], row[3], row[4], row[5]) for row in rows]
    assert Counter(projected) == Counter(
        [
            (email_s.id, learner_email.email, "false", "played", 5.0, "{}"),
            (email_s.id, learner_email.email, "false", "paused", 8.0, "{}"),
            (
                mobile_s.id,
                learner_mobile.mobile,
                "true",
                "paused",
                12.5,
                '{"reason": "buffering"}',
            ),
            (
                unique_s.id,
                learner_unique.unique_id,
                "false",
                "question_answered",
                20.0,
                "{}",
            ),
            (authorg_s.id, learner_authorg.email, "false", "played", 30.0, "{}"),
        ]
    )
    # the event's global time is the *event row's own* created_at -- a builder
    # sourcing it from the session (or any other timestamp) fails these
    # equality checks against the model field
    by_key = {(row[0], row[3]): row for row in rows}
    for event in (played_e, paused_email_e, paused_mobile_e, answered_e, authorg_e):
        assert by_key[(event.session_id, event.type)][6] == event.created_at


def test_events_masked_identifier_is_md5_of_user_id(db, org_a):
    with in_workspace(org_a):
        plio = PlioFactory()
        (
            learner_email,
            learner_mobile,
            learner_unique,
            learner_authorg,
        ) = _seed_identity_learners(org_a)
        email_s = SessionFactory(plio=plio, user=learner_email)
        mobile_s = SessionFactory(plio=plio, user=learner_mobile)
        unique_s = SessionFactory(plio=plio, user=learner_unique)
        authorg_s = SessionFactory(plio=plio, user=learner_authorg)
        EventFactory(session=email_s, type="played", player_time=5, details={})
        EventFactory(session=mobile_s, type="paused", player_time=12.5, details={})
        EventFactory(
            session=unique_s, type="question_answered", player_time=20, details={}
        )
        EventFactory(session=authorg_s, type="played", player_time=30, details={})
        # decoy plio in the same workspace with its own session + event
        decoy = PlioFactory()
        decoy_s = SessionFactory(plio=decoy, user=UserFactory())
        EventFactory(session=decoy_s, type="played", player_time=99, details={})

    rows = _run(
        get_events_query(plio.uuid, org_a.schema_name, show_unmasked_user_id=False)
    )

    # with masking on, each event row's user_identifier is the MD5 of the
    # (stringified) user id, checked against the independent Python hashlib
    # oracle. The SSO flag is unaffected by masking (the authorg learner's
    # auth_org-without-unique_id stays 'false'). Decoy absent;
    # order-insensitive, multiset.
    projected = [(row[0], row[1], row[2]) for row in rows]
    assert Counter(projected) == Counter(
        [
            (email_s.id, _masked_identifier(learner_email.id), "false"),
            (mobile_s.id, _masked_identifier(learner_mobile.id), "true"),
            (unique_s.id, _masked_identifier(learner_unique.id), "false"),
            (authorg_s.id, _masked_identifier(learner_authorg.id), "false"),
        ]
    )


def _seed_responses_grading(org):
    """Seed one learner answering four questions, one per grading outcome.

    The responses-dump builder's ``is_answer_correct`` CASE grades a row 'true'
    when the answer is non-null AND (the question is subjective OR the answer
    equals the correct answer); everything else is 'false'. Each of the four
    items below drives one branch:

    - ``subj_item``  -- subjective question, non-null answer ``"essay"`` -> 'true'
    - ``match_item`` -- mcq, answer ``0`` equals correct answer ``0`` -> 'true'
    - ``mismatch_item`` -- mcq, answer ``1`` differs from correct ``0`` -> 'false'
    - ``skip_item``  -- mcq, null (skipped) answer -> 'false'

    The grading learner is a *mobile-fallback SSO learner* (no email, unique_id +
    auth_org): this builder carries its own copies of the identifier-coalesce and
    SSO CASE expressions, so they are pinned here independently of the
    sessions/events specs. A second, email/no-SSO learner answers the match item
    to pin the coalesce's email branch and the SSO 'false' side in this builder
    too.

    A decoy plio in the same workspace carries its own session + answer; the
    builder filters on ``plio.uuid``, so a lost per-plio predicate would pull the
    decoy row into the result set. Slice-local: shared by the two responses-dump
    specs, kept out of the harness until a second module needs it.
    """
    plio = PlioFactory()
    subj_item = ItemFactory(plio=plio, time=10)
    QuestionFactory(
        item=subj_item, type="subjective", options=None, correct_answer=None
    )
    match_item = ItemFactory(plio=plio, time=20)
    QuestionFactory(item=match_item, type="mcq", options=["A", "B"], correct_answer=0)
    mismatch_item = ItemFactory(plio=plio, time=30)
    QuestionFactory(
        item=mismatch_item, type="mcq", options=["A", "B"], correct_answer=0
    )
    skip_item = ItemFactory(plio=plio, time=40)
    QuestionFactory(item=skip_item, type="mcq", options=["A", "B"], correct_answer=0)

    learner = UserFactory(email=None, unique_id="sso-responses", auth_org=org)
    session = SessionFactory(plio=plio, user=learner)
    answers = [
        SessionAnswerFactory(session=session, item=subj_item, answer="essay"),
        SessionAnswerFactory(session=session, item=match_item, answer=0),
        SessionAnswerFactory(session=session, item=mismatch_item, answer=1),
        SessionAnswerFactory(session=session, item=skip_item, answer=None),
    ]

    email_learner = UserFactory()
    email_session = SessionFactory(plio=plio, user=email_learner)
    answers.append(
        SessionAnswerFactory(session=email_session, item=match_item, answer=0)
    )

    decoy = PlioFactory()
    decoy_item = ItemFactory(plio=decoy, time=5)
    QuestionFactory(item=decoy_item, mcq=True)
    decoy_session = SessionFactory(plio=decoy, user=UserFactory())
    SessionAnswerFactory(session=decoy_session, item=decoy_item, answer=0)

    return SimpleNamespace(
        plio=plio,
        learner=learner,
        session=session,
        email_learner=email_learner,
        email_session=email_session,
        answers=answers,
        subj_item=subj_item,
        match_item=match_item,
        mismatch_item=mismatch_item,
        skip_item=skip_item,
    )


def test_responses_dump_grading_matrix_and_unmasked_identifier(db, org_a):
    with in_workspace(org_a):
        s = _seed_responses_grading(org_a)

    rows = _run(
        get_responses_dump_query(
            s.plio.uuid, org_a.schema_name, show_unmasked_user_id=True
        )
    )

    # (session_id, user_identifier, sso_flag, answer, item_id, question_type,
    # correct_answer, is_answer_correct) per row. This builder has its own
    # copies of the identity expressions: the grading learner has no email, so
    # the unmasked identifier falls back to the mobile, and their
    # unique_id+auth_org drive the sso flag 'true'; the email learner pins the
    # coalesce's email branch with sso 'false'. Answers and correct answers
    # come back in their raw jsonb text form -- the scalar ``0``/``1`` read as
    # "0"/"1", the subjective string ``"essay"`` keeps its json quotes, the
    # skipped (null) answer and the subjective (null) correct answer are None.
    # The 1-based re-indexing is a later pandas step pinned at the HTTP seam
    # (#401), not here. The four grading outcomes: subjective-non-null 'true',
    # mcq-match 'true', mcq-mismatch 'false', skipped 'false'. Decoy absent; no
    # ORDER BY -> order-insensitive, multiset.
    projected = [row[:8] for row in rows]
    assert Counter(projected) == Counter(
        [
            (
                s.session.id,
                s.learner.mobile,
                "true",
                '"essay"',
                s.subj_item.id,
                "subjective",
                None,
                "true",
            ),
            (
                s.session.id,
                s.learner.mobile,
                "true",
                "0",
                s.match_item.id,
                "mcq",
                "0",
                "true",
            ),
            (
                s.session.id,
                s.learner.mobile,
                "true",
                "1",
                s.mismatch_item.id,
                "mcq",
                "0",
                "false",
            ),
            (
                s.session.id,
                s.learner.mobile,
                "true",
                None,
                s.skip_item.id,
                "mcq",
                "0",
                "false",
            ),
            (
                s.email_session.id,
                s.email_learner.email,
                "false",
                "0",
                s.match_item.id,
                "mcq",
                "0",
                "true",
            ),
        ]
    )
    # the answered-at timestamp is the *answer row's own* created_at -- a
    # builder sourcing it from the session (or any other timestamp) fails
    # these equality checks against the model field
    by_key = {(row[0], row[4]): row for row in rows}
    for answer in s.answers:
        assert by_key[(answer.session_id, answer.item_id)][8] == answer.created_at


def test_responses_dump_masked_identifier_is_md5_of_user_id(db, org_a):
    with in_workspace(org_a):
        s = _seed_responses_grading(org_a)

    rows = _run(
        get_responses_dump_query(
            s.plio.uuid, org_a.schema_name, show_unmasked_user_id=False
        )
    )

    # with masking on, every row's user_identifier is the MD5 of the
    # (stringified) user id, checked against the independent Python hashlib
    # oracle. Masking touches only the identifier: the grading outcomes are
    # unchanged. Projecting (user_identifier, item_id, is_answer_correct) pins
    # all three at once and proves the decoy row is absent; order-insensitive,
    # multiset.
    masked = _masked_identifier(s.learner.id)
    projected = [(row[1], row[4], row[7]) for row in rows]
    assert Counter(projected) == Counter(
        [
            (masked, s.subj_item.id, "true"),
            (masked, s.match_item.id, "true"),
            (masked, s.mismatch_item.id, "false"),
            (masked, s.skip_item.id, "false"),
            (_masked_identifier(s.email_learner.id), s.match_item.id, "true"),
        ]
    )


def _seed_metrics_timeline(org):
    """Seed a three-learner rollup timeline with three questions and a decoy.

    The plio has three mcq questions, each with correct answer ``0``. Three
    learners with lexicographically unambiguous emails cover distinct completion
    levels, and one is an SSO learner so the rollup carries both flag states:

    - ``alice`` -- answers all three correctly. Her session is created *last*
      among this plio's sessions, so it holds the highest session id; the
      builder's ``totalQuestions`` CTE derives the question count from that
      globally-max session (its documented max-session-id assumption), fixing
      ``total_questions`` at 3.
    - ``bob`` -- answers Q1 correctly, Q2 wrong, and skips Q3 (null answer):
      two attempted, one correct, not all attempted. Carries an ``auth_org``
      but *no* unique_id, so his sso flag stays 'false' -- pinning the
      unique_id half of this builder's own SSO AND-predicate.
    - ``carol`` -- a rewatcher and SSO learner (unique_id + auth_org, so her sso
      flag is 'true'). Her older session answered Q1; her newer session answers
      Q2 and Q3 correctly. The rollup must reflect only the newer session (two
      attempted, two correct), never both.
    - ``dave`` -- no email, so this builder's own identifier coalesce falls back
      to his mobile; answers Q1 correctly only.

    A decoy plio in the same workspace carries its own learner/session/answer;
    the builder filters on ``plio.uuid``, so a lost per-plio predicate would pull
    the decoy learner into the result set. Slice-local: shared by the two
    user-level-metrics specs.
    """
    # each question has a *different* correct answer: with a uniform correct
    # answer, a grading join degraded to ON TRUE still matches every answer
    # against some question's correct value and the DISTINCT aggregates hide
    # the fan-out -- distinct values make cross-question matches count wrong
    plio = PlioFactory()
    q1 = ItemFactory(plio=plio, time=10)
    QuestionFactory(item=q1, type="mcq", options=["A", "B", "C"], correct_answer=0)
    q2 = ItemFactory(plio=plio, time=20)
    QuestionFactory(item=q2, type="mcq", options=["A", "B", "C"], correct_answer=1)
    q3 = ItemFactory(plio=plio, time=30)
    QuestionFactory(item=q3, type="mcq", options=["A", "B", "C"], correct_answer=2)

    alice = UserFactory(email="alice@example.com")
    bob = UserFactory(email="bob@example.com", unique_id=None, auth_org=org)
    carol = UserFactory(email="carol@example.com", unique_id="sso-carol", auth_org=org)
    dave = UserFactory(email=None)

    # carol rewatch: older session (Q1 only), then newer session (Q2 + Q3). The
    # newer session has the higher id, so it is carol's latest.
    carol_old = SessionFactory(plio=plio, user=carol)
    SessionAnswerFactory(session=carol_old, item=q1, answer=0)
    carol_new = SessionFactory(plio=plio, user=carol)
    SessionAnswerFactory(session=carol_new, item=q2, answer=1)
    SessionAnswerFactory(session=carol_new, item=q3, answer=2)

    # bob partial: Q1 right, Q2 wrong (submits q1's correct value against q2's
    # different one), Q3 skipped (explicit null-answer row)
    bob_s = SessionFactory(plio=plio, user=bob)
    SessionAnswerFactory(session=bob_s, item=q1, answer=0)
    SessionAnswerFactory(session=bob_s, item=q2, answer=0)
    SessionAnswerFactory(session=bob_s, item=q3, answer=None)

    # dave: Q1 correct only, before alice so hers stays the highest session id
    dave_s = SessionFactory(plio=plio, user=dave)
    SessionAnswerFactory(session=dave_s, item=q1, answer=0)

    # alice full completion, created last so hers is the globally-highest
    # session id for this plio (drives totalQuestions = 3)
    alice_s = SessionFactory(plio=plio, user=alice)
    SessionAnswerFactory(session=alice_s, item=q1, answer=0)
    SessionAnswerFactory(session=alice_s, item=q2, answer=1)
    SessionAnswerFactory(session=alice_s, item=q3, answer=2)

    decoy = PlioFactory()
    decoy_item = ItemFactory(plio=decoy, time=5)
    QuestionFactory(item=decoy_item, mcq=True)
    decoy_learner = UserFactory(email="zzz-decoy@example.com")
    decoy_session = SessionFactory(plio=decoy, user=decoy_learner)
    SessionAnswerFactory(session=decoy_session, item=decoy_item, answer=0)

    return SimpleNamespace(
        plio=plio,
        alice=alice,
        bob=bob,
        carol=carol,
        dave=dave,
    )


def test_user_level_metrics_rollup_unmasked_ordered_by_identifier(db, org_a):
    with in_workspace(org_a):
        s = _seed_metrics_timeline(org_a)

    rows = _run(
        get_user_level_metrics_query(
            s.plio.uuid, org_a.schema_name, show_unmasked_user_id=True
        )
    )

    # (user_identifier, sso_flag, num_questions_attempted,
    # num_questions_answered_correctly, are_all_questions_attempted). Rows are
    # hand-computed from the timeline against total_questions = 3:
    #   dave  -- Q1 correct only (identifier = mobile)          -> 1, 1, 'false'
    #   alice -- all three attempted and correct                -> 3, 3, 'true'
    #   bob   -- Q1 correct, Q2 wrong, Q3 skipped               -> 2, 1, 'false'
    #   carol -- rewatcher; only her newer session (Q2, Q3)     -> 2, 2, 'false'
    # carol's sso flag is 'true' (unique_id + auth_org); bob's auth_org without
    # a unique_id stays 'false' (this builder's own AND-predicate); dave's
    # missing email exercises this builder's own mobile fallback. This builder
    # ends with ORDER BY user_identifier: dave's "+9100..." mobile sorts before
    # the emails, which sort alice < bob < carol. The decoy learner is absent.
    assert rows == [
        (s.dave.mobile, "false", 1, 1, "false"),
        ("alice@example.com", "false", 3, 3, "true"),
        ("bob@example.com", "false", 2, 1, "false"),
        ("carol@example.com", "true", 2, 2, "false"),
    ]


def test_user_level_metrics_masked_identifier_is_md5_of_user_id(db, org_a):
    with in_workspace(org_a):
        s = _seed_metrics_timeline(org_a)

    rows = _run(
        get_user_level_metrics_query(
            s.plio.uuid, org_a.schema_name, show_unmasked_user_id=False
        )
    )

    # with masking on, each learner's user_identifier is the MD5 of their user
    # id (independent Python hashlib oracle). Masking touches only the
    # identifier: the rollup counts, the all-attempted flag, and the sso flag are
    # the same hand-computed literals as the unmasked rollup, and grouping stays
    # per-learner (carol's two sessions share one masked id, so her rollup still
    # reflects only the newer session). ORDER BY runs on the masked identifier,
    # whose lexicographic order is hash-dependent; the row *order* is pinned by
    # the unmasked spec, so here compare order-insensitively (multiset). Decoy
    # learner absent.
    assert Counter(rows) == Counter(
        [
            (_masked_identifier(s.alice.id), "false", 3, 3, "true"),
            (_masked_identifier(s.bob.id), "false", 2, 1, "false"),
            (_masked_identifier(s.carol.id), "true", 2, 2, "false"),
            (_masked_identifier(s.dave.id), "false", 1, 1, "false"),
        ]
    )
