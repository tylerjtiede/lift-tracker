import pytest
from lift_tracker.analysis import compute_progression, compute_plateau, compute_gaps


# --- compute_progression ---

def test_progression_insufficient_data():
    history = [{"session_date": "2026-04-01", "weight": 135.0}]
    result = compute_progression(history)
    assert result["trend"] == "insufficient_data"
    assert result["sessions_analyzed"] == 1


def test_progression_improving():
    history = [
        {"session_date": "2026-03-01", "weight": 135.0},
        {"session_date": "2026-03-08", "weight": 145.0},
        {"session_date": "2026-03-15", "weight": 155.0},
    ]
    result = compute_progression(history)
    assert result["trend"] == "improving"


def test_progression_declining():
    history = [
        {"session_date": "2026-03-01", "weight": 225.0},
        {"session_date": "2026-03-08", "weight": 205.0},
        {"session_date": "2026-03-15", "weight": 185.0},
    ]
    result = compute_progression(history)
    assert result["trend"] == "declining"


def test_progression_stalling():
    history = [
        {"session_date": "2026-03-01", "weight": 185.0},
        {"session_date": "2026-03-08", "weight": 185.0},
        {"session_date": "2026-03-15", "weight": 185.0},
    ]
    result = compute_progression(history)
    assert result["trend"] == "stalling"


def test_progression_uses_max_weight_per_session():
    # Multiple sets in the same session — should use the max
    history = [
        {"session_date": "2026-03-01", "weight": 135.0},
        {"session_date": "2026-03-01", "weight": 155.0},
        {"session_date": "2026-03-08", "weight": 165.0},
    ]
    result = compute_progression(history)
    assert result["trend"] == "improving"
    assert result["max_weights"][0]["weight"] == 155.0


def test_progression_num_sessions_limit():
    history = [
        {"session_date": f"2026-0{i}-01", "weight": float(100 + i * 10)}
        for i in range(1, 8)
    ]
    result = compute_progression(history, num_sessions=3)
    assert result["sessions_analyzed"] == 3


# --- compute_plateau ---

def test_plateau_insufficient_data():
    history = [
        {"session_date": "2026-03-01", "weight": 185.0},
        {"session_date": "2026-03-08", "weight": 185.0},
    ]
    result = compute_plateau(history)
    assert result["plateau"] is False


def test_plateau_detected():
    history = [
        {"session_date": "2026-03-01", "weight": 185.0},
        {"session_date": "2026-03-08", "weight": 185.0},
        {"session_date": "2026-03-15", "weight": 185.0},
    ]
    result = compute_plateau(history)
    assert result["plateau"] is True
    assert result["sessions_stalled"] == 3
    assert result["stuck_weight"] == 185.0


def test_no_plateau_when_improving():
    history = [
        {"session_date": "2026-03-01", "weight": 175.0},
        {"session_date": "2026-03-08", "weight": 180.0},
        {"session_date": "2026-03-15", "weight": 185.0},
    ]
    result = compute_plateau(history)
    assert result["plateau"] is False


# --- compute_gaps ---

def make_session(date_str, sets):
    return {"date": date_str, "sets": sets}


def make_set(muscle_group):
    return {"muscle_group": muscle_group}


def test_gaps_empty_sessions():
    result = compute_gaps([])
    assert result == []


def test_gaps_inactivity(freezegun_date=None):
    # A session from 15 days ago should trigger inactivity
    from datetime import date, timedelta
    old_date = (date.today() - timedelta(days=15)).isoformat()
    sessions = [make_session(old_date, [make_set("chest")])]
    result = compute_gaps(sessions)
    types = [suggestion["type"] for suggestion in result]
    assert "inactivity" in types


def test_gaps_insufficient_recovery():
    from datetime import date, timedelta
    day1 = (date.today() - timedelta(days=3)).isoformat()
    day2 = (date.today() - timedelta(days=2)).isoformat()  # only 1 day gap
    sessions = [
        make_session(day1, [make_set("chest")]),
        make_session(day2, [make_set("chest")]),
    ]
    result = compute_gaps(sessions)
    types = [suggestion["type"] for suggestion in result]
    assert "insufficient_recovery" in types


def test_gaps_missed_group():
    from datetime import date, timedelta
    old_date = (date.today() - timedelta(days=10)).isoformat()
    sessions = [make_session(old_date, [make_set("legs")])]
    result = compute_gaps(sessions)
    types = [suggestion["type"] for suggestion in result]
    assert "missed_group" in types


def test_gaps_no_issues():
    from datetime import date, timedelta
    # Recent sessions with sufficient recovery — no issues expected for trained groups
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    sessions = [make_session(yesterday, [make_set("chest")])]
    result = compute_gaps(sessions)
    # Should not flag insufficient recovery (only one session)
    types = [suggestion["type"] for suggestion in result]
    assert "insufficient_recovery" not in types
