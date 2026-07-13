"""Creator item-authoring CRUD journeys.

Items are the timed markers on a plio. Every spec drives the real
``/api/v1/items/`` API and observes state through responses and subsequent
reads; tenancy is exercised only through the ``Organization`` header.
"""


def _new_plio(creator, organization=None):
    response = creator.post(
        "/api/v1/plios/", {"name": "Host plio"}, organization=organization
    )
    assert response.status_code == 201
    return response.data


def test_item_crud_journey_in_personal_workspace(creator):
    plio = _new_plio(creator)

    # create
    created = creator.post(
        "/api/v1/items/",
        {"plio": plio["id"], "type": "question", "time": 10},
    )
    assert created.status_code == 201
    assert created.data["plio"] == plio["id"]
    assert created.data["type"] == "question"
    assert created.data["time"] == 10
    item_id = created.data["id"]

    # read
    fetched = creator.get("/api/v1/items/{}/".format(item_id))
    assert fetched.status_code == 200
    assert fetched.data["time"] == 10

    # update
    updated = creator.patch(
        "/api/v1/items/{}/".format(item_id), {"time": 25, "plio": plio["id"]}
    )
    assert updated.status_code == 200
    assert creator.get("/api/v1/items/{}/".format(item_id)).data["time"] == 25

    # list for this plio
    listing = creator.get("/api/v1/items/?plio={}".format(plio["uuid"]))
    assert listing.status_code == 200
    assert [row["id"] for row in listing.data] == [item_id]

    # delete
    assert creator.delete("/api/v1/items/{}/".format(item_id)).status_code == 204
    assert creator.get("/api/v1/items/{}/".format(item_id)).status_code == 404
    assert creator.get("/api/v1/items/?plio={}".format(plio["uuid"])).data == []


def test_item_list_orders_by_time(creator):
    plio = _new_plio(creator)
    # items are returned ordered by their marker time (Item.Meta ordering
    # "time" and the viewset's explicit order_by); expected order stated from
    # that contract, not from creation order.
    for time in (30, 10, 20):
        creator.post(
            "/api/v1/items/",
            {"plio": plio["id"], "type": "question", "time": time},
        )

    times = [
        row["time"]
        for row in creator.get("/api/v1/items/?plio={}".format(plio["uuid"])).data
    ]
    assert times == [10, 20, 30]


def test_item_crud_journey_in_org_workspace(creator, org_a):
    plio = _new_plio(creator, organization=org_a)

    created = creator.post(
        "/api/v1/items/",
        {"plio": plio["id"], "type": "question", "time": 15},
        organization=org_a,
    )
    assert created.status_code == 201
    item_id = created.data["id"]

    # reads back under the org-a header
    assert (
        creator.get("/api/v1/items/{}/".format(item_id), organization=org_a).status_code
        == 200
    )

    # deleting hides it from the org-a item list
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
