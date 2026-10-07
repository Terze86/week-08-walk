import base64

import pytest
from fastapi.testclient import TestClient

from app.core.files import get_file_store
from tests.casework import SIGNATURE_PNG
from tests.conftest import as_user


@pytest.fixture
def api(client: TestClient, file_store):
    client.app.dependency_overrides[get_file_store] = lambda: file_store
    return client


def ok(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


@pytest.mark.urs(
    "WF-02.01",
    "WF-02.03",
    "WF-02.06",
    "WF-02.07",
    "WF-02.08",
    "WF-02.09",
    "WF-02.11",
    "WF-03.04",
    "WF-03.08",
)
def test_reception_to_storage_to_handover_over_http(api: TestClient, staff, lab, setting) -> None:
    cs, slo = as_user("cs1"), as_user("slo1")
    detail = ok(
        api.post(
            "/api/cases",
            headers=cs,
            json={
                "laboratory_id": str(lab.id),
                "client_id": str(setting.client.id),
                "client_reference": "IR/2026/0412",
                "source": "paper",
                "submitter_name": "SSgt Tan",
                "investigating_officer_name": "Insp Lee",
            },
        ),
        201,
    )
    subcase_id = detail["subcases"][0]["id"]

    shirt = ok(
        api.post(
            f"/api/subcases/{subcase_id}/exhibits",
            headers=cs,
            json={"description": "Blue shirt", "marking": "A1", "seal": "S-0001"},
        ),
        201,
    )
    swab = ok(
        api.post(f"/api/subcases/{subcase_id}/exhibits", headers=cs, json={"description": "Swab"}),
        201,
    )
    ok(
        api.post(
            f"/api/exhibits/{shirt['id']}/accept",
            headers=cs,
            json={"description_matches": True, "marking_matches": True, "seal_intact": True},
        )
    )
    r = api.post(f"/api/exhibits/{swab['id']}/reject", headers=cs, json={"reason": ""})
    assert r.status_code == 422
    ok(api.post(f"/api/exhibits/{swab['id']}/reject", headers=cs, json={"reason": "Leaking"}))

    receipt = ok(
        api.post(
            f"/api/subcases/{subcase_id}/receipts", headers=cs, json={"exhibit_ids": [shirt["id"]]}
        ),
        201,
    )
    assert [e["barcode"] for e in receipt["accepted_exhibits"]] == [shirt["barcode"]]
    assert [e["rejection_reason"] for e in receipt["rejected_exhibits"]] == ["Leaking"]
    data_url = "data:image/png;base64," + base64.b64encode(SIGNATURE_PNG).decode()
    done = ok(
        api.post(
            f"/api/receipts/{receipt['id']}/complete",
            headers=cs,
            json={"actual_submitter_name": "Cpl Ong", "signature_png_base64": data_url},
        )
    )
    assert done["state"] == "completed" and done["receiving_staff"]["display_name"]
    sig = api.get(f"/api/receipts/{receipt['id']}/signature", headers=cs)
    assert sig.status_code == 200 and sig.content == SIGNATURE_PNG

    code = shirt["barcode"]
    stored = ok(
        api.post(
            "/api/custody/move",
            headers=cs,
            json={
                "barcodes": [code],
                "verified_barcodes": [code],
                "to_location_id": str(setting.store_a.id),
            },
        )
    )
    assert stored[0]["current"]["to_location"]["code"] == "STORE-A"

    # Retrieve to self, then hand over to the screening officer.
    ok(
        api.post(
            "/api/custody/move",
            headers=cs,
            json={"barcodes": [code], "verified_barcodes": [code], "keep_with_me": True},
        )
    )
    handover = ok(
        api.post(
            "/api/custody/handovers",
            headers=cs,
            json={
                "barcodes": [code],
                "verified_barcodes": [code],
                "to_person_id": str(staff["slo1"].id),
            },
        ),
        201,
    )
    work = ok(api.get("/api/my-work", headers=slo))
    assert [h["id"] for h in work["incoming_handovers"]] == [handover["id"]]
    r = api.post(
        f"/api/custody/handovers/{handover['id']}/accept",
        headers=as_user("dlo1"),
        json={"barcodes": [code], "verified_barcodes": [code]},
    )
    assert r.status_code == 403 and r.json()["rule"] == "SOD-HANDOVER"
    ok(
        api.post(
            f"/api/custody/handovers/{handover['id']}/accept",
            headers=slo,
            json={"barcodes": [code], "verified_barcodes": [code]},
        )
    )
    item = ok(api.get(f"/api/custody/items/{code}", headers=slo))
    assert item["current"]["to_person"]["id"] == str(staff["slo1"].id)
    assert [e["movement"]["kind"] for e in item["history"]] == [
        "receipt",
        "move",
        "move",
        "handover",
    ]


@pytest.mark.urs("WF-01.05", "WF-01.06")
def test_codis_and_admin_cannot_open_casework(api: TestClient, staff, lab, setting) -> None:
    detail = ok(
        api.post(
            "/api/cases",
            headers=as_user("cs1"),
            json={
                "laboratory_id": str(lab.id),
                "client_id": str(setting.client.id),
                "client_reference": "R",
                "source": "paper",
                "submitter_name": "S",
                "investigating_officer_name": "O",
            },
        ),
        201,
    )
    case_id = detail["case"]["id"]
    for user in ("codis1", "admin1"):
        assert api.get(f"/api/cases/{case_id}", headers=as_user(user)).status_code == 404
        assert api.get("/api/cases", headers=as_user(user)).json() == []
    assert api.get(f"/api/cases/{case_id}", headers=as_user("dlo1")).status_code == 200


def test_staff_picker_lists_casework_colleagues(api: TestClient, staff) -> None:
    names = {c["display_name"] for c in ok(api.get("/api/staff", headers=as_user("cs1")))}
    assert staff["slo1"].display_name in names
    assert staff["codis1"].display_name not in names
    assert staff["admin1"].display_name not in names
