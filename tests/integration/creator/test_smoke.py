import pytest


pytestmark = pytest.mark.integration


def test_creator_plio_is_isolated_between_workspaces(creator, org_a, org_b):
    create_response = creator.post(
        "/api/v1/plios/",
        {"name": "Org A smoke plio"},
        organization=org_a,
    )

    assert create_response.status_code == 201
    assert creator.get("/api/v1/plios/", organization=org_a).data["count"] == 1
    assert creator.get("/api/v1/plios/", organization=org_b).data["count"] == 0
