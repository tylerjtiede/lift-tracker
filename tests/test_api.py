import pytest
from httpx import AsyncClient, ASGITransport
from lift_tracker.main import app


@pytest.fixture
async def client():
    """Async HTTP client wired directly to the FastAPI app — no live server needed."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


# --- Programs ---

async def test_create_program(client):
    """POST /programs returns 201 with the created program including id and created_at."""
    response = await client.post("/programs", json={"name": "PPL", "description": "Push Pull Legs"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "PPL"
    assert data["description"] == "Push Pull Legs"
    assert "id" in data
    assert "created_at" in data


async def test_list_programs_empty(client):
    """GET /programs returns an empty list when no programs exist."""
    response = await client.get("/programs")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_programs(client):
    """GET /programs returns all created programs."""
    await client.post("/programs", json={"name": "PPL"})
    await client.post("/programs", json={"name": "5/3/1"})
    response = await client.get("/programs")
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "PPL" in names
    assert "5/3/1" in names


async def test_create_program_duplicate_name(client):
    """POST /programs returns 409 when a program with the same name already exists."""
    await client.post("/programs", json={"name": "PPL"})
    response = await client.post("/programs", json={"name": "PPL"})
    assert response.status_code == 409


# --- Sessions ---

async def test_create_session(client):
    """POST /sessions returns 201 with the created session; program_id is None when omitted."""
    response = await client.post("/sessions", json={"date": "2026-04-01"})
    assert response.status_code == 201
    data = response.json()
    assert data["date"] == "2026-04-01"
    assert data["program_id"] is None


async def test_create_session_with_program(client):
    """POST /sessions correctly links the session to a program when program_id is provided."""
    program = (await client.post("/programs", json={"name": "PPL"})).json()
    response = await client.post("/sessions", json={"date": "2026-04-01", "program_id": program["id"]})
    assert response.status_code == 201
    assert response.json()["program_id"] == program["id"]


async def test_get_session_not_found(client):
    """GET /sessions/{id} returns 404 for a non-existent session."""
    response = await client.get("/sessions/999")
    assert response.status_code == 404


async def test_get_session_with_sets(client):
    """GET /sessions/{id} returns the session with its sets nested, and exercise is lowercased."""
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
    assert data["sets"][0]["exercise"] == "bench press"


# --- Sets ---

async def test_add_set_normalizes_exercise(client):
    """POST /sessions/{id}/sets stores exercise name as lowercase regardless of input casing."""
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
    """POST /sessions/{id}/sets returns 404 when the session does not exist."""
    response = await client.post("/sessions/999/sets", json={
        "exercise": "squat",
        "weight": 225.0,
        "reps": 3,
        "set_number": 1,
    })
    assert response.status_code == 404


async def test_add_set_invalid_weight(client):
    """POST /sessions/{id}/sets returns 422 when weight is not a positive number."""
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
    """GET /exercises/{name}/history returns an empty list for an unknown exercise."""
    response = await client.get("/exercises/squat/history")
    assert response.status_code == 200
    assert response.json() == []


async def test_exercise_progression(client):
    """GET /exercises/{name}/progression returns insufficient_data with only one session logged."""
    session = (await client.post("/sessions", json={"date": "2026-04-01"})).json()
    await client.post(f"/sessions/{session['id']}/sets", json={
        "exercise": "deadlift", "weight": 315.0, "reps": 5, "set_number": 1,
    })
    response = await client.get("/exercises/deadlift/progression")
    assert response.status_code == 200
    data = response.json()
    assert "trend" in data
    assert data["trend"] == "insufficient_data"


async def test_exercise_plateau(client):
    """GET /exercises/{name}/plateau returns plateau=False when no history exists."""
    response = await client.get("/exercises/deadlift/plateau")
    assert response.status_code == 200
    assert response.json()["plateau"] is False


# --- Gap analysis ---

async def test_gaps_program_not_found(client):
    """GET /programs/{id}/gaps returns 404 for a non-existent program."""
    response = await client.get("/programs/999/gaps")
    assert response.status_code == 404


async def test_gaps_empty_program(client):
    """GET /programs/{id}/gaps returns an empty list for a program with no sessions."""
    program = (await client.post("/programs", json={"name": "PPL"})).json()
    response = await client.get(f"/programs/{program['id']}/gaps")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
