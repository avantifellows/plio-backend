"""Learner event-stream journeys.

Played/paused/skipped events are recorded within a session, and the latest event
is where a resumed learner picks up -- both within the same session and, on
reopening the plio, carried over from the previous session. Specs drive the real
``/api/v1/events/`` and ``/api/v1/sessions/`` APIs and observe the resumption
pointer through the session read's ``last_event``; the identity of the "latest"
event is taken from the response of the event the learner posted last, not
recomputed from the app.

Slice-local helpers live in this module to stay conflict-free with the parallel
learner-progress slice.
"""

from tests.factories import PlioFactory


def _published_plio():
    return PlioFactory(published=True, video__duration=3)


def _record_event(learner, session_id, event_type, player_time):
    response = learner.post(
        "/api/v1/events/",
        {"session": session_id, "type": event_type, "player_time": player_time},
        format="json",
    )
    assert response.status_code == 201, response.data
    return response.data


def test_latest_recorded_event_is_the_resumption_point(learner):
    plio = _published_plio()
    session = learner.post("/api/v1/sessions/", {"plio": plio.id}, format="json")
    assert session.status_code == 201
    session_id = session.data["id"]

    # the learner plays, pauses, then skips a question -- in that order
    _record_event(learner, session_id, "played", 5)
    _record_event(learner, session_id, "paused", 12)
    latest = _record_event(learner, session_id, "question_skipped", 20)

    # re-reading the session resumes at the last event recorded
    resumed = learner.get("/api/v1/sessions/{}/".format(session_id))
    assert resumed.status_code == 200
    assert resumed.data["last_event"]["id"] == latest["id"]
    assert resumed.data["last_event"]["type"] == "question_skipped"
    assert resumed.data["last_event"]["player_time"] == 20


def test_new_session_resumes_at_previous_sessions_latest_event(learner):
    plio = _published_plio()
    first = learner.post("/api/v1/sessions/", {"plio": plio.id}, format="json")
    assert first.status_code == 201
    _record_event(learner, first.data["id"], "played", 5)
    latest = _record_event(learner, first.data["id"], "paused", 18)

    # reopening the plio makes a new session, but resumption still points at the
    # last event of the previous session (which has no events of its own yet)
    second = learner.post("/api/v1/sessions/", {"plio": plio.id}, format="json")
    assert second.status_code == 201
    assert second.data["id"] != first.data["id"]
    assert second.data["last_event"]["id"] == latest["id"]
    assert second.data["last_event"]["type"] == "paused"
    assert second.data["last_event"]["player_time"] == 18
