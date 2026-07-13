"""Websocket live-users canary.

Drives the real ``UserConsumer`` route through channels' test communicator at
the ASGI boundary -- no mocked channel layer, the per-worker Redis logical DB
from the harness backs it. Adding a learner to an organization fires the
production ``update_organization_user`` signal, which pushes the serialized user
over the ``user_<id>`` group; the spec asserts that update arrives at the
websocket. This doubles as the canary for the channels version bump in the
Django upgrade chain.

Why this spec is ``slow_lane``: the consumer runs in its own thread and only
sees *committed* rows, so it uses the ``slow_lane_db`` fixture (real commits,
truncation cleanup) rather than the suite's transaction-rollback isolation. That
fixture also rebuilds the per-worker tenant universe its flush would otherwise
wipe. See this package's ``conftest.py`` for the truncation approach.
"""
import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from plio.asgi import application
from tests.factories import UserFactory
from users.models import OrganizationUser, Role


@pytest.mark.slow_lane
def test_org_membership_change_pushes_live_user_update(slow_lane_db, org_a):
    learner = UserFactory()
    role = Role.objects.get(name="org-view")

    def add_learner_to_org():
        # the production trigger for a live-user update; its signal calls
        # async_to_sync(group_send), which must run off the event-loop thread
        OrganizationUser.objects.create(user=learner, organization=org_a, role=role)

    async def scenario():
        communicator = WebsocketCommunicator(
            application, "/api/v1/users/{}".format(learner.id)
        )
        connected, _ = await communicator.connect()
        assert connected

        # database_sync_to_async (not plain sync_to_async) so the executor
        # thread's ORM connection is closed afterwards -- a leaked connection
        # makes postgres reject pytest-django's DROP DATABASE at teardown
        await database_sync_to_async(add_learner_to_org)()

        message = await communicator.receive_json_from(timeout=5)
        await communicator.disconnect()
        return message

    message = async_to_sync(scenario)()

    # the update carries the learner that was just added, observed at the wire
    assert message["user"]["id"] == learner.id
    assert message["user"]["email"] == learner.email
