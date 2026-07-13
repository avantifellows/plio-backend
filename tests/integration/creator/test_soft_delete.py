"""Creator soft-delete journeys.

Deleting a plio, item or question through the API hides it (list omits it,
retrieval 404s) but the row survives — django-safedelete turns the delete into
a soft delete. "Hidden" is proved through API behaviour; "not destroyed" is
proved through the documented safedelete contract (the ``deleted_objects``
manager), never via raw SQL. Schema access goes through the shared
``in_workspace`` builder, so no spec touches ``connection.set_schema()``.
"""

from plio.models import Item, Plio, Question
from tests.builders import in_workspace


def _new_plio(creator, org):
    response = creator.post("/api/v1/plios/", {"name": "Doomed plio"}, organization=org)
    assert response.status_code == 201
    return response.data


def _new_item(creator, org, plio_id):
    response = creator.post(
        "/api/v1/items/",
        {"plio": plio_id, "type": "question", "time": 10},
        organization=org,
    )
    assert response.status_code == 201
    return response.data


def _new_question(creator, org, item_id):
    response = creator.post(
        "/api/v1/questions/",
        {
            "item": item_id,
            "type": "mcq",
            "text": "Q",
            "options": ["A", "B"],
            "correct_answer": 0,
        },
        organization=org,
        format="json",
    )
    assert response.status_code == 201
    return response.data


def test_deleting_a_plio_hides_it_but_keeps_the_row(creator, org_a):
    plio = _new_plio(creator, org_a)
    uuid = plio["uuid"]

    assert (
        creator.delete("/api/v1/plios/{}/".format(uuid), organization=org_a).status_code
        == 204
    )

    # hidden: 404 on retrieval and absent from the list
    assert (
        creator.get("/api/v1/plios/{}/".format(uuid), organization=org_a).status_code
        == 404
    )
    assert creator.get("/api/v1/plios/", organization=org_a).data["count"] == 0

    # not destroyed: the visible manager omits it, but it survives as a
    # soft-deleted row.
    with in_workspace(org_a):
        assert not Plio.objects.filter(uuid=uuid).exists()
        assert Plio.deleted_objects.filter(uuid=uuid).exists()


def test_deleting_an_item_hides_it_but_keeps_the_row(creator, org_a):
    plio = _new_plio(creator, org_a)
    item = _new_item(creator, org_a, plio["id"])
    item_id = item["id"]

    assert (
        creator.delete(
            "/api/v1/items/{}/".format(item_id), organization=org_a
        ).status_code
        == 204
    )

    assert (
        creator.get("/api/v1/items/{}/".format(item_id), organization=org_a).status_code
        == 404
    )
    listing = creator.get(
        "/api/v1/items/?plio={}".format(plio["uuid"]), organization=org_a
    )
    assert [row["id"] for row in listing.data] == []

    with in_workspace(org_a):
        assert not Item.objects.filter(id=item_id).exists()
        assert Item.deleted_objects.filter(id=item_id).exists()


def test_deleting_a_question_hides_it_but_keeps_the_row(creator, org_a):
    plio = _new_plio(creator, org_a)
    item = _new_item(creator, org_a, plio["id"])
    question = _new_question(creator, org_a, item["id"])
    question_id = question["id"]

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

    with in_workspace(org_a):
        assert not Question.objects.filter(id=question_id).exists()
        assert Question.deleted_objects.filter(id=question_id).exists()
