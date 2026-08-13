from fastapi.testclient import TestClient


class TestMapRoutes:
    def test_empty_db_returns_no_stops(self, client: TestClient):
        resp = client.get("/api/map/routes")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_stops"] == 0
        assert body["years"] == []

    def test_repeat_visits_to_same_location_each_get_their_own_point(self, client: TestClient):
        # Two fill-ups at the same city/state -- both should plot (actual
        # travel history), not collapse to the location's earliest visit.
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
            "/api/gas/fillups",
            json={
                "date": "2021-01-08",
                "odometer_miles": 100300,
                "gallons": 15,
                "price": 45,
                "notes": "",
                "city": "Chicago, IL",
            },
        )

        body = client.get("/api/map/routes").json()
        assert body["total_stops"] == 2
        [year] = body["years"]
        assert year["year"] == "2021"
        assert [loc["date"] for loc in year["locations"]] == ["2021-01-01", "2021-01-08"]


class TestHealth:
    def test_health_check(self, client: TestClient):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
