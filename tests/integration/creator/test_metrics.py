"""Creator metrics journeys.

The ``metrics`` endpoint reports usage numbers for a plio. Each spec constructs
a deliberately tiny timeline of sessions and answers with factories, then asserts
the API returns exactly the numbers worked out by hand from that timeline — the
expected values are literals derived from the scenario, never recomputed by
re-running the app's own aggregation. The viewer/answer scenarios keep video
durations under a minute so the one-minute-retention metric is intentionally
not-applicable; a dedicated scenario uses a 60-second video with hand-written
retention strings to pin the metric itself.
"""

from tests.factories import (
    ItemFactory,
    PlioFactory,
    QuestionFactory,
    SessionAnswerFactory,
    SessionFactory,
    UserFactory,
)


def test_viewers_and_average_watch_time_use_each_viewer_latest_session(creator):
    # video shorter than a minute -> one-minute retention is not applicable
    plio = PlioFactory(created_by=creator.user, video__duration=30)
    viewer_a = UserFactory()
    viewer_b = UserFactory()

    # viewer A watched twice; only the later (higher-id) session counts
    SessionFactory(plio=plio, user=viewer_a, watch_time=10)
    SessionFactory(plio=plio, user=viewer_a, watch_time=30)
    # viewer B watched once
    SessionFactory(plio=plio, user=viewer_b, watch_time=50)

    # decoy: another plio in the same workspace with its own session -- the
    # metrics below must not absorb it (an aggregation that lost its per-plio
    # predicate would report 3 viewers and a skewed average)
    decoy = PlioFactory(created_by=creator.user, video__duration=30)
    SessionFactory(plio=decoy, user=UserFactory(), watch_time=999)

    response = creator.get("/api/v1/plios/{}/metrics/".format(plio.uuid))
    assert response.status_code == 200

    # two distinct viewers
    assert response.data["unique_viewers"] == 2
    # mean of the latest watch time per viewer: (30 + 50) / 2 = 40.0;
    # viewer A's earlier 10s session is superseded
    assert response.data["average_watch_time"] == 40.0
    # 30s video (< 60s) -> retention-at-one-minute is not applicable
    assert response.data["percent_one_minute_retention"] is None
    # no questions on the plio -> the question metrics are not applicable
    assert response.data["accuracy"] is None
    assert response.data["average_num_answered"] is None
    assert response.data["percent_completed"] is None
    assert response.data["has_survey_question"] is False


def test_one_minute_retention_from_hand_written_retention_strings(creator):
    # 60-second video: the metric is applicable, and second 60 is index 59
    plio = PlioFactory(created_by=creator.user, video__duration=60)

    # viewer A was watching at the one-minute mark: "1" at index 59 only
    retained = ",".join(["0"] * 59 + ["1"])
    SessionFactory(plio=plio, user=UserFactory(), watch_time=60, retention=retained)
    # viewer B watched the first 30 seconds only: all zeros from index 30 on
    not_retained = ",".join(["1"] * 30 + ["0"] * 30)
    SessionFactory(plio=plio, user=UserFactory(), watch_time=30, retention=not_retained)
    # viewer C has an empty retention string (never persisted, see #392):
    # invalid for the metric, but still counted among unique viewers
    SessionFactory(plio=plio, user=UserFactory(), watch_time=0, retention="")

    response = creator.get("/api/v1/plios/{}/metrics/".format(plio.uuid))
    assert response.status_code == 200

    assert response.data["unique_viewers"] == 3
    # retained at one minute: viewer A only, out of ALL 3 unique viewers
    # (not just the 2 with valid strings): round(1/3 * 100, 2) = 33.33
    assert response.data["percent_one_minute_retention"] == 33.33


def test_question_metrics_from_a_constructed_answer_timeline(creator):
    plio = PlioFactory(created_by=creator.user, video__duration=30)
    # two non-survey MCQs, correct answer is option index 0 for both
    first_item = ItemFactory(plio=plio, time=10)
    QuestionFactory(item=first_item, mcq=True)
    second_item = ItemFactory(plio=plio, time=20)
    QuestionFactory(item=second_item, mcq=True)

    viewer_a = UserFactory()
    viewer_b = UserFactory()

    # viewer A answered both: first correct (0), second wrong (1)
    session_a = SessionFactory(plio=plio, user=viewer_a, watch_time=20)
    SessionAnswerFactory(session=session_a, item=first_item, answer=0)
    SessionAnswerFactory(session=session_a, item=second_item, answer=1)

    # viewer B opened both questions but skipped each (answer is null)
    session_b = SessionFactory(plio=plio, user=viewer_b, watch_time=40)
    SessionAnswerFactory(session=session_b, item=first_item, answer=None)
    SessionAnswerFactory(session=session_b, item=second_item, answer=None)

    # decoy: a second plio with a perfectly-answered question in the same
    # workspace -- accuracy/attempts/completion below must not absorb it
    decoy = PlioFactory(created_by=creator.user, video__duration=30)
    decoy_item = ItemFactory(plio=decoy, time=5)
    QuestionFactory(item=decoy_item, mcq=True)
    decoy_session = SessionFactory(plio=decoy, user=UserFactory(), watch_time=15)
    SessionAnswerFactory(session=decoy_session, item=decoy_item, answer=0)

    response = creator.get("/api/v1/plios/{}/metrics/".format(plio.uuid))
    assert response.status_code == 200

    assert response.data["unique_viewers"] == 2
    # mean latest watch time: (20 + 40) / 2 = 30.0
    assert response.data["average_watch_time"] == 30.0
    assert response.data["percent_one_minute_retention"] is None
    # accuracy averages each answering viewer's correct/attempted ratio, in %:
    # A answered 2, got 1 right -> 0.5; B answered 0 -> excluded. mean(0.5) = 50.0
    assert response.data["accuracy"] == 50.0
    # attempts per viewer: A=2, B=0; round(mean(2, 0)) = round(1.0) = 1
    assert response.data["average_num_answered"] == 1
    # viewers who attempted every question: A only -> 1 of 2 = 50.0%
    assert response.data["percent_completed"] == 50.0
    assert response.data["has_survey_question"] is False
