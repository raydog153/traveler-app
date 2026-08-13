from fastapi.testclient import TestClient


class TestDashboardSummary:
    def test_empty_db_returns_valid_empty_summary(self, client: TestClient):
        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["subhead"] == ""
        assert body["yearly"] == []
        assert body["service_alert"] is None
        assert body["cost_of_ownership"]["total_cost"] == 0

    def test_reflects_created_fillups_and_maintenance(self, client: TestClient):
        client.post(
            "/api/gas/fillups",
            json={
                "date": "2021-01-01",
                "odometer_miles": 100000,
                "gallons": 20,
                "price": 60,
                "notes": "",
                "city": "Chicago, IL",
            },
        )
        client.post(
            "/api/maintenance/records",
            json={
                "date": "2021-02-01",
                "expense": "Oil change",
                "place": "Chicago, IL",
                "odometer_miles": 100200,
                "vendor": "",
                "cost": 50,
            },
        )

        body = client.get("/api/dashboard/summary").json()
        assert "1 fill-ups" in body["subhead"]
        assert "1 maintenance records" in body["subhead"]
        assert body["yearly"][0]["year"] == "2021"
