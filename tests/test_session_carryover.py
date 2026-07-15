"""Pin the learner-resume carryover recursion at the Session model seam.

When a learner reopens a plio, the session read resumes them where they left
off: ``Session.last_global_event`` (the resume pointer) walks back recursively
through that learner's earlier sessions on the same plio, and
``Session.last_session`` picks the predecessor to recurse into. No unit test in
any lane instantiates an ``Event`` or exercises this recursion beyond one hop,
so an ORM manager or ordering shift in the Django 3.1 -> 5.2 upgrade could break
learner resume with CI green. Each spec here pins one edge of that recursion.

Oracle discipline: every expected value is the identity (``.id``) of a specific
event or session built by hand in the spec's own tiny timeline -- or ``None`` --
never a value produced by re-running the recursion. Timelines are deliberately
small (one learner, one plio, 2-3 sessions, 1-3 events) so the expected identity
is obvious by reading the construction. Sessions are created in PK order
(factories yield ascending ids), matching the ``id__lt`` / ``-id`` predecessor
selection; a session's own events are created oldest-first, so the ``-updated_at``
event ordering matches their creation order (``auto_now``/``auto_now_add``
strictly advance -- no sleeps, no timestamp literals). All data is built inside
``in_workspace(org_a)`` with the shared factories; properties are read directly
on the model, with no HTTP, no view, and no ``connection.set_schema()``.

This is the shared home for the whole entries unit fill (#376); later slices
append the soft-delete edges, the ``-updated_at`` re-save identity pin, the
cross-learner/cross-plio scoping decoys, and the ``SessionSerializer``
create-path carryover specs. This slice (#407) pins the recursion's core path.
It changes no product code -- the observed behaviour is pinned as-is.
"""

from tests.builders import in_workspace
from tests.factories import (
    EventFactory,
    PlioFactory,
    SessionFactory,
    UserFactory,
)


def test_first_session_has_no_predecessor_and_no_global_event(db, org_a):
    # A learner's only session on a plio, with no events: there is no earlier
    # session to recurse into and no event to resume from.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        session = SessionFactory(plio=plio, user=learner)

        assert session.last_session is None
        assert session.last_global_event is None


def test_session_with_own_events_returns_its_latest_event(db, org_a):
    # A session with its own events resumes from its most-recently-updated
    # event. The two events are created oldest-first, so the second is the
    # latest by ``-updated_at``.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        session = SessionFactory(plio=plio, user=learner)
        older_event = EventFactory(session=session)
        latest_event = EventFactory(session=session)

        assert latest_event.updated_at > older_event.updated_at
        assert session.last_global_event.id == latest_event.id


def test_own_events_beat_a_predecessors_later_event(db, org_a):
    # The recursion short-circuits on the current session's own events: even
    # when a predecessor holds an event updated *after* the current session's
    # own event, the resume pointer is the current session's own event. The
    # predecessor's event is created last, so it carries the later updated_at.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        predecessor = SessionFactory(plio=plio, user=learner)
        current = SessionFactory(plio=plio, user=learner)
        own_event = EventFactory(session=current)
        predecessor_later_event = EventFactory(session=predecessor)

        assert predecessor_later_event.updated_at > own_event.updated_at
        assert current.last_global_event.id == own_event.id


def test_one_hop_returns_predecessors_latest_event(db, org_a):
    # The current session has no events of its own, so the resume pointer comes
    # from its immediate predecessor -- that predecessor's latest event.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        predecessor = SessionFactory(plio=plio, user=learner)
        older_event = EventFactory(session=predecessor)
        predecessor_latest = EventFactory(session=predecessor)
        current = SessionFactory(plio=plio, user=learner)

        assert predecessor_latest.updated_at > older_event.updated_at
        assert current.last_global_event.id == predecessor_latest.id


def test_multi_hop_walks_chain_to_event_bearing_session(db, org_a):
    # Two event-less sessions stacked atop an event-bearing one: the recursion
    # walks back through both empty sessions to the earliest session's latest
    # event.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        event_bearing = SessionFactory(plio=plio, user=learner)
        older_event = EventFactory(session=event_bearing)
        bottom_latest = EventFactory(session=event_bearing)
        SessionFactory(plio=plio, user=learner)  # event-less middle
        current = SessionFactory(plio=plio, user=learner)  # event-less top

        assert bottom_latest.updated_at > older_event.updated_at
        assert current.last_global_event.id == bottom_latest.id


def test_all_event_less_chain_exhausts_to_none(db, org_a):
    # A chain of sessions none of which has any event: the recursion walks to
    # the first session, finds no predecessor, and returns None.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        SessionFactory(plio=plio, user=learner)
        SessionFactory(plio=plio, user=learner)
        current = SessionFactory(plio=plio, user=learner)

        assert current.last_global_event is None


def test_last_session_is_nearest_predecessor_by_pk(db, org_a):
    # Predecessor selection is PK-based: among three sessions built in PK order
    # for one learner-plio pair, the third's ``last_session`` is the second
    # (the nearest earlier session by id), not the first.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        first = SessionFactory(plio=plio, user=learner)
        second = SessionFactory(plio=plio, user=learner)
        third = SessionFactory(plio=plio, user=learner)

        assert first.id < second.id < third.id
        assert third.last_session.id == second.id
