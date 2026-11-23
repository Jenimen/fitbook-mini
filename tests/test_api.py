import pytest
from fastapi.testclient import TestClient

ADMIN = {"X-Role": "admin"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from app.main import app

    with TestClient(app) as c:
        yield c


def make_session(client, capacity=2):
    resp = client.post(
        "/sessions",
        json={"name": "Jóga", "trainer": "Anna", "starts_at": "2026-12-20T18:00:00", "capacity": capacity},
        headers=ADMIN,
    )
    assert resp.status_code == 201
    return resp.json()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_admin_creates_session(client):
    session = make_session(client, capacity=12)
    assert session["free_places"] == 12
    assert client.get("/sessions").json()[0]["name"] == "Jóga"


def test_member_cannot_create_session(client):
    resp = client.post(
        "/sessions",
        json={"name": "Jóga", "trainer": "Anna", "starts_at": "2026-12-20T18:00:00", "capacity": 5},
    )
    assert resp.status_code == 403


@pytest.mark.parametrize("capacity, expected", [(0, 422), (1, 201), (50, 201), (51, 422)])
def test_capacity_boundaries(client, capacity, expected):
    resp = client.post(
        "/sessions",
        json={"name": "Jóga", "trainer": "Anna", "starts_at": "2026-12-20T18:00:00", "capacity": capacity},
        headers=ADMIN,
    )
    assert resp.status_code == expected


def test_booking_until_full_then_waitlist(client):
    sid = make_session(client, capacity=1)["id"]
    first = client.post(f"/sessions/{sid}/bookings", json={"member": "Béla"}).json()
    second = client.post(f"/sessions/{sid}/bookings", json={"member": "Cili"}).json()
    assert first["status"] == "ACTIVE"
    assert second["status"] == "WAITLISTED"
    assert client.get(f"/sessions/{sid}").json()["free_places"] == 0


def test_double_booking_rejected(client):
    sid = make_session(client)["id"]
    client.post(f"/sessions/{sid}/bookings", json={"member": "Béla"})
    resp = client.post(f"/sessions/{sid}/bookings", json={"member": "Béla"})
    assert resp.status_code == 409


def test_cancel_promotes_first_waitlisted(client):
    sid = make_session(client, capacity=1)["id"]
    active = client.post(f"/sessions/{sid}/bookings", json={"member": "Béla"}).json()
    waiting = client.post(f"/sessions/{sid}/bookings", json={"member": "Cili"}).json()
    resp = client.delete(f"/bookings/{active['id']}")
    assert resp.status_code == 200
    assert resp.json()["promoted"] == waiting["id"]
    assert client.get(f"/sessions/{sid}").json()["booked"] == 1


def test_cancel_twice_rejected(client):
    sid = make_session(client)["id"]
    booking = client.post(f"/sessions/{sid}/bookings", json={"member": "Béla"}).json()
    client.delete(f"/bookings/{booking['id']}")
    assert client.delete(f"/bookings/{booking['id']}").status_code == 409


def test_unknown_session_404(client):
    assert client.post("/sessions/999/bookings", json={"member": "Béla"}).status_code == 404
