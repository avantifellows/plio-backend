"""The exhaustive plio access matrix.

Every combination of ``role`` (member / non-member / superuser) x ``workspace``
(personal / org) x ``visibility`` (public / private) is a distinct parametrized
case with its expected outcome stated per cell. The plio under test is always
owned by a separate ``owner``, so access is decided by the matrix axes and never
by the actor happening to be the creator.

Expected outcomes are hand-derived from the permission rules in
``plio/permissions.py`` and ``plio/views.py`` (read as the spec) and stated as
literal status codes / counts here -- never recomputed by calling the app.
Tenancy is exercised only through the ``Organization`` header.
"""
from collections import namedtuple

import pytest

# workspace: "personal" (public schema, no header) or "org" (org-a header)
# role:      "member" | "non_member" | "superuser"
# visibility:"public" | "private"
# list_count: plios the actor sees in GET /plios/ for this cell (only the
#             owner's single plio can ever appear)
# retrieve/play/mutate: expected HTTP status for the detail endpoints
Cell = namedtuple(
    "Cell",
    "id workspace role visibility list_count retrieve play mutate",
)

MATRIX = [
    # --- personal workspace (public schema): access needs ownership; only a
    #     superuser bypasses object permission. list is always own-plios-only. ---
    Cell("personal-member-public", "personal", "member", "public", 0, 403, 200, 403),
    Cell("personal-member-private", "personal", "member", "private", 0, 403, 404, 403),
    Cell(
        "personal-nonmember-public",
        "personal",
        "non_member",
        "public",
        0,
        403,
        200,
        403,
    ),
    Cell(
        "personal-nonmember-private",
        "personal",
        "non_member",
        "private",
        0,
        403,
        404,
        403,
    ),
    Cell(
        "personal-superuser-public", "personal", "superuser", "public", 0, 200, 200, 200
    ),
    Cell(
        "personal-superuser-private",
        "personal",
        "superuser",
        "private",
        0,
        200,
        404,
        200,
    ),
    # --- org workspace: members see/edit public plios; private plios stay with
    #     their creator; non-members are shut out; superuser bypasses object
    #     permission but is not a member so its list is empty; play is open to
    #     anyone for public plios regardless of membership. ---
    Cell("org-member-public", "org", "member", "public", 1, 200, 200, 200),
    Cell("org-member-private", "org", "member", "private", 0, 403, 404, 403),
    Cell("org-nonmember-public", "org", "non_member", "public", 0, 403, 200, 403),
    Cell("org-nonmember-private", "org", "non_member", "private", 0, 403, 404, 403),
    Cell("org-superuser-public", "org", "superuser", "public", 0, 200, 200, 200),
    Cell("org-superuser-private", "org", "superuser", "private", 0, 200, 404, 200),
]

MATRIX_IDS = [cell.id for cell in MATRIX]


def _header(cell, org_a):
    return org_a if cell.workspace == "org" else None


@pytest.mark.parametrize("cell", MATRIX, ids=MATRIX_IDS)
def test_plio_list_access(cell, make_plio, matrix_actor, org_a):
    plio = make_plio(cell.workspace, cell.visibility)
    actor = matrix_actor(cell.role)

    response = actor.get("/api/v1/plios/", organization=_header(cell, org_a))

    assert response.status_code == 200
    assert response.data["count"] == cell.list_count
    if cell.list_count:
        # the one plio the actor may see is exactly the owner's plio for this cell
        assert response.data["results"][0]["uuid"] == plio.uuid


@pytest.mark.parametrize("cell", MATRIX, ids=MATRIX_IDS)
def test_plio_retrieve_access(cell, make_plio, matrix_actor, org_a):
    plio = make_plio(cell.workspace, cell.visibility)
    actor = matrix_actor(cell.role)

    response = actor.get(
        "/api/v1/plios/{}/".format(plio.uuid), organization=_header(cell, org_a)
    )

    assert response.status_code == cell.retrieve


@pytest.mark.parametrize("cell", MATRIX, ids=MATRIX_IDS)
def test_plio_play_access(cell, make_plio, matrix_actor, org_a):
    plio = make_plio(cell.workspace, cell.visibility)
    actor = matrix_actor(cell.role)

    response = actor.get(
        "/api/v1/plios/{}/play/".format(plio.uuid), organization=_header(cell, org_a)
    )

    assert response.status_code == cell.play


@pytest.mark.parametrize("cell", MATRIX, ids=MATRIX_IDS)
def test_plio_mutate_access(cell, make_plio, matrix_actor, org_a):
    plio = make_plio(cell.workspace, cell.visibility)
    actor = matrix_actor(cell.role)

    response = actor.patch(
        "/api/v1/plios/{}/".format(plio.uuid),
        {"name": "renamed"},
        organization=_header(cell, org_a),
    )

    assert response.status_code == cell.mutate
