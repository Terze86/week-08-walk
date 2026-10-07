import pytest
from fastapi.testclient import TestClient

from tests.conftest import as_user


@pytest.mark.urs("WF-01.02", "WF-01.03")
def test_each_person_sees_their_own_workspaces(client: TestClient, staff) -> None:
    r = client.get("/api/me", headers=as_user("cs1"))
    assert r.status_code == 200
    assert r.json()["username"] == "cs1"
    assert [w["key"] for w in r.json()["workspaces"]] == ["case-scientist"]
    r = client.get("/api/me", headers=as_user("codis1"))
    assert [w["key"] for w in r.json()["workspaces"]] == ["codis"]


def test_unknown_or_missing_user_is_rejected(client: TestClient, staff) -> None:
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers=as_user("nobody")).status_code == 403


@pytest.mark.urs("WF-01.01", "WF-19.01")
def test_admin_maintains_accounts_with_reasons(client: TestClient, staff) -> None:
    admin = as_user("admin1")
    r = client.post(
        "/api/admin/users",
        headers=admin,
        json={"username": "cs3", "display_name": "New Scientist", "roles": ["case_scientist"]},
    )
    assert r.status_code == 201, r.text
    uid = r.json()["id"]

    r = client.put(f"/api/admin/users/{uid}/roles", headers=admin, json={"roles": ["reviewer"]})
    assert r.status_code == 422  # reason required

    r = client.put(
        f"/api/admin/users/{uid}/roles",
        headers=admin,
        json={"roles": ["case_scientist", "reviewer"], "reason": "Authorised as reviewer"},
    )
    assert sorted(r.json()["roles"]) == ["case_scientist", "reviewer"]
    r = client.put(
        f"/api/admin/users/{uid}/roles",
        headers=admin,
        json={"roles": ["reviewer", "case_scientist"], "reason": "Repeat"},
    )
    assert r.status_code == 400  # no-op changes are refused, not audited

    r = client.put(
        f"/api/admin/users/{uid}/status",
        headers=admin,
        json={"status": "disabled", "reason": "Left the laboratory"},
    )
    assert r.json()["status"] == "disabled"
    assert client.get("/api/me", headers=as_user("cs3")).status_code == 403

    events = client.get("/api/admin/audit", headers=admin, params={"entity_id": uid}).json()
    assert [e["action"] for e in events] == [
        "user.status_changed",
        "user.roles_changed",
        "user.created",
    ]
    assert events[0]["reason"] == "Left the laboratory"
    assert client.get("/api/admin/audit/verify", headers=admin).json()["intact"] is True


@pytest.mark.urs("WF-19.01", "WF-19.04")
def test_admin_console_is_admin_only_and_not_self_service(client: TestClient, staff) -> None:
    assert client.get("/api/admin/users", headers=as_user("cs1")).status_code == 403
    admin_id = staff["admin1"].id
    r = client.put(
        f"/api/admin/users/{admin_id}/roles",
        headers=as_user("admin1"),
        json={"roles": ["lims_admin", "reviewer"], "reason": "self-escalation"},
    )
    assert r.status_code == 403


def test_laboratories(client: TestClient, staff) -> None:
    r = client.post(
        "/api/admin/laboratories",
        headers=as_user("admin1"),
        json={"code": "BIO", "name": "Biology"},
    )
    assert r.status_code == 201
    lab_id = r.json()["id"]
    r = client.put(
        f"/api/admin/users/{staff['cs1'].id}/laboratories",
        headers=as_user("admin1"),
        json={"laboratory_ids": [lab_id], "reason": "Joined biology"},
    )
    assert r.json()["laboratory_ids"] == [lab_id]
