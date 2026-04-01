from pydantic import BaseModel, Field


# --- Programs ---

class ProgramCreate(BaseModel):
    name: str
    description: str | None = None


class ProgramResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: str


# --- Sessions ---

class SessionCreate(BaseModel):
    program_id: int | None = None
    date: str  # YYYY-MM-DD
    notes: str | None = None


class SessionResponse(BaseModel):
    id: int
    program_id: int | None
    date: str
    notes: str | None
    created_at: str


class SessionWithSetsResponse(BaseModel):
    id: int
    program_id: int | None
    date: str
    notes: str | None
    created_at: str
    sets: list["SetResponse"]


# --- Sets ---

class SetCreate(BaseModel):
    exercise: str
    muscle_group: str | None = None
    weight: float = Field(gt=0)
    reps: int = Field(gt=0)
    set_number: int = Field(gt=0)


class SetResponse(BaseModel):
    id: int
    session_id: int
    exercise: str
    muscle_group: str | None
    weight: float
    reps: int
    set_number: int
    created_at: str
