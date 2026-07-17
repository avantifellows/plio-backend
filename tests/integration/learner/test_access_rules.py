"""Learner play-time access journeys.

Playback obeys a plio's visibility: a *public* plio plays for any authenticated
learner, even one who neither created it nor belongs to the workspace, while a
*private* plio refuses everyone but its creator. These specs drive the real
``GET /api/v1/plios/{uuid}/play/`` endpoint through a learner who sits outside
the workspace and observe only the HTTP response -- the play queryset itself is
the visibility gate under test.

The org/tenancy slice owns the who-gets-in permission *matrix*; this slice owns
what a learner experiences at play time. Slice-local helpers live in this module
to stay conflict-free with the parallel learner-session slice.
"""

from tests.factories import PlioFactory


def _play(actor, plio):
    return actor.get("/api/v1/plios/{}/play/".format(plio.uuid))


def test_public_plio_plays_for_a_learner_outside_the_workspace(learner):
    # created by someone else; the learner is not its creator and not a member
    plio = PlioFactory(published=True, is_public=True)

    response = _play(learner, plio)

    assert response.status_code == 200, response.data
    # the learner receives the plio they asked to play
    assert response.data["uuid"] == plio.uuid


def test_private_plio_refuses_a_learner_outside_the_workspace(learner):
    plio = PlioFactory(published=True, is_public=False)

    response = _play(learner, plio)

    # a private plio is invisible at play time to anyone but its creator
    assert response.status_code == 404


def test_private_plio_still_plays_for_its_own_creator(authed_client):
    # the refusal above is access-based, not existence-based: the very same
    # private plio plays for the creator who owns it.
    owner = authed_client()
    plio = PlioFactory(published=True, is_public=False, created_by=owner.user)

    response = _play(owner, plio)

    assert response.status_code == 200, response.data
    assert response.data["uuid"] == plio.uuid
