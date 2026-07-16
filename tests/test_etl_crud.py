"""Pin the etl app's ``bigquery-jobs`` endpoint family at the authenticated HTTP seam.

The etl app exposes a single superuser-gated write API -- the ``bigquery-jobs``
``ModelViewSet`` over ``BigqueryJobs`` -- and has zero tests, not even a placeholder
``tests.py``. The Django 3.1 -> 5.2 upgrade chain (the reason the test wall exists)
could silently shift its DRF routing, serializer contract, permission enforcement,
or CRUD semantics with CI green, because nothing in any lane exercises this surface.
This module is the single shared home for the whole #378 etl fill, sibling to the
plio/entries/users fill modules; it lives outside ``tests/integration/`` so the
unit lane collects it. Every expected value is a hand-written literal derived from
the spec's own constructed rows/payloads -- never recomputed by re-running the
app's own serializer or queryset.

Caller classes (three; documented here up front so the whole fill reads as one):

* superuser -- an authed actor with ``is_superuser`` flipped on and saved (the #377
  idiom, kept as a slice-local helper; deliberately not promoted to the shared
  harness so existing tests stay untouched). ``ETLPermissions`` gates every action
  on ``request.user.is_superuser``, so the superuser is the only caller that reaches
  the CRUD paths. This slice (#417) pins all six of its CRUD actions.
* authenticated non-superuser -- a plain authed actor; rejected 403 across all
  actions (pinned below, by the parametrized rejection matrix).
* anonymous -- a bare unauthenticated client; the request never succeeds -- it
  crashes (pinned below; see the anonymous-caller quirk).

Shared-schema deviation (flagged): the etl app is SHARED_APPS-only, so ``bigquery_jobs``
is a public-schema table. This module therefore builds rows directly with a
slice-local ORM helper and sends **no** ``Organization`` header on any request --
there is no ``in_workspace(...)`` and no ``connection.set_schema()`` anywhere in the
module. Tenancy is irrelevant to this surface: the table resolves in the public
schema regardless of the header. This mirrors the #377 users fill's flagged
deviation.

Two observed product quirks are documented here and pinned as-is -- a product fix
later must consciously flip the pinning spec; neither is fixed in this fill:

* Hard delete despite a soft-delete docstring (pinned in this slice). ``BigqueryJobs``
  is a ``SafeDeleteModel`` with ``_safedelete_policy = HARD_DELETE``, while the
  viewset docstring claims "Soft delete a row" and the project rule is
  soft-delete-everywhere. Destroy therefore genuinely removes the row: it is absent
  even from the deleted-inclusive ``all_objects`` manager (``deleted_objects`` would
  hold a soft-deleted row). The destroy spec pins this; the delete itself is
  performed only through the endpoint, and ``all_objects`` is read only as an oracle.
* Anonymous-caller crash (pinned below). DRF is configured with
  ``UNAUTHENTICATED_USER: None`` and the etl viewset's ``permission_classes`` contains
  only ``ETLPermissions`` -- no ``IsAuthenticated`` is stacked first -- so an anonymous
  request reaches ``has_permission`` and dereferences ``None.is_superuser``, raising
  ``AttributeError`` (HTTP 500 in production). Documented here so no future
  contributor "fixes" it without updating its pinning spec.

Slice map: #417 (this module's first commit) pins the six superuser CRUD actions;
#418 adds the serializer required/nullable edges and the per-caller rejection
matrix (non-superuser 403, anonymous crash); #419 bumps the unit coverage floor.
The module changes no product code.
"""

import pytest
from rest_framework.test import APIClient

from etl.models import BigqueryJobs

JOBS_URL = "/api/v1/bigquery-jobs/"


def _detail_url(job_id):
    """Detail-route URL for a bigquery job (list route + ``<id>/``)."""
    return "{}{}/".format(JOBS_URL, job_id)


def _superuser(authed_client):
    """Build a superuser caller: an authed actor with ``is_superuser`` flipped on and
    saved. ``ETLPermissions`` gates every action on ``is_superuser``, so this is the
    only caller class that reaches the CRUD paths (the #377 idiom, slice-local)."""
    actor = authed_client()
    actor.user.is_superuser = True
    actor.user.save()
    return actor


def _job(schema, table_to_sync, **fields):
    """Create a ``BigqueryJobs`` row through the default ORM manager (public schema).

    Slice-local -- the model is two required strings plus three nullable sync-state
    fields, and no other module needs it, so no shared factory is added. ``**fields``
    lets a spec set the nullable ``last_synced_row_id`` / datetime fields explicitly.
    """
    return BigqueryJobs.objects.create(
        schema=schema, table_to_sync=table_to_sync, **fields
    )


