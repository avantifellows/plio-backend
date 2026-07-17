"""Creator video-URL validation journeys.

The server-side check the video API enforces on a URL is the ``url`` field's
length limit (255 chars on ``Video.url``); an over-length URL is rejected with
a 400 keyed on ``url``. A well-formed URL within the limit is stored verbatim.
The expected outcomes are stated from that field contract.
"""

# 32-char youtube prefix + filler pushes this well past the 255-char limit
OVERLONG_URL = "https://www.youtube.com/watch?v=" + "a" * 230
VALID_URL = "https://www.youtube.com/watch?v=vnISjBbrMUM"


def test_creating_video_with_overlong_url_is_rejected(creator):
    response = creator.post(
        "/api/v1/videos/",
        {"url": OVERLONG_URL, "title": "Too long", "duration": 60},
    )
    assert response.status_code == 400
    # the error is keyed on the offending field and carries a message
    assert "url" in response.data
    assert len(response.data["url"]) >= 1


def test_updating_video_url_to_overlong_value_is_rejected(creator):
    created = creator.post(
        "/api/v1/videos/",
        {"url": VALID_URL, "title": "Fine", "duration": 60},
    )
    assert created.status_code == 201
    video_id = created.data["id"]

    response = creator.patch(
        "/api/v1/videos/{}/".format(video_id), {"url": OVERLONG_URL}
    )
    assert response.status_code == 400
    assert "url" in response.data

    # the stored URL is unchanged after the rejected update
    assert creator.get("/api/v1/videos/{}/".format(video_id)).data["url"] == VALID_URL


def test_creating_video_with_valid_url_succeeds(creator):
    created = creator.post(
        "/api/v1/videos/",
        {"url": VALID_URL, "title": "Fine", "duration": 60},
    )
    assert created.status_code == 201
    assert created.data["url"] == VALID_URL
