"""Creator image-upload journey.

Runs against the harness's local file-storage override (``FileSystemStorage``
into a temp ``MEDIA_ROOT``) — no AWS credentials are needed anywhere. The
journey asserts the Image record is created and its returned reference is usable
by reading it back through the API.
"""

from plio.models import Image

TEST_IMAGE = "plio/static/plio/test_image.jpeg"


def test_creator_uploads_an_image(creator):
    with open(TEST_IMAGE, "rb") as image_file:
        created = creator.post(
            "/api/v1/images/",
            {"url": image_file, "alt_text": "A diagram"},
        )

    assert created.status_code == 201
    image_id = created.data["id"]
    reference = created.data["url"]
    assert created.data["alt_text"] == "A diagram"
    # the stored reference lands under the "images" upload path with the
    # original extension preserved
    assert "images/" in reference
    assert reference.endswith(".jpeg")

    # the record exists and its reference is retrievable through the API
    fetched = creator.get("/api/v1/images/{}/".format(image_id))
    assert fetched.status_code == 200
    assert fetched.data["url"] == reference
    assert fetched.data["alt_text"] == "A diagram"

    # the uploaded bytes actually reached storage: a backend that returned a
    # generated name without writing content would pass every check above
    stored = Image.objects.get(id=image_id)
    assert stored.url.storage.exists(stored.url.name)
    with open(TEST_IMAGE, "rb") as image_file:
        original_bytes = image_file.read()
    with stored.url.open("rb") as stored_file:
        assert stored_file.read() == original_bytes
