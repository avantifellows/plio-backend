from django.db import transaction

from plio.models import Plio
from tests.builders import in_workspace
from tests.factories import PlioFactory


def test_writes_across_workspaces_roll_back_on_one_connection(creator, org_a, org_b):
    with transaction.atomic():
        with in_workspace(org_a):
            PlioFactory(created_by=creator.user)
            # positive check before the rollback: the write landed in org_a's
            # schema -- without it, this test would stay green even if
            # in_workspace() stopped switching schemas
            assert Plio.objects.count() == 1
        with in_workspace(org_b):
            PlioFactory(created_by=creator.user)
            # exactly one here too (not two) proves the schemas are separate
            assert Plio.objects.count() == 1
        transaction.set_rollback(True)

    assert creator.get("/api/v1/plios/", organization=org_a).data["count"] == 0
    assert creator.get("/api/v1/plios/", organization=org_b).data["count"] == 0