def test_list_returns_the_exact_set_of_existing_jobs(authed_client):
    # list -> exact id set of the hand-constructed rows. Three distinct rows are
    # built so the set is non-trivial by construction: a handler that dropped or
    # duplicated a row, or leaked some other table, fails the exact-set equality.
    caller = _superuser(authed_client)
    first = _job("analytics", "events")
    second = _job("warehouse", "orders")
    third = _job("reporting", "sessions")

    response = caller.get(JOBS_URL)

    assert response.status_code == 200, response.status_code
    assert {row["id"] for row in response.data} == {first.id, second.id, third.id}


def test_retrieve_returns_the_rows_fields_verbatim(authed_client):
    # retrieve -> field-by-field literals. The row is constructed with a non-null
    # ``last_synced_row_id`` and the two datetime fields left null; the retrieve
    # response is asserted whole against those hand-written literals so a serializer
    # field addition/removal or a renamed key goes red.
    caller = _superuser(authed_client)
    job = _job("analytics", "events", last_synced_row_id=42)

    response = caller.get(_detail_url(job.id))

    assert response.status_code == 200, response.status_code
    assert response.data == {
        "id": job.id,
        "schema": "analytics",
        "table_to_sync": "events",
        "last_updated_at": None,
        "last_synced_at": None,
        "last_synced_row_id": 42,
    }


def test_create_persists_and_echoes_the_payload(authed_client):
    # create -> 201; the response echoes the literal payload (with the omitted
    # nullable sync-state fields defaulting to null), then a follow-up retrieve
    # independently confirms the row is persisted with the same literals.
    caller = _superuser(authed_client)
    payload = {
        "schema": "warehouse",
        "table_to_sync": "orders",
        "last_synced_row_id": 7,
    }

    response = caller.post(JOBS_URL, payload, format="json")

    assert response.status_code == 201, response.status_code
    created_id = response.data["id"]
    assert response.data == {
        "id": created_id,
        "schema": "warehouse",
        "table_to_sync": "orders",
        "last_updated_at": None,
        "last_synced_at": None,
        "last_synced_row_id": 7,
    }
    follow_up = caller.get(_detail_url(created_id))
    assert follow_up.status_code == 200, follow_up.status_code
    assert follow_up.data == {
        "id": created_id,
        "schema": "warehouse",
        "table_to_sync": "orders",
        "last_updated_at": None,
        "last_synced_at": None,
        "last_synced_row_id": 7,
    }


def test_update_via_put_replaces_all_writable_fields(authed_client):
    # update via PUT -> 200 with the replaced literals. PUT is a full replace, so
    # every writable field is overwritten; the response is asserted whole against the
    # new literals. Driven through the actor's underlying client with format="json"
    # (the established integration-suite idiom -- the shared Actor exposes only
    # get/post/patch/delete and is not modified).
    caller = _superuser(authed_client)
    job = _job("old-schema", "old-table", last_synced_row_id=1)

    response = caller.client.put(
        _detail_url(job.id),
        {
            "schema": "new-schema",
            "table_to_sync": "new-table",
            "last_synced_row_id": 99,
        },
        format="json",
    )

    assert response.status_code == 200, response.status_code
    assert response.data == {
        "id": job.id,
        "schema": "new-schema",
        "table_to_sync": "new-table",
        "last_updated_at": None,
        "last_synced_at": None,
        "last_synced_row_id": 99,
    }


def test_partial_update_via_patch_changes_only_the_named_field(authed_client):
    # partial_update via PATCH -> 200; only the named field changes. The spec asserts
    # both the changed field (table_to_sync) and the deliberately-untouched fields
    # (schema, last_synced_row_id still hold their original literals), so a write that
    # silently widened past the patched field goes red.
    caller = _superuser(authed_client)
    job = _job("keep-schema", "keep-table", last_synced_row_id=5)

    response = caller.patch(
        _detail_url(job.id), {"table_to_sync": "patched-table"}, format="json"
    )

    assert response.status_code == 200, response.status_code
    assert response.data == {
        "id": job.id,
        "schema": "keep-schema",
        "table_to_sync": "patched-table",
        "last_updated_at": None,
        "last_synced_at": None,
        "last_synced_row_id": 5,
    }


def test_destroy_hard_deletes_the_row(authed_client):
    # destroy -> 204, subsequent retrieve 404, and the row absent even from the
    # deleted-inclusive ``all_objects`` manager. That last assertion pins the
    # HARD_DELETE quirk as-is: the model hard-deletes despite the viewset docstring
    # saying "Soft delete" and the project's soft-delete-everywhere rule, so a
    # soft-deleted row (which ``all_objects`` would still surface) is genuinely gone.
    # The delete goes only through the endpoint; ``all_objects`` is read as an oracle.
    caller = _superuser(authed_client)
    job = _job("doomed-schema", "doomed-table")
    job_id = job.id

    response = caller.delete(_detail_url(job_id))

    assert response.status_code == 204, response.status_code
    assert caller.get(_detail_url(job_id)).status_code == 404
    assert not BigqueryJobs.all_objects.filter(id=job_id).exists()


