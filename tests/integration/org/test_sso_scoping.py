"""Cross-org SSO scoping.

A user minted through an org's ``api_key`` is scoped to that org (``auth_org`` +
``unique_id``). This slice starts from already-minted SSO users (the auth flows
themselves are the auth slice) and proves the scoping holds across orgs:

- the same ``unique_id`` presented with a different org's ``api_key`` is a
  different person, bound to that other org;
- an org-a-minted identity carries no authoring rights into org-b's workspace,
  even though its token is a genuine, authenticated credential.
"""


def test_sso_identity_is_scoped_per_org(sso_login, org_a, org_b):
    org_a_user = sso_login("shared-learner", org_a)
    org_b_user = sso_login("shared-learner", org_b)

    # the same unique_id under a different org's api_key is a distinct user
    assert org_a_user.user.id != org_b_user.user.id
    assert org_a_user.user.auth_org_id == org_a.id
    assert org_b_user.user.auth_org_id == org_b.id


def test_org_a_sso_user_is_denied_write_access_under_org_b_header(
    sso_login, creator, org_a, org_b
):
    sso_user = sso_login("sso-writer", org_a)

    # the minted token is a real, authenticated credential ...
    assert sso_user.get("/api/v1/plios/", organization=org_b).status_code == 200
    # ... yet an org-a-scoped identity gets no authoring rights under org-b
    assert (
        sso_user.post(
            "/api/v1/plios/", {"name": "intruder"}, organization=org_b
        ).status_code
        == 403
    )
    # a genuine org-b member is allowed the same write
    assert (
        creator.post(
            "/api/v1/plios/", {"name": "member plio"}, organization=org_b
        ).status_code
        == 201
    )
