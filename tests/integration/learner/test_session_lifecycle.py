"""Learner session-lifecycle journeys.

A learner opening a plio creates a session; reopening the same plio creates a
*new* session that carries retention, watch time, answers, and the last event
over from that learner's previous session on the same plio. These specs drive
the real ``/api/v1/sessions/`` API through the ``learner`` actor and observe
behaviour through responses and subsequent reads only -- never by reaching
across schemas or into internal queries. Expected values (retention strings,
carried-over numbers) are stated as literals derived from the constructed
scenario, not recomputed from the app's own logic.

Slice-local helpers live in this module to stay conflict-free with the parallel
learner-progress slice.
"""

from tests.factories import PlioFactory


def _published_plio(duration):
    """A published plio in the personal workspace with a video of ``duration``
    seconds. Learners play it with no ``Organization`` header, so it lives in
    the schema requests land in by default."""
    return PlioFactory(published=True, video__duration=duration)


def test_first_visit_creates_a_first_session(learner):
    plio = _published_plio(duration=3)

    response = learner.post("/api/v1/sessions/", {"plio": plio.id}, format="json")

    assert response.status_code == 201, response.data
    # the very first session for this learner-plio pair
    assert response.data["is_first"] is True
    # a fresh session starts with zero watch time and a zeroed retention string
    # (one "0" per second of the 3-second video)
    assert response.data["watch_time"] == 0
    assert response.data["retention"] == "0,0,0"

    # the zeroed retention string is only assigned in memory after the row is
    # created, so it is never persisted: a fresh read returns the model default
    # "" (pre-existing bug, tracked in #392 -- update this literal to "0,0,0"
    # when it is fixed)
    fresh = learner.get("/api/v1/sessions/{}/".format(response.data["id"]))
    assert fresh.status_code == 200, fresh.data
    assert fresh.data["watch_time"] == 0
    assert fresh.data["retention"] == ""


def test_reopening_creates_a_new_session_carrying_over_state(learner):
    plio = _published_plio(duration=3)

    # first visit
    first = learner.post("/api/v1/sessions/", {"plio": plio.id}, format="json")
    assert first.status_code == 201
    assert first.data["is_first"] is True

    # the learner progresses through the video: record watch time and retention
    updated = learner.client.put(
        "/api/v1/sessions/{}/".format(first.data["id"]),
        {"plio": plio.id, "watch_time": 5.0, "retention": "1,1,0"},
        format="json",
    )
    assert updated.status_code == 200

    # reopening the same plio -> a brand-new session row, not the first anymore,
    # carrying over the watch time and retention from the previous session
    second = learner.post("/api/v1/sessions/", {"plio": plio.id}, format="json")
    assert second.status_code == 201
    assert second.data["id"] != first.data["id"]
    assert second.data["is_first"] is False
    assert second.data["watch_time"] == 5.0
    assert second.data["retention"] == "1,1,0"


def test_a_first_session_does_not_inherit_another_learners_state(
    learner, authed_client
):
    # carry-over is scoped per learner: A's progress on a plio must not bleed
    # into B's *first* session on the same plio. Without this, carry-over that
    # stopped filtering by user passes every learner spec (each one reuses a
    # single actor).
    plio = _published_plio(duration=3)

    # learner A builds up state on the plio
    a_first = learner.post("/api/v1/sessions/", {"plio": plio.id}, format="json")
    assert a_first.status_code == 201
    updated = learner.client.put(
        "/api/v1/sessions/{}/".format(a_first.data["id"]),
        {"plio": plio.id, "watch_time": 9.0, "retention": "1,1,1"},
        format="json",
    )
    assert updated.status_code == 200
    # ...including a recorded event: last_event flows through its own
    # per-learner lookup path, separate from the field carry-over
    recorded = learner.post(
        "/api/v1/events/",
        {"session": a_first.data["id"], "type": "played", "player_time": 2},
        format="json",
    )
    assert recorded.status_code == 201

    # learner B's first visit to the same plio: a fresh first session with
    # none of A's watch time, retention, or events
    learner_b = authed_client()
    b_first = learner_b.post("/api/v1/sessions/", {"plio": plio.id}, format="json")
    assert b_first.status_code == 201
    assert b_first.data["is_first"] is True
    assert b_first.data["watch_time"] == 0
    assert b_first.data["retention"] == "0,0,0"
    # no event identity leaked from A: a fresh session's last_event is an
    # all-None husk (today's serializer shape), never A's recorded event
    last_event = b_first.data["last_event"] or {}
    assert last_event.get("id") is None
    assert last_event.get("type") is None


def test_a_session_does_not_inherit_from_a_different_plio(learner):
    # carry-over is scoped per plio: a prior session on plio A must not bleed
    # into the learner's first session on plio B.
    plio_a = _published_plio(duration=3)
    plio_b = _published_plio(duration=5)

    # the learner watches plio A and builds up some state there
    on_a = learner.post("/api/v1/sessions/", {"plio": plio_a.id}, format="json")
    assert on_a.status_code == 201
    updated_a = learner.client.put(
        "/api/v1/sessions/{}/".format(on_a.data["id"]),
        {"plio": plio_a.id, "watch_time": 7.0, "retention": "1,1,1"},
        format="json",
    )
    assert updated_a.status_code == 200

    # first visit to plio B: a fresh first session, none of plio A's state
    on_b = learner.post("/api/v1/sessions/", {"plio": plio_b.id}, format="json")
    assert on_b.status_code == 201
    assert on_b.data["is_first"] is True
    assert on_b.data["watch_time"] == 0
    # retention is freshly zeroed to plio B's own 5-second duration, not A's 3
    assert on_b.data["retention"] == "0,0,0,0,0"
