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
decoys. Slice #409 then adds the module's one *secondary* seam -- two
``SessionSerializer`` create-path specs -- pinning the retention/answer carryover
across a soft-deleted predecessor: the fallback to the nearest *live* predecessor,
and the fresh start when the whole history is soft-deleted. Those specs are
grouped at the end of the module below the model-seam specs. A later slice
ratchets the backend-unit coverage floor. This module changes no product code --
the observed behaviour, quirks included, is pinned as-is.
"""

from types import SimpleNamespace

import pytest

from entries.serializers import SessionSerializer
from tests.builders import in_workspace
from tests.factories import (
    EventFactory,
    ExperimentFactory,
    ItemFactory,
    PlioFactory,
    SessionAnswerFactory,
    SessionFactory,
    UserFactory,
    VideoFactory,
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
    # from its immediate predecessor -- that predecessor's latest event. A
    # *farther* event-bearing predecessor exists too, and its event is touched
    # last: the recursion must stop at the *nearer* event-bearing session, so a
    # flat "latest event across all my sessions" lookup (which would pick the
    # most recently updated event) fails here.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        farther = SessionFactory(plio=plio, user=learner)
        farther_event = EventFactory(session=farther)
        predecessor = SessionFactory(plio=plio, user=learner)
        older_event = EventFactory(session=predecessor)
        predecessor_latest = EventFactory(session=predecessor)
        current = SessionFactory(plio=plio, user=learner)
        # touch the farther session's event so update-recency opposes
        # session-chain nearness
        farther_event.save()
        farther_event.refresh_from_db()

        assert predecessor_latest.updated_at > older_event.updated_at
        assert farther_event.updated_at > predecessor_latest.updated_at
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
    # (the nearest earlier session by id), not the first. The first session is
    # re-saved *after* everything else so its updated_at is the newest --
    # timestamp-based ordering (-updated_at) would pick it and fail here.
    with in_workspace(org_a):
        learner = UserFactory()
        plio = PlioFactory()
        first = SessionFactory(plio=plio, user=learner)
        second = SessionFactory(plio=plio, user=learner)
        third = SessionFactory(plio=plio, user=learner)
        first.save()
        first.refresh_from_db()

        assert first.id < second.id < third.id
        assert first.updated_at > second.updated_at
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


# --- Secondary seam: the SessionSerializer create path (#409) --------------
#
# The retention/answer carryover copy lives in ``SessionSerializer.create``, not
# on the model, so its soft-delete edges are invisible at the model seam above.
# These two specs drive the serializer directly -- no HTTP client -- with a
# slice-local fake view context, per the fill's decided serializer seam. Nothing
# here graduates to the shared harness.


def _create_session_via_serializer(plio, user):
    """Run the full serializer create lifecycle and return the new Session.

    Slice-local on purpose. The serializer only needs ``context['view'].action``
    to be ``"create"`` (the update branch of ``validate`` is the only reader of
    ``view.kwargs``, and this drives create), and the user is passed explicitly
    in the data rather than via a request -- so a bare ``SimpleNamespace`` stands
    in for the view with no HTTP client. Driving ``is_valid`` then ``save``
    exercises the ``is_first`` assignment in ``validate`` together with the
    create-path carryover copy.
    """
    serializer = SessionSerializer(
        data={"plio": plio.id, "user": user.id},
        context={"view": SimpleNamespace(action="create")},
    )
    serializer.is_valid(raise_exception=True)
    return serializer.save()


def test_create_carries_over_from_nearest_live_predecessor(db, org_a):
    """Session-create falls back to the nearest *live* predecessor.

    Timeline: one learner on one published plio (two items). *Two* live
    sessions precede the deleted one, each with distinctive retention, watch
    time, has-video-played, and a session answer per item; the immediate
    predecessor is soft-deleted. The safedelete manager hides the deleted
    successor, so the create path's own predecessor query must resolve to the
    *newest live* session (not the oldest, not an arbitrary one): the created
    session copies that session's three carryover fields and its answers, and
    ``is_first`` is False. The soft-deleted successor's and the oldest live
    session's distinctive values must appear nowhere.

    Experiment carryover is a pinned quirk, and it is why the live predecessor
    here owns no experiment. The create path copies the predecessor's fields from
    ``SessionSerializer(last_session).data``, whose ``to_representation`` renders
    the experiment as a serialized *dict*; assigning that dict back to the
    ``Session.experiment`` foreign key raises ``ValueError``, so a live
    predecessor that owns an experiment cannot be carried over at all today
    (a product fix is out of scope for this test-only fill). The created
    session's experiment is therefore carried as ``None``. The factory-built
    experiment instead hangs on the *soft-deleted* successor, where it doubles as
    a wrong-pick tripwire: were the safedelete manager to stop hiding the deleted
    successor, the create path would try to copy that experiment dict and raise,
    turning a silent wrong-predecessor regression into a loud one.

    Every expected value is a literal from this timeline -- the live session's own
    field values and item/answer pairs -- never recomputed by re-running the
    serializer.
    """
    with in_workspace(org_a):
        creator = UserFactory()
        video = VideoFactory(duration=4)
        plio = PlioFactory(published=True, video=video, created_by=creator)
        item_a = ItemFactory(plio=plio, time=1)
        item_b = ItemFactory(plio=plio, time=2)
        learner = UserFactory()

        # an even older live session with its own distinct state: among
        # multiple live candidates the create path must pick the *newest*
        # live one, so a query that picked the oldest (or an arbitrary) live
        # session would carry these values and fail below
        oldest_live = SessionFactory(
            plio=plio,
            user=learner,
            retention="0,1,0,0",
            watch_time=5.0,
            has_video_played=False,
        )
        SessionAnswerFactory(session=oldest_live, item=item_a, answer=0)
        SessionAnswerFactory(session=oldest_live, item=item_b, answer=1)

        # newer LIVE predecessor: unmistakable, non-default carryover values and
        # one answer per item, no experiment (see the docstring quirk)
        live = SessionFactory(
            plio=plio,
            user=learner,
            retention="1,1,1,0",
            watch_time=42.0,
            has_video_played=True,
        )
        SessionAnswerFactory(session=live, item=item_a, answer=2)
        SessionAnswerFactory(session=live, item=item_b, answer=3)

        # newer session -- the immediate predecessor -- with different values, a
        # factory-built experiment (the wrong-pick tripwire), then soft-deleted
        deleted = SessionFactory(
            plio=plio,
            user=learner,
            retention="9,9,9,9",
            watch_time=99.0,
            has_video_played=False,
            experiment=ExperimentFactory(created_by=creator),
        )
        SessionAnswerFactory(session=deleted, item=item_a, answer=7)
        SessionAnswerFactory(session=deleted, item=item_b, answer=8)
        deleted.delete()  # soft delete via the model, not raw SQL

        created = _create_session_via_serializer(plio, learner)

        # the deleted successor is the nearest predecessor by id; the live one is
        # older -- so a pick that ignored the soft delete would take the
        # successor, and a pick that ignored recency would take oldest_live
        assert oldest_live.id < live.id < deleted.id < created.id

        # the three carryover fields come from the live predecessor, as literals
        assert created.retention == "1,1,1,0"
        assert created.watch_time == 42.0
        assert created.has_video_played is True
        # experiment carried as None from the live predecessor -- not the deleted
        # successor's experiment (whose dict copy would have raised)
        assert created.experiment_id is None
        # a live predecessor exists, so this is not the learner's first session
        assert created.is_first is False

        # the answers replicate the live predecessor's item/answer pairs exactly
        answers = sorted(
            created.sessionanswer_set.values_list("item_id", "answer"),
            key=lambda pair: pair[0],
        )
        assert answers == [(item_a.id, 2), (item_b.id, 3)]

        # the soft-deleted successor's distinctive values and answers appear
        # nowhere on the created session
        assert created.retention != "9,9,9,9"
        assert created.watch_time != 99.0
        assert 7 not in [answer for _item_id, answer in answers]
        assert 8 not in [answer for _item_id, answer in answers]


def test_create_with_experiment_bearing_live_predecessor_raises(db, org_a):
    """Bug #391 pinned at the serializer seam: an experiment-bearing *live*
    predecessor makes session-create raise.

    The carryover copies fields from ``SessionSerializer(last_session).data``,
    where ``to_representation`` renders a non-null experiment as a serialized
    *dict*; ``Session.objects.create`` then rejects that dict for the
    ``experiment`` foreign key with ``ValueError``. Today that surfaces as a 500
    on reopening any plio whose live predecessor carries an experiment --
    tracked as #391, out of scope for this test-only fill. When #391 is fixed,
    flip this to assert the carried-over experiment instead.
    """
    with in_workspace(org_a):
        creator = UserFactory()
        video = VideoFactory(duration=4)
        plio = PlioFactory(published=True, video=video, created_by=creator)
        learner = UserFactory()
        SessionFactory(
            plio=plio,
            user=learner,
            experiment=ExperimentFactory(created_by=creator),
        )

        with pytest.raises(ValueError, match="experiment"):
            _create_session_via_serializer(plio, learner)


def test_create_starts_fresh_when_all_predecessors_soft_deleted(db, org_a):
    """A learner whose whole history is soft-deleted is treated as brand new.

    Quirk pinned as-is: when every earlier session for the learner-plio pair is
    soft-deleted, the create path's predecessor query (safedelete manager) finds
    none, so the new session starts fresh -- a zeroed retention string sized to
    the video duration, one empty answer per item, and ``is_first`` True again --
    exactly as if the learner had never visited. The soft-deleted session's
    retention and answer never resurface. A product fix (e.g. keeping
    ``is_first`` False, or carrying from soft-deleted history) is out of scope for
    this test-only fill.

    The video duration is a small integer (4) so the zeroed retention is a
    hand-written literal, ``"0,0,0,0"`` (four zeroes, comma-joined). The create
    path sets that string on the returned in-memory session and does not persist
    it, so the assertion reads the returned object -- the same value the HTTP
    response serializes -- rather than re-reading the row. Every expected value
    is a literal from this timeline, never recomputed by re-running the
    serializer.
    """
    with in_workspace(org_a):
        creator = UserFactory()
        video = VideoFactory(duration=4)
        plio = PlioFactory(published=True, video=video, created_by=creator)
        item_a = ItemFactory(plio=plio, time=1)
        item_b = ItemFactory(plio=plio, time=2)
        learner = UserFactory()

        # the learner's only prior session, with a non-default retention and an
        # answer -- then soft-deleted so no live history remains
        only = SessionFactory(plio=plio, user=learner, retention="1,2,3,4")
        SessionAnswerFactory(session=only, item=item_a, answer=5)
        only.delete()  # soft delete via the model, not raw SQL

        created = _create_session_via_serializer(plio, learner)

        # fresh start: zeroed retention sized to the duration-4 video, hand-written
        assert created.retention == "0,0,0,0"
        # the whole history being soft-deleted resets is_first to True (the quirk)
        assert created.is_first is True

        # exactly one empty (null-answer) session answer per item
        answers = sorted(
            created.sessionanswer_set.values_list("item_id", "answer"),
            key=lambda pair: pair[0],
        )
        assert answers == [(item_a.id, None), (item_b.id, None)]

        # the soft-deleted session's retention and answer do not resurface
        assert created.retention != "1,2,3,4"
        assert 5 not in [answer for _item_id, answer in answers]
