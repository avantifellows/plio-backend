"""Creator copy-to-workspace journeys.

Copying a plio drops its whole graph into a *different* workspace's schema while
leaving the source workspace untouched. Tenancy is exercised only through the
``Organization`` header on API reads — presence in the target and absence of
side effects in the source are both proved that way, never through
``connection.set_schema()``.
"""

from tests.factories import ItemFactory, PlioFactory, QuestionFactory


def _seed_plio_with_question(owner):
    plio = PlioFactory(created_by=owner, name="Source plio")
    item = ItemFactory(plio=plio, time=15)
    QuestionFactory(item=item, mcq=True, text="Only question")
    return plio


def test_copy_lands_in_target_workspace_and_spares_the_source(creator, org_a):
    # source plio lives in the personal workspace (no Organization header)
    original = _seed_plio_with_question(creator.user)

    response = creator.post(
        "/api/v1/plios/{}/copy/".format(original.uuid),
        {"workspace": org_a.shortcode},
    )
    assert response.status_code == 200
    copy_uuid = response.data["uuid"]
    assert copy_uuid != original.uuid

    # present in the target: the copy reads back under org-a's header with its
    # graph intact, and it is the only plio in that workspace
    in_target = creator.get("/api/v1/plios/{}/".format(copy_uuid), organization=org_a)
    assert in_target.status_code == 200
    assert in_target.data["name"] == "Source plio"
    assert len(in_target.data["items"]) == 1
    assert in_target.data["items"][0]["details"]["text"] == "Only question"
    assert creator.get("/api/v1/plios/", organization=org_a).data["count"] == 1

    # no side effects in the source: the copy's uuid is unknown in the personal
    # workspace, while the original still reads back there unchanged...
    assert creator.get("/api/v1/plios/{}/".format(copy_uuid)).status_code == 404
    source_view = creator.get("/api/v1/plios/{}/".format(original.uuid))
    assert source_view.status_code == 200
    assert source_view.data["name"] == "Source plio"
    assert len(source_view.data["items"]) == 1
    assert creator.get("/api/v1/plios/").data["count"] == 1

    # ...and the original never leaked into the target workspace
    assert (
        creator.get(
            "/api/v1/plios/{}/".format(original.uuid), organization=org_a
        ).status_code
        == 404
    )
