"""Creator duplicate journeys.

Duplicating a plio clones its full graph — video, items, questions — into the
same workspace as an independent draft. The clone shares no rows with the
original: editing the copy leaves the source untouched. The graph is seeded with
factories (shared test vocabulary) and every observation goes through the real
``/api/v1/`` API; no spec touches ``connection.set_schema()``.
"""

from tests.factories import ItemFactory, PlioFactory, QuestionFactory


def _seed_two_question_plio(owner):
    # a published plio with two timed questions of different types
    plio = PlioFactory(created_by=owner, published=True)
    first_item = ItemFactory(plio=plio, time=10)
    first_question = QuestionFactory(item=first_item, mcq=True, text="Q-one")
    second_item = ItemFactory(plio=plio, time=20)
    QuestionFactory(item=second_item, subjective=True, text="Q-two")
    return plio, first_question


def test_duplicate_clones_full_graph_as_independent_draft(creator):
    original, _ = _seed_two_question_plio(creator.user)

    response = creator.post("/api/v1/plios/{}/duplicate/".format(original.uuid))
    assert response.status_code == 200
    copy = response.data

    # the clone is a distinct plio, always a draft, with its own fresh video —
    # even though the source was published
    assert copy["uuid"] != original.uuid
    assert copy["status"] == "draft"
    assert copy["video"]["id"] != original.video.id

    # the whole graph came across in item-time order with content intact
    items = copy["items"]
    assert len(items) == 2
    assert items[0]["time"] == 10
    assert items[0]["details"]["type"] == "mcq"
    assert items[0]["details"]["text"] == "Q-one"
    assert items[0]["details"]["correct_answer"] == 0
    assert items[1]["time"] == 20
    assert items[1]["details"]["type"] == "subjective"
    assert items[1]["details"]["text"] == "Q-two"


def test_editing_the_copy_leaves_the_original_untouched(creator):
    original, original_question = _seed_two_question_plio(creator.user)

    copy_item = creator.post("/api/v1/plios/{}/duplicate/".format(original.uuid)).data[
        "items"
    ][0]
    copy_question_id = copy_item["details"]["id"]

    # the clone owns brand-new rows, not the originals
    assert copy_question_id != original_question.id

    # edit the clone's first question through the API
    edited = creator.patch(
        "/api/v1/questions/{}/".format(copy_question_id),
        {
            "item": copy_item["id"],
            "type": "mcq",
            "text": "Edited copy",
            "options": ["A", "B"],
            "correct_answer": 1,
        },
        format="json",
    )
    assert edited.status_code == 200

    # the clone changed...
    assert (
        creator.get("/api/v1/questions/{}/".format(copy_question_id)).data["text"]
        == "Edited copy"
    )

    # ...but the original question is still exactly as seeded
    original_view = creator.get("/api/v1/questions/{}/".format(original_question.id))
    assert original_view.data["text"] == "Q-one"
    assert original_view.data["correct_answer"] == 0
