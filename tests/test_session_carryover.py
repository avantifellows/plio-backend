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

This is the shared home for the whole entries unit fill (#376). Slice #407
pinned the recursion's core path; slice #408 adds the deletion, ordering-identity,
and scoping edges: soft-deleted sessions and events skipped by the walk, the
session -> event ``SOFT_DELETE_CASCADE``, chain exhaustion by deletion, the
``-updated_at`` re-save identity pin, and the cross-learner/cross-plio scoping
decoys. A later slice appends the ``SessionSerializer`` create-path carryover
specs. It changes no product code -- the observed behaviour is pinned as-is.
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


def test_soft_deleted_mid_chain_session_is_skipped_by_both_properties(db, org_a):
    # A soft-deleted session mid-chain is invisible to the safedelete manager, so
    # both properties step past it to the live session before it. ``mid`` holds
    # its own event, which would be the resume point if it were not skipped; the
    # deletion makes the pointer fall back to ``bottom``'s event instead.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        bottom = SessionFactory(plio=plio, user=learner)
        bottom_event = EventFactory(session=bottom)
        mid = SessionFactory(plio=plio, user=learner)
        EventFactory(session=mid)  # would win if mid were not skipped
        current = SessionFactory(plio=plio, user=learner)  # event-less

        mid.delete()  # soft delete via the model, not raw SQL

        # last_session steps over the soft-deleted mid to the live predecessor
        assert current.last_session.id == bottom.id
        # and the resume pointer is bottom's event, not the skipped mid's
        assert current.last_global_event.id == bottom_event.id


def test_soft_deleting_a_session_cascades_and_hides_its_events(db, org_a):
    # SOFT_DELETE_CASCADE ties a session's events to the session: deleting the
    # session takes its events with it. ``mid`` holds the most-recently-updated
    # event of the whole chain, so if it leaked it would win the resume pointer;
    # the cascade removes it from mid's own relation and from the walk.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        bottom = SessionFactory(plio=plio, user=learner)
        bottom_event = EventFactory(session=bottom)
        mid = SessionFactory(plio=plio, user=learner)
        mid_event = EventFactory(session=mid)  # newest event in the chain
        current = SessionFactory(plio=plio, user=learner)  # event-less

        assert mid_event.updated_at > bottom_event.updated_at
        assert mid.event_set.first().id == mid_event.id  # live before deletion

        mid.delete()  # cascades to mid's events (via the model, not raw SQL)

        # the cascade removed mid's event: it is gone from mid's own relation ...
        assert mid.event_set.first() is None
        # ... and never surfaces in the walk, which resumes from bottom's event
        assert current.last_global_event.id == bottom_event.id


def test_soft_deleted_latest_event_falls_back_to_next_latest_live_event(db, org_a):
    # Deleting a single event (not its session) is invisible to the safedelete
    # ``event_set`` manager: the predecessor's newest event is removed directly,
    # so the resume pointer falls back to the next-latest event still live.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        predecessor = SessionFactory(plio=plio, user=learner)
        older_event = EventFactory(session=predecessor)
        latest_event = EventFactory(session=predecessor)
        current = SessionFactory(plio=plio, user=learner)  # event-less

        assert latest_event.updated_at > older_event.updated_at
        assert current.last_global_event.id == latest_event.id  # baseline

        latest_event.delete()  # soft delete the single event, not the session

        # the resume pointer falls back to the next-latest live event
        assert current.last_global_event.id == older_event.id


def test_all_predecessors_soft_deleted_exhausts_to_none(db, org_a):
    # When every earlier session for the learner-plio pair is soft-deleted, the
    # safedelete manager hides them all: last_session finds no live predecessor
    # and both properties return None. The predecessors carry events, proving
    # even event-bearing history cannot leak once its sessions are gone.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        first = SessionFactory(plio=plio, user=learner)
        EventFactory(session=first)
        second = SessionFactory(plio=plio, user=learner)
        EventFactory(session=second)
        current = SessionFactory(plio=plio, user=learner)  # event-less

        first.delete()
        second.delete()

        assert current.last_session is None
        assert current.last_global_event is None


def test_resaving_an_older_event_moves_the_resume_point(db, org_a):
    # Event ordering is ``-updated_at``, not creation order. The predecessor's
    # two events are created oldest-first, so ``newer_event`` is the resume point
    # to begin with. Re-saving ``older_event`` advances its ``updated_at``
    # (``auto_now`` strictly increases on save -- no sleeps, no timestamp
    # literals) past ``newer_event``, making the re-saved older event win.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        predecessor = SessionFactory(plio=plio, user=learner)
        older_event = EventFactory(session=predecessor)
        newer_event = EventFactory(session=predecessor)
        current = SessionFactory(plio=plio, user=learner)  # event-less

        assert newer_event.updated_at > older_event.updated_at
        assert current.last_global_event.id == newer_event.id  # baseline

        older_event.save()  # auto_now advances updated_at past newer_event
        older_event.refresh_from_db()

        assert older_event.updated_at > newer_event.updated_at
        assert current.last_global_event.id == older_event.id


def test_decoys_from_other_learner_and_other_plio_stay_out_of_the_chain(db, org_a):
    # The chain is scoped to one learner-plio pair. Two decoys live in the same
    # workspace with strictly later events and lower ids than ``current``: a
    # different learner on the same plio, and the same learner on a different
    # plio. A dropped user_id or plio_id filter in last_session would select a
    # decoy (they are the nearest ids below current); neither may enter the chain.
    with in_workspace(org_a):
        learner = UserFactory()
        other_learner = UserFactory()
        plio = PlioFactory()
        other_plio = PlioFactory()

        real_predecessor = SessionFactory(plio=plio, user=learner)
        real_event = EventFactory(session=real_predecessor)
        # decoy: another learner on the SAME plio, with a strictly later event
        other_learner_session = SessionFactory(plio=plio, user=other_learner)
        other_learner_event = EventFactory(session=other_learner_session)
        # decoy: the SAME learner on ANOTHER plio, with a strictly later event
        other_plio_session = SessionFactory(plio=other_plio, user=learner)
        other_plio_event = EventFactory(session=other_plio_session)
        # the learner's current session on the real plio, event-less
        current = SessionFactory(plio=plio, user=learner)

        # both decoys precede current by id (so a dropped scope filter would pick
        # them) and carry strictly later events than the real chain
        assert other_learner_session.id < current.id
        assert other_plio_session.id < current.id
        assert other_learner_event.updated_at > real_event.updated_at
        assert other_plio_event.updated_at > real_event.updated_at

        # neither decoy enters the chain: both properties resolve to the real pair
        assert current.last_session.id == real_predecessor.id
        assert current.last_global_event.id == real_event.id
