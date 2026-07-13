"""Learner scorecard-math journeys.

A learner's score is how many questions they answered correctly. The backend's
scoring rule lives in the ``metrics`` endpoint: mcq/checkbox answers are correct
only on an exact match with the question's ``correct_answer``, while a
subjective answer counts as correct whenever it is non-empty. These specs build
answer sets across all three question types by driving the real
``/api/v1/sessions/`` and ``/api/v1/session-answers/`` APIs as a learner, then
assert the scores the creator's metrics endpoint reports. Every expected number
is hand-computed from the constructed answer set -- never recomputed by
re-running the app's grading.

Scenarios cover a fully answered session (mixed right/wrong across the three
types) and a partially answered session, exercising the "answered at least one"
and "answered them all" branches of the scoring. Slice-local helpers live in
this module to stay conflict-free with the parallel learner-session slice.
"""

from tests.factories import ItemFactory, PlioFactory, QuestionFactory


def _plio_with_one_question_per_type(owner):
    """A published plio owned by ``owner`` with one non-survey question of each
    type, each at a distinct time. Returns the plio and a ``{type: item}`` map.
    Factory correct answers: mcq -> option 0, checkbox -> options [0]."""
    plio = PlioFactory(created_by=owner, published=True, video__duration=30)
    items = {}
    for index, qtype in enumerate(["mcq", "checkbox", "subjective"]):
        item = ItemFactory(plio=plio, time=(index + 1) * 10)
        QuestionFactory(item=item, **{qtype: True})
        items[qtype] = item
    return plio, items


def _open_session(learner, plio):
    response = learner.post("/api/v1/sessions/", {"plio": plio.id}, format="json")
    assert response.status_code == 201, response.data
    return response.data


def _submit_answers(learner, session_answers, item_id_to_answer):
    """Answer only the items present in ``item_id_to_answer``; leave the rest
    untouched (unanswered)."""
    for entry in session_answers:
        if entry["item_id"] in item_id_to_answer:
            response = learner.patch(
                "/api/v1/session-answers/{}/".format(entry["id"]),
                {"answer": item_id_to_answer[entry["item_id"]]},
                format="json",
            )
            assert response.status_code == 200, response.data


def test_fully_answered_session_scores_across_all_three_types(creator, authed_client):
    plio, items = _plio_with_one_question_per_type(creator.user)
    mcq, checkbox, subjective = items["mcq"], items["checkbox"], items["subjective"]
    learner = authed_client()
    session = _open_session(learner, plio)

    # answer every question: mcq right, checkbox wrong, subjective answered.
    _submit_answers(
        learner,
        session["session_answers"],
        {
            mcq.id: 0,  # matches correct_answer 0 -> correct
            checkbox.id: [0, 1],  # != correct_answer [0] -> wrong
            subjective.id: "Cells are the unit of life",  # non-empty -> correct
        },
    )

    response = creator.get("/api/v1/plios/{}/metrics/".format(plio.uuid))
    assert response.status_code == 200

    assert response.data["unique_viewers"] == 1
    # attempted all 3 questions
    assert response.data["average_num_answered"] == 3
    # 2 correct (mcq + subjective) out of 3 answered -> round(2/3 * 100, 2)
    assert response.data["accuracy"] == 66.67
    # this learner answered every non-survey question -> 100% completion
    assert response.data["percent_completed"] == 100.0


def test_partially_answered_session_scores_only_the_attempted_questions(
    creator, authed_client
):
    plio, items = _plio_with_one_question_per_type(creator.user)
    learner = authed_client()
    session = _open_session(learner, plio)

    # answer only the mcq (correctly); leave checkbox and subjective unanswered.
    _submit_answers(learner, session["session_answers"], {items["mcq"].id: 0})

    response = creator.get("/api/v1/plios/{}/metrics/".format(plio.uuid))
    assert response.status_code == 200

    assert response.data["unique_viewers"] == 1
    # only 1 of 3 questions attempted
    assert response.data["average_num_answered"] == 1
    # 1 correct out of 1 answered -> accuracy is over attempted questions only
    assert response.data["accuracy"] == 100.0
    # did not answer all 3 -> not counted as completed
    assert response.data["percent_completed"] == 0.0
