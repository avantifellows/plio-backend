def test_creator_plio_is_isolated_between_workspaces(creator, org_a, org_b):
    create_response = creator.post(
        "/api/v1/plios/",
        {"name": "Org A smoke plio"},
        organization=org_a,
    )

    assert create_response.status_code == 201
    assert creator.get("/api/v1/plios/", organization=org_a).data["count"] == 1
    assert creator.get("/api/v1/plios/", organization=org_b).data["count"] == 0


def test_org_b_header_routes_to_its_own_schema(creator, org_a, org_b):
    """Positive org-b routing control: create *through* the org-b header and
    read the same identity back under it. Without this, a middleware that
    resolved every org-b header to the (empty) public schema would pass the
    lane -- all other org-b assertions are negative zero-counts."""
    created = creator.post(
        "/api/v1/plios/", {"name": "Org B smoke plio"}, organization=org_b
    )
    assert created.status_code == 201
    uuid = created.data["uuid"]

    in_org_b = creator.get("/api/v1/plios/{}/".format(uuid), organization=org_b)
    assert in_org_b.status_code == 200
    assert in_org_b.data["uuid"] == uuid
    assert creator.get("/api/v1/plios/", organization=org_b).data["count"] == 1

    # ...and that identity exists nowhere else
    assert (
        creator.get("/api/v1/plios/{}/".format(uuid), organization=org_a).status_code
        == 404
    )
    assert creator.get("/api/v1/plios/{}/".format(uuid)).status_code == 404
