"""Creator question-authoring CRUD journeys.

Questions are the interactive payload of an item. Specs drive the real
``/api/v1/questions/`` API and observe through responses and subsequent reads;
tenancy is exercised only through the ``Organization`` header.
"""


def _new_item(creator, organization=None):
    plio = creator.post(
        "/api/v1/plios/", {"name": "Host plio"}, organization=organization
    )
    assert plio.status_code == 201
    item = creator.post(
        "/api/v1/items/",
        {"plio": plio.data["id"], "type": "question", "time": 10},
        organization=organization,
    )
    assert item.status_code == 201
    return item.data


def test_question_crud_journey_in_personal_workspace(creator):
    item = _new_item(creator)

    # create
    created = creator.post(
        "/api/v1/questions/",
        {
            "item": item["id"],
            "type": "mcq",
            "text": "What is 2 + 2?",
            "options": ["3", "4", "5"],
            "correct_answer": 1,
        },
        format="json",
    )
    assert created.status_code == 201
    assert created.data["item"] == item["id"]
    assert created.data["text"] == "What is 2 + 2?"
    question_id = created.data["id"]

    # read
    fetched = creator.get("/api/v1/questions/{}/".format(question_id))
    assert fetched.status_code == 200
    assert fetched.data["options"] == ["3", "4", "5"]
    assert fetched.data["correct_answer"] == 1

    # update
    updated = creator.patch(
        "/api/v1/questions/{}/".format(question_id),
        {"text": "What is two plus two?"},
        format="json",
    )
    assert updated.status_code == 200
    assert creator.get("/api/v1/questions/{}/".format(question_id)).data["text"] == (
        "What is two plus two?"
    )

    # list
    listing = creator.get("/api/v1/questions/")
    assert listing.status_code == 200
    assert [row["id"] for row in listing.data] == [question_id]

    # delete
    assert (
        creator.delete("/api/v1/questions/{}/".format(question_id)).status_code == 204
    )
    assert creator.get("/api/v1/questions/{}/".format(question_id)).status_code == 404


def test_question_types_round_trip(creator):
    # each question type stores its own options/correct_answer shape; the
    # expected values below are the payloads the creator submits (a storage
    # round trip), not values recomputed from the app.
    cases = [
        {"type": "mcq", "options": ["A", "B"], "correct_answer": 0},
        {"type": "checkbox", "options": ["A", "B", "C"], "correct_answer": [0, 2]},
        {"type": "subjective", "options": None, "correct_answer": None},
    ]
    for case in cases:
        item = _new_item(creator)
        created = creator.post(
            "/api/v1/questions/",
            {"item": item["id"], "text": "Q", **case},
            format="json",
        )
        assert created.status_code == 201, created.data
        fetched = creator.get("/api/v1/questions/{}/".format(created.data["id"]))
        assert fetched.data["type"] == case["type"]
        assert fetched.data["options"] == case["options"]
        assert fetched.data["correct_answer"] == case["correct_answer"]


def test_question_crud_journey_in_org_workspace(creator, org_a):
    item = _new_item(creator, organization=org_a)

    created = creator.post(
        "/api/v1/questions/",
        {
            "item": item["id"],
            "type": "mcq",
            "text": "Org question",
            "options": ["A", "B"],
            "correct_answer": 0,
        },
        organization=org_a,
        format="json",
    )
    assert created.status_code == 201
    question_id = created.data["id"]

    assert (
        creator.get(
            "/api/v1/questions/{}/".format(question_id), organization=org_a
        ).status_code
        == 200
    )

    assert (
        creator.delete(
            "/api/v1/questions/{}/".format(question_id), organization=org_a
        ).status_code
        == 204
    )
    assert (
        creator.get(
            "/api/v1/questions/{}/".format(question_id), organization=org_a
        ).status_code
        == 404
    )
