"""Learner skip-rule journeys.

Whether a learner may skip a question is a per-plio policy the player reads from
the plio's ``config`` at play time (``settings.player.skipEnabled``). Enforcement
of the rule lives in the player; the backend's job is to hand the player the
right policy. These specs configure a plio with skipping enabled and, separately,
disabled, then assert the learner's real ``GET /api/v1/plios/{uuid}/play/``
response carries exactly that flag -- covering both configurations. The expected
value is the flag the plio was configured with.

Slice-local helpers live in this module to stay conflict-free with the parallel
learner-session slice.
"""

from tests.factories import PlioFactory


def _published_plio_with_skip(skip_enabled):
    # public + published so a learner outside the workspace can play it; the
    # skip policy is carried on the plio's settings config the player consumes.
    return PlioFactory(
        published=True,
        is_public=True,
        config={"settings": {"player": {"skipEnabled": skip_enabled}}},
    )


def _play_config(learner, plio):
    response = learner.get("/api/v1/plios/{}/play/".format(plio.uuid))
    assert response.status_code == 200, response.data
    return response.data["config"]["settings"]["player"]


def test_skip_enabled_is_exposed_to_the_learner_at_play_time(learner):
    plio = _published_plio_with_skip(skip_enabled=True)

    player_config = _play_config(learner, plio)

    assert player_config["skipEnabled"] is True


def test_skip_disabled_is_exposed_to_the_learner_at_play_time(learner):
    plio = _published_plio_with_skip(skip_enabled=False)

    player_config = _play_config(learner, plio)

    assert player_config["skipEnabled"] is False
