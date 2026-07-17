"""Learner watch-time journeys.

Watch time is seconds-of-video-watched, accumulated by the player from a
play/pause timeline and reported by the learner onto their session. The backend
stores that number and, in the creator's ``metrics`` endpoint, averages the
latest session per viewer. These specs construct deliberate play/pause
timelines, hand-compute the watched seconds as literals, report them through the
real ``/api/v1/sessions/`` API, and assert the API returns exactly those
literals -- first on the learner's own session read, then as the mean the
metrics endpoint computes across learners. Expected numbers are worked out by
hand from each timeline, never recomputed by re-running the app's aggregation.

Slice-local helpers live in this module to stay conflict-free with the parallel
learner-session slice.
"""

from tests.factories import PlioFactory


def _open_session(actor, plio):
    response = actor.post("/api/v1/sessions/", {"plio": plio.id}, format="json")
    assert response.status_code == 201, response.data
    return response.data


def _report_watch_time(actor, session_id, plio, watch_time):
    # a full update carrying the watch time the player accumulated so far;
    # PUT (not PATCH) so the serializer's update branch runs, as the player does.
    response = actor.client.put(
        "/api/v1/sessions/{}/".format(session_id),
        {"plio": plio.id, "watch_time": watch_time},
        format="json",
    )
    assert response.status_code == 200, response.data
    return response.data


def test_reported_watch_time_from_a_timeline_round_trips(learner):
    plio = PlioFactory(published=True, is_public=True, video__duration=60)
    session = _open_session(learner, plio)

    # timeline: play 0->pause 10 (watched 10s), then play 20->pause 45 (25s).
    # gap 10->20 is paused and not counted. total = 10 + 25 = 35.0 seconds.
    _report_watch_time(learner, session["id"], plio, 35.0)

    reread = learner.get("/api/v1/sessions/{}/".format(session["id"]))
    assert reread.status_code == 200
    assert reread.data["watch_time"] == 35.0


def test_average_watch_time_is_the_mean_of_each_learners_reported_time(
    creator, authed_client
):
    # the creator owns the plio (personal workspace) so they can read its metrics
    plio = PlioFactory(created_by=creator.user, published=True, video__duration=30)

    # learner A's timeline: play 0->pause 10 (10s) + play 20->pause 45 (25s) = 35.0
    learner_a = authed_client()
    session_a = _open_session(learner_a, plio)
    _report_watch_time(learner_a, session_a["id"], plio, 35.0)

    # learner B's timeline: play 0->pause 5 = 5.0
    learner_b = authed_client()
    session_b = _open_session(learner_b, plio)
    _report_watch_time(learner_b, session_b["id"], plio, 5.0)

    response = creator.get("/api/v1/plios/{}/metrics/".format(plio.uuid))
    assert response.status_code == 200

    # two distinct learners watched
    assert response.data["unique_viewers"] == 2
    # mean of the reported watch times: (35.0 + 5.0) / 2 = 20.0
    assert response.data["average_watch_time"] == 20.0
