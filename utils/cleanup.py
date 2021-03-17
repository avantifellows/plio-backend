from plio.secrets import TEST_IDS, TEST_PLIO_VIDEO_IDS


def is_valid_user_id(user_id: str) -> bool:
    """Returns whether given user id is not a test user ID"""
    return user_id not in TEST_IDS


def is_test_plio_id(plio_id: str) -> bool:
    """Returns whether given plio id is a test plio ID or not"""
    return "test" in plio_id


def is_test_plio_video(video_id: str) -> bool:
    """Returns whether the video for the plio is a test video"""
    return video_id in TEST_PLIO_VIDEO_IDS
