"""Learner A/B-splitting journeys (learner side only).

An experiment splits traffic across two variant plios. Which arm a given learner
is assigned to is decided client-side (the backend's assignment endpoint is not
implemented). What the backend guarantees, and what these specs pin, is the pair
of facts a learner depends on: both arms of the experiment are independently
playable, and once a learner enters via the experiment link their assigned
variant is recorded faithfully on the session and stays put on re-read -- a
deterministic record of the arm they play, never a re-randomized one.

The experiments app's own CRUD is out of scope (#366): the experiment and its
arms are seeded directly, and no experiment API endpoint is exercised.
Slice-local helpers live in this module to stay conflict-free with the parallel
learner-session slice.
"""

from experiments.models import ExperimentPlio
from tests.factories import ExperimentFactory, PlioFactory


def _ab_experiment():
    """A 50/50 experiment across two published, public variant plios.
    Returns ``(experiment, control, variant)``."""
    experiment = ExperimentFactory()
    control = PlioFactory(published=True, is_public=True, video__duration=3)
    variant = PlioFactory(published=True, is_public=True, video__duration=3)
    ExperimentPlio.objects.create(
        experiment=experiment, plio=control, split_percentage=50
    )
    ExperimentPlio.objects.create(
        experiment=experiment, plio=variant, split_percentage=50
    )
    return experiment, control, variant


def test_both_experiment_variants_are_independently_playable(learner):
    _experiment, control, variant = _ab_experiment()

    control_play = learner.get("/api/v1/plios/{}/play/".format(control.uuid))
    variant_play = learner.get("/api/v1/plios/{}/play/".format(variant.uuid))

    assert control_play.status_code == 200, control_play.data
    assert variant_play.status_code == 200, variant_play.data
    # each arm serves its own distinct plio
    assert control_play.data["uuid"] == control.uuid
    assert variant_play.data["uuid"] == variant.uuid
    assert control.uuid != variant.uuid


def test_learner_entering_via_experiment_is_recorded_against_one_variant(learner):
    experiment, _control, variant = _ab_experiment()

    # the learner enters the experiment and is routed to the `variant` arm;
    # the session records exactly that (experiment, variant) assignment.
    session = learner.post(
        "/api/v1/sessions/",
        {"plio": variant.id, "experiment": experiment.id},
        format="json",
    )
    assert session.status_code == 201, session.data
    assert session.data["experiment"]["id"] == experiment.id
    assert session.data["plio"]["id"] == variant.id

    # deterministic: re-reading the session returns the same arm, not a
    # re-rolled one.
    reread = learner.get("/api/v1/sessions/{}/".format(session.data["id"]))
    assert reread.status_code == 200
    assert reread.data["experiment"]["id"] == experiment.id
    assert reread.data["plio"]["id"] == variant.id
