from fastapi.testclient import TestClient


def make_payload(**overrides) -> dict:
    payload = {
        "date": "2021-03-15",
        "expense": "Oil change",
        "place": "Chicago, IL",
        "odometer_miles": 100000,
        "vendor": "Jiffy Lube",
        "cost": 60,
    }
    payload.update(overrides)
    return payload


class TestCreateRecord:
    def test_create_returns_201_with_place_from_location(self, client: TestClient):
        resp = client.post("/api/maintenance/records", json=make_payload())
        assert resp.status_code == 201
        body = resp.json()
        assert body["place"] == "Chicago, IL"
        assert body["is_major"] is False

    def test_cost_above_threshold_marked_major(self, client: TestClient):
        resp = client.post("/api/maintenance/records", json=make_payload(cost=2500, expense="Transmission"))
        assert resp.json()["is_major"] is True

    def test_blank_expense_rejected(self, client: TestClient):
        resp = client.post("/api/maintenance/records", json=make_payload(expense=""))
        assert resp.status_code == 422

    def test_blank_place_rejected(self, client: TestClient):
        resp = client.post("/api/maintenance/records", json=make_payload(place=""))
        assert resp.status_code == 422

    def test_negative_cost_is_allowed(self, client: TestClient):
        # Deliberately allowed: the historical log includes a legitimate
        # refund/credit entry recorded as a negative cost.
        resp = client.post("/api/maintenance/records", json=make_payload(cost=-25, expense="Refund"))
        assert resp.status_code == 201
        assert resp.json()["cost"] == -25


class TestListRecords:
    def test_empty_when_no_records(self, client: TestClient):
        resp = client.get("/api/maintenance/records")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_ordered_by_date(self, client: TestClient):
        client.post("/api/maintenance/records", json=make_payload(date="2021-06-01"))
        client.post("/api/maintenance/records", json=make_payload(date="2021-01-01"))
        rows = client.get("/api/maintenance/records").json()
        assert [r["date"] for r in rows] == ["2021-01-01", "2021-06-01"]


class TestUpdateRecord:
    def test_update_returns_updated_fields(self, client: TestClient):
        created = client.post("/api/maintenance/records", json=make_payload()).json()
        resp = client.put(f"/api/maintenance/records/{created['id']}", json=make_payload(cost=99, vendor="Midas"))
        assert resp.status_code == 200
        body = resp.json()
        assert body["cost"] == 99
        assert body["vendor"] == "Midas"

    def test_update_missing_record_returns_404(self, client: TestClient):
        resp = client.put("/api/maintenance/records/999", json=make_payload())
        assert resp.status_code == 404


class TestDeleteRecord:
    def test_delete_returns_204_and_removes_row(self, client: TestClient):
        created = client.post("/api/maintenance/records", json=make_payload()).json()
        resp = client.delete(f"/api/maintenance/records/{created['id']}")
        assert resp.status_code == 204
        assert client.get("/api/maintenance/records").json() == []

    def test_delete_missing_record_returns_404(self, client: TestClient):
        resp = client.delete("/api/maintenance/records/999")
        assert resp.status_code == 404
