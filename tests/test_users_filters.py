"""Pin ``UserViewSet``'s happy-path query-param filter branches at the HTTP seam.

``GET /api/v1/users/`` supports three optional filters -- ``ids`` (a CSV of user
ids), ``organization`` (a workspace id), and ``email`` (an exact match) -- applied
in ``UserViewSet.get_queryset``. No test in any lane passes a single filter param,
so an ORM or request-parsing shift in the Django 3.1 -> 5.2 upgrade chain could
silently widen or empty those lists with CI green. Each spec here pins one
happy-path branch: it builds a tiny hand-constructed set of users (and, for the
``organization`` filter, membership rows) with the shared factories, lists over
the real authenticated HTTP seam as a superuser caller, and asserts the exact set
of ``id``s that branch must return.

Caller class -- superuser: the list permission gate restricts ``list`` to
superusers (``users/permissions.py``), so every spec drives the endpoint as a
superuser actor, built by flipping ``is_superuser`` on an ``authed_client()`` actor
and saving -- the same idiom the integration membership journey uses. The gate
itself stays pinned by the legacy ``users/tests.py`` suite and is not re-tested
here.

Shared-schema deviation (flagged): unlike the plio and entries fills, the users
app lives in SHARED_APPS, so users, roles, and membership rows live in the public
schema. These specs therefore build data directly with the shared factories --
there is no ``in_workspace(...)`` and no ``connection.set_schema()`` anywhere in
this module. The two seeded workspaces (``org_a``, ``org_b``) are used only as the
``organization`` filter's target/decoy; membership rows are created directly on
``OrganizationUser`` with the seeded ``DEFAULT_ROLES`` fetched by name, the same
way the harness's ``creator`` fixture does. No new shared factories.

Oracle discipline: every expected value is a set of ``id``s hand-listed from the
spec's own constructed rows -- never recomputed by re-running the app's filtering.
List responses are compared as unordered sets of ``id``s (the model declares no
ordering). Every filter spec seeds at least one non-matching decoy user, so a
filter that silently widens the result cannot pass by accident, and the exact-set
equality goes red if the branch either widens (decoy leaks in) or narrows (a
matching row drops out).

This is the single shared home for the whole #377 users fill, mirroring the plio
and entries fills' one-module pattern. It lives outside ``tests/integration/`` so
the unit lane collects it. This slice (#412) pins only the happy-path filter
branches; invalid/empty inputs, the de-duplication edge, soft-delete visibility,
and the ``RoleViewSet`` visibility matrix are later slices. The module changes no
product code.
"""

from urllib.parse import urlencode

from tests.factories import UserFactory
from users.models import OrganizationUser, Role

USERS_URL = "/api/v1/users/"


def _superuser(authed_client):
    """Build a superuser caller: an authed actor with ``is_superuser`` flipped on
    and saved -- the list permission gate allows only superusers to list users."""
    actor = authed_client()
    actor.user.is_superuser = True
    actor.user.save()
    return actor


def _member(user, organization, role_name="org-view"):
    """Create a membership row directly on ``OrganizationUser`` with a seeded role
    fetched by name -- no ad-hoc role machinery, the harness's own idiom."""
    role = Role.objects.get(name=role_name)
    return OrganizationUser.objects.create(
        user=user, organization=organization, role=role
    )


def _list(caller, **params):
    """List users over the HTTP seam with the given query-param filters.

    The filters live in the query string (the viewset reads them from
    ``request.query_params``), so they are encoded onto the URL rather than passed
    as ``Actor.get`` kwargs (which become request headers). ``organization`` here
    is the filter's workspace *id* query param -- not the ``Organization`` request
    header -- and no header is sent: users live in the public schema, so the list
    resolves there regardless.
    """
    query = urlencode(params)
    path = "{}?{}".format(USERS_URL, query) if query else USERS_URL
    return caller.get(path)


def _listed_ids(response):
    """The set of user ``id``s in a list response -- responses are compared as
    unordered sets because neither the model nor the viewset declares an ordering."""
    assert response.status_code == 200, response.status_code
    return {row["id"] for row in response.data}


def test_no_filter_params_returns_full_user_set(authed_client):
    # No filter params: every user is returned, including the superuser caller
    # itself. Two extra users are constructed; the expected set is all three ids
    # hand-listed from the constructed rows.
    caller = _superuser(authed_client)
    alice = UserFactory()
    bob = UserFactory()

    response = caller.get(USERS_URL)

    assert _listed_ids(response) == {caller.user.id, alice.id, bob.id}


def test_ids_single_value_returns_only_that_user(authed_client):
    # ``ids=<one id>`` narrows to exactly that user. A decoy user exists but is
    # not requested; a filter that silently widened would leak it (and the
    # superuser caller) into the set.
    caller = _superuser(authed_client)
    target = UserFactory()
    UserFactory()  # decoy: exists, not requested

    response = _list(caller, ids=str(target.id))

    assert _listed_ids(response) == {target.id}


