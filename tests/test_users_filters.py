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
the unit lane collects it. #412 pinned the happy-path filter branches; #413 adds
the invalid/empty-input quirks, the de-duplication edge, and soft-delete
visibility; the ``RoleViewSet`` visibility matrix is a later slice. The module
changes no product code.

Filter quirks pinned as-is by #413 (documented here, not fixed):

* Asymmetry -- the two numeric filters react to a malformed value of the same
  class in opposite ways. An all-invalid ``ids`` value drops every token at the
  ``.isdigit()`` gate, leaving an empty id list, so the ``if id_list:`` guard
  *skips* the filter and the **full** list returns; a non-integer ``organization``
  value instead fails ``int(...)`` and returns an **empty** list. Callers see
  opposite failure modes for the same mistake. Pinned, not reconciled.
* Empty string -- an empty-string value for ``ids`` / ``organization`` / ``email``
  is falsy, so each guard treats it as filter-*absent* (full list), never as
  "match nothing".
* Raw exact match -- the ``email`` filter compares verbatim, with no
  normalization.

The ``ids`` handler's ``except ValueError`` conversion fallback is near-dead:
tokens are ``.isdigit()``-gated before ``int(...)``, so it is reachable only by
exotic Unicode digit-like characters (e.g. a superscript digit, which passes
``.isdigit()`` yet fails ``int(...)``). Per the decided handling it is pinned here
with such a token rather than documented away.
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


def _listed_id_sequence(response):
    """The user ``id``s in a list response as a *list*, duplicates preserved.

    Used only by the de-duplication spec: an unordered-set comparison would silently
    collapse a row that appeared twice, so that spec asserts against this ordering-
    agnostic-but-duplicate-preserving list (a single-element list == a single
    appearance) instead of ``_listed_ids``.
    """
    assert response.status_code == 200, response.status_code
    return [row["id"] for row in response.data]


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
    target_email = "filter-target@example.com"
    target = UserFactory(email=target_email)
    UserFactory(email="filter-decoy@example.com")  # decoy: different email

    response = _list(caller, email=target_email)

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

    winner_email = "combined-winner@example.com"
    winner = UserFactory(email=winner_email)
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
        email=winner_email,
    )

    assert _listed_ids(response) == {winner.id}


def test_ids_mixed_valid_and_invalid_tokens_applies_only_valid(authed_client):
    # ``ids=<valid id>,<non-digit token>`` drops the non-digit token at the
    # ``.isdigit()`` gate and applies the surviving valid id: the result is exactly
    # the one requested valid user. A decoy user is present but neither requested
    # nor returned, so a handler that ignored the id list (and returned the full
    # set) would fail this exact-set assertion.
    caller = _superuser(authed_client)
    target = UserFactory()
    UserFactory()  # decoy: not named by any token

    response = _list(caller, ids="{},notanid".format(target.id))

    assert _listed_ids(response) == {target.id}


def test_ids_unicode_digit_like_token_triggers_conversion_fallback_empty(authed_client):
    # Near-dead branch pinned: the ``ids`` handler digit-gates every token with
    # ``str.isdigit()`` before calling ``int(...)``, so ordinary input never reaches
    # the ``except ValueError`` fallback. A superscript digit (``"²"``, i.e.
    # ``"2"`` superscript) is the exotic exception -- it satisfies ``.isdigit()`` yet
    # raises ``ValueError`` inside ``int(...)`` -- so it drives the fallback, which
    # returns an empty list. A decoy user is present: were the token instead merely
    # skipped by the digit gate, the id list would be empty, the filter would be
    # skipped, and the decoy (plus the caller) would come back -- so the empty
    # result proves the conversion fallback fired, not the digit gate.
    caller = _superuser(authed_client)
    UserFactory()  # decoy: would appear if the fallback did not fire

    response = _list(caller, ids="²")

    assert _listed_ids(response) == set()


def test_ids_all_invalid_tokens_skips_filter_and_returns_full_list(authed_client):
    # Quirk pinned as-is: when *every* ``ids`` token fails the ``.isdigit()`` gate,
    # the parsed id list is empty, the ``if id_list:`` guard skips the filter
    # entirely, and the *full* user list returns. This is the opposite failure mode
    # from a non-integer ``organization`` value, which returns an *empty* list --
    # the asymmetry is documented in the module docstring and pinned, not fixed.
    # The expected set hand-lists every constructed user plus the caller, so an
    # accidental partial filter (returning fewer) cannot pass by luck.
    caller = _superuser(authed_client)
    alice = UserFactory()
    bob = UserFactory()

    response = _list(caller, ids="not,an,id")

    assert _listed_ids(response) == {caller.user.id, alice.id, bob.id}


