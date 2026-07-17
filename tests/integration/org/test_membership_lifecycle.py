"""Org membership lifecycle: add a member, change the role, remove the member.

Access to the workspace flips immediately after each membership mutation, and
every mutation is driven through the real ``organization-users`` API by a
superuser. Roles come from the users-app data migration -- the specs never
build ad-hoc role machinery.

Two access probes observe the flips through the API:
- authoring: ``POST /plios/`` under the org header (403 for a non-member, 201
  for any member) -- flips on add and on remove;
- assignable roles: ``GET /roles/`` under the org header (an org-view member
  sees none, an org-admin sees the org-view role it may grant) -- flips on the
  role change.
"""
from users.models import Role


def test_membership_mutations_flip_workspace_access(authed_client, org_a):
    superadmin = authed_client()
    superadmin.user.is_superuser = True
    superadmin.user.save()

    candidate = authed_client()
    org_view = Role.objects.get(name="org-view")
    org_admin = Role.objects.get(name="org-admin")

    def author_in_org_a():
        return candidate.post(
            "/api/v1/plios/", {"name": "member plio"}, organization=org_a
        )

    def assignable_roles():
        return candidate.get("/api/v1/roles/", organization=org_a).data

    # --- not a member yet: cannot author in the workspace ---
    assert author_in_org_a().status_code == 403

    # --- add as an org-view member: authoring is now allowed ---
    added = superadmin.post(
        "/api/v1/organization-users/",
        {"user": candidate.user.id, "organization": org_a.id, "role": org_view.id},
    )
    assert added.status_code == 201
    membership_id = added.data["id"]

    assert author_in_org_a().status_code == 201
    # an org-view member has no roles it is allowed to assign
    assert len(assignable_roles()) == 0

    # --- promote to org-admin: the assignable-roles view opens up ---
    promoted = superadmin.patch(
        "/api/v1/organization-users/{}/".format(membership_id),
        {"role": org_admin.id},
    )
    assert promoted.status_code == 200
    # an org-admin may now assign the org-view role
    assert [role["name"] for role in assignable_roles()] == ["org-view"]

    # --- remove the member: authoring access is revoked ---
    removed = superadmin.delete("/api/v1/organization-users/{}/".format(membership_id))
    assert removed.status_code == 204
    assert author_in_org_a().status_code == 403
