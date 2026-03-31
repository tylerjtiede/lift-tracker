# lift-tracker

A FastAPI backend for tracking and analyzing strength training progress. Log workout sessions by exercise and program, then query for progression trends, plateau detection, training gaps, and AI-generated suggestions.

## Features

- **Session logging** — record exercises, sets, reps, and weight per workout
- **Program organization** — group sessions under named programs (PPL, 5/3/1, etc.)
- **Progression tracking** — trend analysis on max weight per exercise over time
- **Plateau detection** — flags exercises with no weight increase over N sessions
- **Gap analysis** — detects missed muscle groups, insufficient recovery time, and long absences
- **Suggestions** — rule-based recommendations based on your training history

## Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/) — REST API framework
- [SQLite](https://www.sqlite.org/) — embedded database, zero config
- [Pydantic v2](https://docs.pydantic.dev/) — request/response validation
- [Uvicorn](https://www.uvicorn.org/) — ASGI server
- Deployed on [Render](https://render.com)

## Project Structure

```
lift-tracker/
├── src/
│   └── lift_tracker/
│       ├── main.py        # FastAPI app and route definitions
│       ├── database.py    # SQLite connection and schema initialization
│       ├── models.py      # Pydantic request/response models
│       └── analysis.py    # Progression, plateau, and gap logic
├── static/
│   └── index.html         # Web UI
├── tests/
├── pyproject.toml
├── requirements.txt
└── .env.example
```

## Local Development

```bash
# Clone and enter the repo
git clone https://github.com/tylerjtiede/lift-tracker
cd lift-tracker

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy env file and configure
cp .env.example .env

# Run the dev server
uvicorn src.lift_tracker.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/programs` | Create a training program |
| GET | `/programs` | List all programs |
| POST | `/sessions` | Log a workout session |
| GET | `/sessions/{id}` | Get a session with its sets |
| POST | `/sessions/{id}/sets` | Add sets to a session |
| GET | `/exercises/{name}/history` | Full set history for an exercise |
| GET | `/exercises/{name}/progression` | Weight trend over time |
| GET | `/exercises/{name}/plateau` | Plateau detection |
| GET | `/programs/{id}/gaps` | Gap and recovery analysis with suggestions |

## Deployment

This project is deployed on Render as a web service. The `requirements.txt` is used for dependency installation. SQLite is used for persistence — the database file is stored on Render's persistent disk.
