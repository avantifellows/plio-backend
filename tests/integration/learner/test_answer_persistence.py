"""Learner answer-persistence journeys.

Submitting an answer to an item persists one session answer per item per
session; the answer survives a subsequent read and is carried forward into a
new session on the same plio. Specs cover all three question types (mcq,
checkbox, subjective) built from the harness factory's question-type traits,
and drive only the real ``/api/v1/sessions/`` and ``/api/v1/session-answers/``
APIs. Expected answers are the literals the learner submits (a storage round
trip), never values recomputed from the app.

Slice-local helpers live in this module to stay conflict-free with the parallel
learner-progress slice.
"""

from tests.factories import ItemFactory, PlioFactory, QuestionFactory

# the answer payload each question type stores: an option index for mcq, a list
# of indices for checkbox, and free text for subjective.
ANSWERS_BY_TYPE = {
    "mcq": 0,
    "checkbox": [0, 1],
    "subjective": "Because the mitochondria is the powerhouse of the cell",
}


def _published_plio_with_one_item_per_type():
    """A published plio with one item per question type, each at a distinct
    time so session answers come back in a stable order. Returns the plio and a
    ``{question_type: item}`` map."""
    plio = PlioFactory(published=True, video__duration=3)
    items = {}
    for index, qtype in enumerate(["mcq", "checkbox", "subjective"]):
        item = ItemFactory(plio=plio, time=(index + 1) * 10)
        QuestionFactory(item=item, **{qtype: True})
        items[qtype] = item
    return plio, items


def _answer_each_item(learner, session_answers, item_id_to_answer):
    """Submit the given answer for each session answer, keyed by its item."""
    for entry in session_answers:
        answer = item_id_to_answer[entry["item_id"]]
        response = learner.patch(
            "/api/v1/session-answers/{}/".format(entry["id"]),
            {"answer": answer},
            format="json",
        )
        assert response.status_code == 200, response.data


def test_answers_persist_per_question_type_and_survive_a_read(learner):
    plio, items = _published_plio_with_one_item_per_type()
    expected = {items[qtype].id: answer for qtype, answer in ANSWERS_BY_TYPE.items()}

    session = learner.post("/api/v1/sessions/", {"plio": plio.id}, format="json")
    assert session.status_code == 201
    # one empty session answer per item, all initially unanswered
    assert len(session.data["session_answers"]) == 3
    assert all(entry["answer"] is None for entry in session.data["session_answers"])

    _answer_each_item(learner, session.data["session_answers"], expected)

    # subsequent read: every answer persisted, one row per item
    reread = learner.get("/api/v1/sessions/{}/".format(session.data["id"]))
    assert reread.status_code == 200
    persisted = {e["item_id"]: e["answer"] for e in reread.data["session_answers"]}
    assert persisted == expected


def test_answers_carry_forward_into_a_new_session(learner):
    plio, items = _published_plio_with_one_item_per_type()
    expected = {items[qtype].id: answer for qtype, answer in ANSWERS_BY_TYPE.items()}

    first = learner.post("/api/v1/sessions/", {"plio": plio.id}, format="json")
    assert first.status_code == 201
    _answer_each_item(learner, first.data["session_answers"], expected)

    # reopening the plio -> a new session whose answers are carried over
    second = learner.post("/api/v1/sessions/", {"plio": plio.id}, format="json")
    assert second.status_code == 201
    assert second.data["is_first"] is False
    carried = {e["item_id"]: e["answer"] for e in second.data["session_answers"]}
    assert carried == expected
