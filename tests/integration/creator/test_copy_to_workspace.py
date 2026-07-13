"""Creator copy-to-workspace journeys.

Copying a plio drops its whole graph into a *different* workspace's schema while
leaving the source workspace untouched. Tenancy is exercised only through the
``Organization`` header on API reads — presence in the target and absence of
side effects in the source are both proved that way, never through
``connection.set_schema()``.
"""

from tests.factories import ItemFactory, PlioFactory, QuestionFactory


def _seed_plio_with_questions(owner):
    # two distinguishable item/question pairs: a copy that silently truncated
    # the graph to its first item would pass a single-item fixture
    plio = PlioFactory(created_by=owner, name="Source plio")
    first = ItemFactory(plio=plio, time=15)
    QuestionFactory(item=first, mcq=True, text="First question")
    second = ItemFactory(plio=plio, time=30)
    QuestionFactory(item=second, mcq=True, text="Second question")
    return plio


def test_copy_lands_in_target_workspace_and_spares_the_source(creator, org_a):
    # source plio lives in the personal workspace (no Organization header)
    original = _seed_plio_with_questions(creator.user)

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
    # the *whole* graph arrived: both items, in item-time order, questions intact
    assert len(in_target.data["items"]) == 2
    assert in_target.data["items"][0]["details"]["text"] == "First question"
    assert in_target.data["items"][1]["details"]["text"] == "Second question"
    # the video is cloned into the target too, content intact -- a copy that
    # saved the target plio with video=None passes every other check here
    # (integer ids are schema-local and can collide, so content is the proof)
    assert in_target.data["video"]["url"] == original.video.url
    assert in_target.data["video"]["duration"] == original.video.duration
    assert creator.get("/api/v1/plios/", organization=org_a).data["count"] == 1

    # no side effects in the source: the copy's uuid is unknown in the personal
    # workspace, while the original still reads back there unchanged...
    assert creator.get("/api/v1/plios/{}/".format(copy_uuid)).status_code == 404
    source_view = creator.get("/api/v1/plios/{}/".format(original.uuid))
    assert source_view.status_code == 200
    # identity, not just shape: source and copy can share an integer PK in
    # their separate schemas, so a cache key that lost its tenant scoping
    # would serve the copy here -- and name/item-count would still match
    assert source_view.data["uuid"] == original.uuid
    assert source_view.data["name"] == "Source plio"
    assert len(source_view.data["items"]) == 2
    assert creator.get("/api/v1/plios/").data["count"] == 1

    # ...and the original never leaked into the target workspace
    assert (
        creator.get(
            "/api/v1/plios/{}/".format(original.uuid), organization=org_a
        ).status_code
        == 404
    )