def test_organization_non_integer_value_returns_empty(authed_client, org_a):
    # Quirk pinned as-is: a non-integer ``organization`` value fails ``int(...)`` and
    # the handler returns an *empty* list -- the opposite failure mode from an
    # all-invalid ``ids`` value, which skips its filter and returns the full list
    # (the asymmetry is documented in the module docstring, pinned not fixed). A
    # decoy member of org_a exists, so the empty result is the conversion fallback
    # firing, not an empty membership table.
    caller = _superuser(authed_client)
    decoy = UserFactory()
    _member(decoy, org_a)

    response = _list(caller, organization="notanumber")

    assert _listed_ids(response) == set()


def test_empty_string_ids_is_filter_absent_returns_full_list(authed_client):
    # Pinned as-is: an empty-string ``ids`` value is falsy, so the ``if ids_param:``
    # guard treats it as filter-absent and the full user list returns -- empty
    # string means "no filter", not "match nothing". Two decoys plus the caller are
    # hand-listed so a handler that mistakenly narrowed on the empty value fails.
    caller = _superuser(authed_client)
    alice = UserFactory()
    bob = UserFactory()

    response = _list(caller, ids="")

    assert _listed_ids(response) == {caller.user.id, alice.id, bob.id}


def test_empty_string_organization_is_filter_absent_returns_full_list(authed_client):
    # Pinned as-is: an empty-string ``organization`` value is falsy, so the
    # ``if org_param:`` guard treats it as filter-absent and the full user list
    # returns -- it does not reach the ``int(...)`` conversion (contrast the
    # non-integer value, which does and returns empty). Decoys plus the caller are
    # hand-listed so a narrowing regression fails.
    caller = _superuser(authed_client)
    alice = UserFactory()
    bob = UserFactory()

    response = _list(caller, organization="")

    assert _listed_ids(response) == {caller.user.id, alice.id, bob.id}


def test_empty_string_email_is_filter_absent_returns_full_list(authed_client):
    # Pinned as-is: an empty-string ``email`` value is falsy, so the
    # ``if email_param:`` guard treats it as filter-absent and the full user list
    # returns -- it does not run an ``email=""`` exact match (which would return
    # empty). Decoys plus the caller are hand-listed so a narrowing regression fails.
    caller = _superuser(authed_client)
    alice = UserFactory()
    bob = UserFactory()

    response = _list(caller, email="")

    assert _listed_ids(response) == {caller.user.id, alice.id, bob.id}


def test_organization_filter_deduplicates_multiple_memberships(authed_client, org_a):
    # A user holding two membership rows in the *same* workspace appears exactly
    # once: the ``organization`` filter joins across the membership relation (which
    # would surface the user once per matching row) and applies ``.distinct()`` to
    # collapse the duplicates. Asserted against the response as a *list* rather than
    # a set, so a regressed ``.distinct()`` -- which would list the user twice --
    # goes red; an unordered-set comparison would mask the duplicate. Two membership
    # rows are created for the one user in org_a (distinct roles, same workspace).
    caller = _superuser(authed_client)
    member = UserFactory()
    _member(member, org_a, role_name="org-admin")
    _member(member, org_a, role_name="org-view")

    response = _list(caller, organization=str(org_a.id))

    assert _listed_id_sequence(response) == [member.id]


def test_soft_deleted_user_absent_from_ids_and_email_filters(authed_client):
    # A soft-deleted user never resurfaces through the filters: their base queryset
    # is ``User.objects`` (the django-safedelete manager), which excludes
    # soft-deleted rows. The user is built, its id and email captured, then deleted
    # via the model instance's own ``delete()`` (a soft delete -- no raw SQL, no
    # ``all_objects`` shortcut); an ``ids`` request and an ``email`` request that
    # each explicitly target the captured identifiers both come back empty.
    caller = _superuser(authed_client)
    doomed = UserFactory(email="soft-deleted-target@example.com")
    doomed_id = doomed.id
    doomed_email = doomed.email
    doomed.delete()

    assert _listed_ids(_list(caller, ids=str(doomed_id))) == set()
    assert _listed_ids(_list(caller, email=doomed_email)) == set()