def test_create_with_only_required_fields_defaults_sync_state_to_null(authed_client):
    # minimal create -> only the two required strings (schema, table_to_sync). The
    # three sync-state fields (last_updated_at, last_synced_at, last_synced_row_id) are
    # omitted from the payload and must come back literally null, pinning their
    # optional/nullable contract through the serializer. The server-assigned id is
    # read back (it cannot be a literal), and the rest is asserted whole.
    caller = _superuser(authed_client)
    payload = {"schema": "minimal-schema", "table_to_sync": "minimal-table"}

    response = caller.post(JOBS_URL, payload, format="json")

    assert response.status_code == 201, response.status_code
    created_id = response.data["id"]
    assert response.data == {
        "id": created_id,
        "schema": "minimal-schema",
        "table_to_sync": "minimal-table",
        "last_updated_at": None,
        "last_synced_at": None,
        "last_synced_row_id": None,
    }


def test_create_missing_a_required_field_is_rejected(authed_client):
    # create missing a required field -> 400 whose body names the missing field.
    # schema and table_to_sync are non-blank CharFields with no default, so a payload
    # that omits table_to_sync is invalid; DRF returns 400 with that field as a key in
    # the error body (pinning the required half of the field contract).
    caller = _superuser(authed_client)
    payload = {"schema": "schema-only"}

    response = caller.post(JOBS_URL, payload, format="json")

    assert response.status_code == 400, response.status_code
    assert "table_to_sync" in response.data


# The six viewset actions as (label, HTTP method, is-detail-route). Parametrizing over
# them is the one accepted deviation from one-named-spec-per-edge: the edge (a rejected
# caller) is identical across actions and only the action/method varies. DRF checks
# view-level permissions in initial() before get_object(), so the detail-route cases
# reject before any object lookup and seed no row -- an arbitrary id is enough.
_ACTIONS = [
    ("list", "get", False),
    ("retrieve", "get", True),
    ("create", "post", False),
    ("update", "put", True),
    ("partial_update", "patch", True),
    ("destroy", "delete", True),
]

_ARBITRARY_ID = 1  # no row with this id is seeded; the rejection precedes any lookup


def _action_url(is_detail):
    """List route, or a detail route at an unseeded arbitrary id."""
    return _detail_url(_ARBITRARY_ID) if is_detail else JOBS_URL


def _issue(client, method, url):
    """Issue one request through a bare ``APIClient`` (or an actor's underlying client),
    dispatching on the HTTP method. Used for both rejection callers so a single
    parametrized body covers all six actions -- including PUT, which the shared ``Actor``
    does not expose. Write methods send an empty json body; the permission check denies
    before the body is ever parsed, so its content is irrelevant to the rejection."""
    issue = getattr(client, method)
    if method in ("post", "put", "patch"):
        return issue(url, {}, format="json")
    return issue(url)


@pytest.mark.parametrize("action, method, is_detail", _ACTIONS)
def test_authenticated_non_superuser_is_forbidden_on_every_action(
    authed_client, action, method, is_detail
):
    # ETLPermissions gates every action on request.user.is_superuser; a plain authed
    # user is not a superuser, so DRF denies at the view-level permission check with
    # 403 on all six actions. Detail routes seed no row -- the rejection precedes
    # get_object(). Requests go through the actor's underlying client so PUT is reachable
    # uniformly (organization=None -> no Organization header is added).
    caller = authed_client()

    response = _issue(caller.client, method, _action_url(is_detail))

    assert response.status_code == 403, (action, response.status_code)


@pytest.mark.parametrize("action, method, is_detail", _ACTIONS)
def test_anonymous_caller_crashes_on_every_action(db, action, method, is_detail):
    # Pinned quirk (not fixed here -- a guard/IsAuthenticated fix is future work for its
    # own issue). DRF runs with UNAUTHENTICATED_USER=None and the etl viewset stacks no
    # IsAuthenticated before ETLPermissions, so has_permission dereferences
    # None.is_superuser and raises AttributeError. In production this surfaces as HTTP
    # 500; at the test-client seam the uncaught exception propagates, so each of the six
    # actions is pinned with pytest.raises(AttributeError). The crash occurs at the
    # view-level permission check, before any object lookup, so detail routes seed no
    # row. A future fix must consciously flip this spec. The caller is a bare
    # unauthenticated APIClient (no credentials) -- not an actor.
    anonymous = APIClient()

    with pytest.raises(AttributeError):
        _issue(anonymous, method, _action_url(is_detail))
