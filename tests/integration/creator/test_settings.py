"""Creator plio-settings persistence journey.

Settings written through the ``setting`` action are stored under
``config["settings"]`` and must survive a round trip: the authoritative check
is a subsequent read of the plio, not the write response. The expected value is
the settings document the creator submits.
"""

from django_redis import get_redis_connection

SETTINGS = {
    "player": {"skipEnabled": True, "watchTime": 15},
    "app": {"aspectRatio": {"value": 0.5625}},
}


def _evict_cache():
    """Drop this worker's Redis DB so the next read is served from Postgres.

    The setting action re-caches the mutated in-memory plio, so a read served
    from Redis would stay green even if the config never reached the database.
    Same per-worker flushdb seam the harness teardown uses.
    """
    get_redis_connection("default").flushdb()


def test_plio_settings_survive_a_round_trip(creator):
    uuid = creator.post("/api/v1/plios/", {"name": "Configured plio"}).data["uuid"]

    written = creator.patch(
        "/api/v1/plios/{}/setting/".format(uuid), SETTINGS, format="json"
    )
    assert written.status_code == 200
    # the write response echoes the stored config...
    assert written.data["settings"] == SETTINGS

    # ...and, authoritatively, the settings are present on a fresh read served
    # from the database, not from the cache the write just repopulated
    _evict_cache()
    fetched = creator.get("/api/v1/plios/{}/".format(uuid))
    assert fetched.status_code == 200
    assert fetched.data["config"]["settings"] == SETTINGS


def test_plio_settings_round_trip_in_org_workspace(creator, org_a):
    uuid = creator.post(
        "/api/v1/plios/", {"name": "Org configured plio"}, organization=org_a
    ).data["uuid"]

    written = creator.patch(
        "/api/v1/plios/{}/setting/".format(uuid),
        SETTINGS,
        organization=org_a,
        format="json",
    )
    assert written.status_code == 200

    _evict_cache()
    fetched = creator.get("/api/v1/plios/{}/".format(uuid), organization=org_a)
    assert fetched.data["config"]["settings"] == SETTINGS
