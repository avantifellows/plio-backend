"""Creator plio-authoring CRUD journeys.

Each spec drives the real ``/api/v1/plios/`` API as the ``creator`` actor and
observes behaviour through responses and subsequent API reads only. The
``Organization`` header (set by ``organization=...`` on the actor) is the sole
tenancy interface exercised; no spec touches ``connection.set_schema()``.
"""


def test_plio_crud_journey_in_personal_workspace(creator):
    # create
    created = creator.post("/api/v1/plios/", {"name": "Fractions intro"})
    assert created.status_code == 201
    assert created.data["name"] == "Fractions intro"
    # a fresh plio defaults to draft
    assert created.data["status"] == "draft"
    uuid = created.data["uuid"]
    assert uuid

    # read
    fetched = creator.get("/api/v1/plios/{}/".format(uuid))
    assert fetched.status_code == 200
    assert fetched.data["name"] == "Fractions intro"

    # update
    updated = creator.patch(
        "/api/v1/plios/{}/".format(uuid), {"name": "Fractions basics"}
    )
    assert updated.status_code == 200
    # the rename is visible on a subsequent read, not just the write response
    assert creator.get("/api/v1/plios/{}/".format(uuid)).data["name"] == (
        "Fractions basics"
    )

    # list
    listing = creator.get("/api/v1/plios/")
    assert listing.status_code == 200
    assert listing.data["count"] == 1

    # delete
    deleted = creator.delete("/api/v1/plios/{}/".format(uuid))
    assert deleted.status_code == 204
    assert creator.get("/api/v1/plios/{}/".format(uuid)).status_code == 404
    assert creator.get("/api/v1/plios/").data["count"] == 0


def test_plio_crud_journey_in_org_workspace(creator, org_a):
    # create in org-a's workspace via the Organization header
    created = creator.post("/api/v1/plios/", {"name": "Org plio"}, organization=org_a)
    assert created.status_code == 201
    uuid = created.data["uuid"]

    # the plio lives in org-a's schema: it reads back under the org-a header
    fetched = creator.get("/api/v1/plios/{}/".format(uuid), organization=org_a)
    assert fetched.status_code == 200
    assert fetched.data["name"] == "Org plio"

    # ...and is invisible from the personal workspace (no header)
    assert creator.get("/api/v1/plios/{}/".format(uuid)).status_code == 404

    # update
    updated = creator.patch(
        "/api/v1/plios/{}/".format(uuid),
        {"name": "Org plio renamed"},
        organization=org_a,
    )
    assert updated.status_code == 200
    assert (
        creator.get("/api/v1/plios/{}/".format(uuid), organization=org_a).data["name"]
        == "Org plio renamed"
    )

    # list scoped to org-a
    listing = creator.get("/api/v1/plios/", organization=org_a)
    assert listing.status_code == 200
    assert listing.data["count"] == 1

    # delete
    assert (
        creator.delete("/api/v1/plios/{}/".format(uuid), organization=org_a).status_code
        == 204
    )
    assert (
        creator.get("/api/v1/plios/{}/".format(uuid), organization=org_a).status_code
        == 404
    )


def test_plio_list_orders_by_most_recently_updated(creator):
    # the plio list defaults to newest-updated first (Plio.Meta ordering
    # "-updated_at"); expected order below is stated from that contract.
    first = creator.post("/api/v1/plios/", {"name": "First"}).data["uuid"]
    second = creator.post("/api/v1/plios/", {"name": "Second"}).data["uuid"]

    # right after creation "Second" is the most recent, so it leads
    order = [row["uuid"] for row in creator.get("/api/v1/plios/").data["results"]]
    assert order == [second, first]

    # touching "First" moves it to the front
    creator.patch("/api/v1/plios/{}/".format(first), {"name": "First edited"})
    order = [row["uuid"] for row in creator.get("/api/v1/plios/").data["results"]]
    assert order == [first, second]
