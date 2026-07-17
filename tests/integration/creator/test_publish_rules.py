"""Creator publish-rule journeys.

These specs pin the *server-side* publish contract as it exists today: the
backend gates publishing purely on the ``status`` field's allowed choices. It
does not require questions before publishing and it does not lock a plio once
published — any such workflow restriction lives in the frontend. The expected
outcomes below are stated from that contract, and the specs would catch a
regression if the Django upgrade changed it.
"""


def _new_plio(creator):
    response = creator.post("/api/v1/plios/", {"name": "Draft plio"})
    assert response.status_code == 201
    assert response.data["status"] == "draft"
    return response.data["uuid"]


def test_publishing_a_plio_with_no_questions_is_allowed(creator):
    uuid = _new_plio(creator)

    # publish with zero items/questions attached
    published = creator.patch("/api/v1/plios/{}/".format(uuid), {"status": "published"})
    assert published.status_code == 200

    # the published state is visible on a subsequent read
    assert creator.get("/api/v1/plios/{}/".format(uuid)).data["status"] == "published"


def test_publishing_rejects_an_unknown_status(creator):
    uuid = _new_plio(creator)

    # only the "draft"/"published" choices are accepted; anything else is a 400
    # keyed on the offending field, and the plio stays in draft.
    rejected = creator.patch("/api/v1/plios/{}/".format(uuid), {"status": "archived"})
    assert rejected.status_code == 400
    assert "status" in rejected.data
    assert creator.get("/api/v1/plios/{}/".format(uuid)).data["status"] == "draft"


def test_editing_a_published_plio_is_allowed(creator):
    uuid = _new_plio(creator)
    creator.patch("/api/v1/plios/{}/".format(uuid), {"status": "published"})

    # content edits are still accepted after publishing (no server-side lock)
    edited = creator.patch(
        "/api/v1/plios/{}/".format(uuid), {"name": "Published then edited"}
    )
    assert edited.status_code == 200

    fetched = creator.get("/api/v1/plios/{}/".format(uuid))
    assert fetched.data["name"] == "Published then edited"
    # ...and it remains published through the edit
    assert fetched.data["status"] == "published"


def test_published_plio_uuid_is_immutable(creator):
    uuid = _new_plio(creator)
    creator.patch("/api/v1/plios/{}/".format(uuid), {"status": "published"})

    # the one edit the API refuses even after publish: reassigning identity.
    # uuid is a read-only field, so the attempt is ignored, not errored.
    response = creator.patch(
        "/api/v1/plios/{}/".format(uuid),
        {"uuid": "reassigned", "name": "Rename attempt"},
    )
    assert response.status_code == 200
    assert response.data["uuid"] == uuid
    # the original uuid still resolves; the attempted one never existed
    assert creator.get("/api/v1/plios/{}/".format(uuid)).status_code == 200
    assert creator.get("/api/v1/plios/reassigned/").status_code == 404
