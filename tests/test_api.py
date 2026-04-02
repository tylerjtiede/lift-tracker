import pytest
from httpx import AsyncClient, ASGITransport
from lift_tracker.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


# --- Programs ---

async def test_create_program(client):
    response = await client.post("/programs", json={"name": "PPL", "description": "Push Pull Legs"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "PPL"
    assert data["description"] == "Push Pull Legs"
    assert "id" in data
    assert "created_at" in data


async def test_list_programs_empty(client):
    response = await client.get("/programs")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_programs(client):
    await client.post("/programs", json={"name": "PPL"})
    await client.post("/programs", json={"name": "5/3/1"})
    response = await client.get("/programs")
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "PPL" in names
    assert "5/3/1" in names


async def test_create_program_duplicate_name(client):
    await client.post("/programs", json={"name": "PPL"})
    response = await client.post("/programs", json={"name": "PPL"})
    assert response.status_code == 409


# --- Sessions ---

async def test_create_session(client):
    response = await client.post("/sessions", json={"date": "2026-04-01"})
    assert response.status_code == 201
    data = response.json()
    assert data["date"] == "2026-04-01"
    assert data["program_id"] is None


async def test_create_session_with_program(client):
    program = (await client.post("/programs", json={"name": "PPL"})).json()
    response = await client.post("/sessions", json={"date": "2026-04-01", "program_id": program["id"]})
    assert response.status_code == 201
    assert response.json()["program_id"] == program["id"]


async def test_get_session_not_found(client):
    response = await client.get("/sessions/999")
    assert response.status_code == 404


async def test_get_session_with_sets(client):
    session = (await client.post("/sessions", json={"date": "2026-04-01"})).json()
    await client.post(f"/sessions/{session['id']}/sets", json={
        "exercise": "Bench Press",
        "muscle_group": "chest",
        "weight": 185.0,
        "reps": 5,
        "set_number": 1,
    })
    response = await client.get(f"/sessions/{session['id']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sets"]) == 1
    assert data["sets"][0]["exercise"] == "bench press"  # normalized to lowercase


# --- Sets ---

async def test_add_set_normalizes_exercise(client):
    session = (await client.post("/sessions", json={"date": "2026-04-01"})).json()
    response = await client.post(f"/sessions/{session['id']}/sets", json={
        "exercise": "SQUAT",
        "muscle_group": "legs",
        "weight": 225.0,
        "reps": 3,
        "set_number": 1,
    })
    assert response.status_code == 201
    assert response.json()["exercise"] == "squat"


async def test_add_set_invalid_session(client):
    response = await client.post("/sessions/999/sets", json={
        "exercise": "squat",
        "weight": 225.0,
        "reps": 3,
        "set_number": 1,
    })
    assert response.status_code == 404


async def test_add_set_invalid_weight(client):
    session = (await client.post("/sessions", json={"date": "2026-04-01"})).json()
    response = await client.post(f"/sessions/{session['id']}/sets", json={
        "exercise": "squat",
        "weight": -10.0,
        "reps": 3,
        "set_number": 1,
    })
    assert response.status_code == 422


# --- Exercise analysis ---

async def test_exercise_history_empty(client):
    response = await client.get("/exercises/squat/history")
    assert response.status_code == 200
    assert response.json() == []


async def test_exercise_progression(client):
    session = (await client.post("/sessions", json={"date": "2026-04-01"})).json()
    await client.post(f"/sessions/{session['id']}/sets", json={
        "exercise": "deadlift", "weight": 315.0, "reps": 5, "set_number": 1,
    })
    response = await client.get("/exercises/deadlift/progression")
    assert response.status_code == 200
    data = response.json()
    assert "trend" in data
    assert data["trend"] == "insufficient_data"  # only 1 session


async def test_exercise_plateau(client):
    response = await client.get("/exercises/deadlift/plateau")
    assert response.status_code == 200
    assert response.json()["plateau"] is False


# --- Gap analysis ---

async def test_gaps_program_not_found(client):
    response = await client.get("/programs/999/gaps")
    assert response.status_code == 404


async def test_gaps_empty_program(client):
    program = (await client.post("/programs", json={"name": "PPL"})).json()
    response = await client.get(f"/programs/{program['id']}/gaps")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
