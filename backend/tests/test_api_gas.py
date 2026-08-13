from fastapi.testclient import TestClient


def make_payload(**overrides) -> dict:
    payload = {
        "date": "2021-01-01",
        "odometer_miles": 100000,
        "gallons": 20,
        "price": 60,
        "notes": "",
        "city": "Chicago, IL",
    }
    payload.update(overrides)
    return payload


class TestCreateFillup:
    def test_create_returns_201_with_computed_fields(self, client: TestClient):
        resp = client.post("/api/gas/fillups", json=make_payload())
        assert resp.status_code == 201
        body = resp.json()
        assert body["city"] == "Chicago, IL"
        assert body["latitude"] == 41.8781
        assert body["longitude"] == -87.6298
        assert body["cost_per_gal"] == 3.0
        assert body["driven"] is None
        assert body["mpg"] is None

    def test_second_fillup_computes_driven_and_mpg_from_first(self, client: TestClient):
        client.post("/api/gas/fillups", json=make_payload())
        resp = client.post(
            "/api/gas/fillups",
            json=make_payload(date="2021-01-08", odometer_miles=100300, gallons=15, price=45),
        )
        body = resp.json()
        assert body["driven"] == 300
        assert body["mpg"] == 20.0

    def test_reuses_existing_location_for_same_city_state(self, client: TestClient):
        client.post("/api/gas/fillups", json=make_payload())
        client.post("/api/gas/fillups", json=make_payload(date="2021-01-08"))
        fillups = client.get("/api/gas/fillups").json()
        assert len({f["city"] for f in fillups}) == 1

    def test_non_positive_gallons_rejected(self, client: TestClient):
        resp = client.post("/api/gas/fillups", json=make_payload(gallons=0))
        assert resp.status_code == 422

    def test_negative_price_rejected(self, client: TestClient):
        resp = client.post("/api/gas/fillups", json=make_payload(price=-1))
        assert resp.status_code == 422

    def test_blank_city_rejected(self, client: TestClient):
        resp = client.post("/api/gas/fillups", json=make_payload(city=""))
        assert resp.status_code == 422


class TestListFillups:
    def test_empty_when_no_fillups(self, client: TestClient):
        resp = client.get("/api/gas/fillups")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_recomputes_driven_and_mpg_for_every_row_on_read(self, client: TestClient):
        client.post("/api/gas/fillups", json=make_payload())
        client.post("/api/gas/fillups", json=make_payload(date="2021-01-08", odometer_miles=100300))

        resp = client.get("/api/gas/fillups")
        rows = resp.json()
        assert len(rows) == 2
        assert rows[0]["driven"] is None
        assert rows[1]["driven"] == 300

    def test_backdated_insert_shifts_later_rows_driven_on_next_read(self, client: TestClient):
        client.post("/api/gas/fillups", json=make_payload(date="2021-01-08", odometer_miles=100300))
        # Backdated fill-up inserted after the fact -- the later row's
        # driven/mpg should update on the next GET even though its own
        # stored fields were computed against a null "previous" at create time.
        client.post("/api/gas/fillups", json=make_payload(date="2021-01-01", odometer_miles=100000))

        rows = client.get("/api/gas/fillups").json()
        by_date = {r["date"]: r for r in rows}
        assert by_date["2021-01-01"]["driven"] is None
        assert by_date["2021-01-08"]["driven"] == 300


class TestUpdateFillup:
    def test_update_returns_updated_fields(self, client: TestClient):
        created = client.post("/api/gas/fillups", json=make_payload()).json()
        resp = client.put(f"/api/gas/fillups/{created['id']}", json=make_payload(gallons=25, price=75))
        assert resp.status_code == 200
        body = resp.json()
        assert body["gallons"] == 25
        assert body["cost_per_gal"] == 3.0

    def test_update_missing_fillup_returns_404(self, client: TestClient):
        resp = client.put("/api/gas/fillups/999", json=make_payload())
        assert resp.status_code == 404

    def test_update_invalid_payload_returns_422(self, client: TestClient):
        created = client.post("/api/gas/fillups", json=make_payload()).json()
        resp = client.put(f"/api/gas/fillups/{created['id']}", json=make_payload(gallons=0))
        assert resp.status_code == 422


class TestDeleteFillup:
    def test_delete_returns_204_and_removes_row(self, client: TestClient):
        created = client.post("/api/gas/fillups", json=make_payload()).json()
        resp = client.delete(f"/api/gas/fillups/{created['id']}")
        assert resp.status_code == 204
        assert client.get("/api/gas/fillups").json() == []

    def test_delete_missing_fillup_returns_404(self, client: TestClient):
        resp = client.delete("/api/gas/fillups/999")
        assert resp.status_code == 404