def test_ids_multi_value_csv_returns_exactly_those_users(authed_client):
    # ``ids=a,b`` (CSV) returns exactly the two requested users -- and no more.
    # A third decoy user is present but omitted from the CSV.
    caller = _superuser(authed_client)
    first = UserFactory()
    second = UserFactory()
    UserFactory()  # decoy: not in the requested CSV

    response = _list(caller, ids="{},{}".format(first.id, second.id))

    assert _listed_ids(response) == {first.id, second.id}


def test_ids_with_no_matching_rows_returns_empty(authed_client):
    # ``ids=<a digit-only id no row has>`` hits the no-match branch: the id list
    # is non-empty (so the filter is applied) but matches nothing, so the result
    # is empty -- distinct from the all-invalid-token quirk (a later slice) that
    # skips the filter and returns the full list. A decoy user is present to prove
    # the empty result is the filter's doing, not an empty table.
    caller = _superuser(authed_client)
    decoy = UserFactory()
    absent_id = decoy.id + 1000  # no user holds this id within the test

    response = _list(caller, ids=str(absent_id))

    assert _listed_ids(response) == set()


def test_organization_filter_returns_only_that_workspaces_members(
    authed_client, org_a, org_b
):
    # ``organization=<org_a id>`` returns exactly the members of that workspace.
    # A decoy user who is a member of only the *other* seeded workspace (org_b)
    # must be excluded, as must the non-member superuser caller.
    caller = _superuser(authed_client)
    member_one = UserFactory()
    member_two = UserFactory()
    _member(member_one, org_a)
    _member(member_two, org_a)
    decoy = UserFactory()
    _member(decoy, org_b)  # member of the other workspace only

    response = _list(caller, organization=str(org_a.id))

    assert _listed_ids(response) == {member_one.id, member_two.id}


def test_organization_filter_with_no_members_returns_empty(authed_client, org_a, org_b):
    # ``organization=<org_a id>`` where org_a has no members returns empty. A decoy
    # user is a member of org_b, so membership rows exist -- the empty result is
    # the workspace predicate at work, not an empty membership table.
    caller = _superuser(authed_client)
    decoy = UserFactory()
    _member(decoy, org_b)

    response = _list(caller, organization=str(org_a.id))

    assert _listed_ids(response) == set()


def test_email_exact_match_returns_that_user(authed_client):
    # ``email=<exact address>`` returns the single user with that address. A decoy
    # user with a different address is present and must be excluded.
    caller = _superuser(authed_client)
    target = UserFactory(email="filter-target@example.com")
    UserFactory(email="filter-decoy@example.com")  # decoy: different email

    response = _list(caller, email="filter-target@example.com")

    assert _listed_ids(response) == {target.id}


def test_email_with_no_match_returns_empty(authed_client):
    # ``email=<address no user holds>`` returns empty. A decoy user with a known,
    # different email is present so the empty result proves the exact-match
    # predicate, not an empty table.
    caller = _superuser(authed_client)
    UserFactory(email="present@example.com")  # decoy: a different, real address

    response = _list(caller, email="absent@example.com")

    assert _listed_ids(response) == set()


def test_combined_filters_are_conjunction_only_all_three_match(
    authed_client, org_a, org_b
):
    # ``ids`` + ``organization`` + ``email`` are ANDed: only the row satisfying all
    # three survives. Three decoys each satisfy a strict subset and must be
    # excluded -- so the set goes red both if a matching row drops out and if the
    # filters degrade to an OR (which would leak a subset decoy). Email is unique
    # per user, so each decoy necessarily carries its own address.
    caller = _superuser(authed_client)

    winner = UserFactory(email="combined-winner@example.com")
    _member(winner, org_a)

    # satisfies {ids, organization} but not email -> excluded (and would leak if
    # the email predicate were dropped)
    decoy_ids_org = UserFactory(email="combined-ids-org@example.com")
    _member(decoy_ids_org, org_a)

    # satisfies {ids} only: requested in the CSV but a member of the other
    # workspace and a different email
    decoy_ids_only = UserFactory(email="combined-ids-only@example.com")
    _member(decoy_ids_only, org_b)

    # satisfies {organization} only: a member of org_a but absent from the CSV and
    # a different email
    decoy_org_only = UserFactory(email="combined-org-only@example.com")
    _member(decoy_org_only, org_a)

    response = _list(
        caller,
        ids="{},{},{}".format(winner.id, decoy_ids_org.id, decoy_ids_only.id),
        organization=str(org_a.id),
        email="combined-winner@example.com",
    )

    assert _listed_ids(response) == {winner.id}
