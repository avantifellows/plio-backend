"""Creator metrics journeys.

The ``metrics`` endpoint reports usage numbers for a plio. Each spec constructs
a deliberately tiny timeline of sessions and answers with factories, then asserts
the API returns exactly the numbers worked out by hand from that timeline — the
expected values are literals derived from the scenario, never recomputed by
re-running the app's own aggregation. Video durations are kept under a minute so
the one-minute-retention metric is intentionally not-applicable, keeping each
scenario small enough to verify by hand.
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
