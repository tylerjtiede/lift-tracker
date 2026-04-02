from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from lift_tracker import database, analysis
from lift_tracker.database import DuplicateError
from lift_tracker.models import (
    ProgramCreate,
    ProgramResponse,
    SessionCreate,
    SessionResponse,
    SessionWithSetsResponse,
    SetCreate,
    SetResponse,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(title="Lift Tracker", lifespan=lifespan)


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")


# --- Programs ---

@app.post("/programs", response_model=ProgramResponse, status_code=201)
def create_program(body: ProgramCreate):
    try:
        return database.create_program(body.name, body.description)
    except DuplicateError as err:
        raise HTTPException(status_code=409, detail=str(err))


@app.get("/programs", response_model=list[ProgramResponse])
def list_programs():
    return database.list_programs()


# --- Sessions ---

@app.post("/sessions", response_model=SessionResponse, status_code=201)
def create_session(body: SessionCreate):
    return database.create_session(body.program_id, body.date, body.notes)


@app.get("/sessions/{session_id}", response_model=SessionWithSetsResponse)
def get_session(session_id: int):
    session = database.get_session_with_sets(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# --- Sets ---

@app.post("/sessions/{session_id}/sets", response_model=SetResponse, status_code=201)
def add_set(session_id: int, body: SetCreate):
    session = database.get_session_with_sets(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return database.add_set(
        session_id=session_id,
        exercise=body.exercise,
        muscle_group=body.muscle_group,
        weight=body.weight,
        reps=body.reps,
        set_number=body.set_number,
    )


# --- Exercise analysis ---

@app.get("/exercises/{name}/history")
def exercise_history(name: str):
    return database.get_exercise_history(name)


@app.get("/exercises/{name}/progression")
def exercise_progression(name: str):
    history = database.get_exercise_history(name)
    return analysis.compute_progression(history)


@app.get("/exercises/{name}/plateau")
def exercise_plateau(name: str):
    history = database.get_exercise_history(name)
    return analysis.compute_plateau(history)


# --- Gap analysis ---

@app.get("/programs/{program_id}/gaps")
def program_gaps(program_id: int):
    program = database.get_program(program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    sessions = database.get_program_sessions(program_id)
    return analysis.compute_gaps(sessions)
