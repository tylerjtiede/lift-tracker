import pytest
from lift_tracker.analysis import compute_progression, compute_plateau, compute_gaps


# --- compute_progression ---

def test_progression_insufficient_data():
    """Returns insufficient_data trend when fewer than 2 sessions are in the history."""
    history = [{"session_date": "2026-04-01", "weight": 135.0}]
    result = compute_progression(history)
    assert result["trend"] == "insufficient_data"
    assert result["sessions_analyzed"] == 1


def test_progression_improving():
    """Returns improving trend when the most recent session's max weight exceeds the oldest."""
    history = [
        {"session_date": "2026-03-01", "weight": 135.0},
        {"session_date": "2026-03-08", "weight": 145.0},
        {"session_date": "2026-03-15", "weight": 155.0},
    ]
    result = compute_progression(history)
    assert result["trend"] == "improving"


def test_progression_declining():
    """Returns declining trend when the most recent session's max weight is below the oldest."""
    history = [
        {"session_date": "2026-03-01", "weight": 225.0},
        {"session_date": "2026-03-08", "weight": 205.0},
        {"session_date": "2026-03-15", "weight": 185.0},
    ]
    result = compute_progression(history)
    assert result["trend"] == "declining"


def test_progression_stalling():
    """Returns stalling trend when max weight is unchanged across all sessions."""
    history = [
        {"session_date": "2026-03-01", "weight": 185.0},
        {"session_date": "2026-03-08", "weight": 185.0},
        {"session_date": "2026-03-15", "weight": 185.0},
    ]
    result = compute_progression(history)
    assert result["trend"] == "stalling"


def test_progression_uses_max_weight_per_session():
    """Uses the heaviest set per session, not the first or last set logged."""
    history = [
        {"session_date": "2026-03-01", "weight": 135.0},
        {"session_date": "2026-03-01", "weight": 155.0},
        {"session_date": "2026-03-08", "weight": 165.0},
    ]
    result = compute_progression(history)
    assert result["trend"] == "improving"
    assert result["max_weights"][0]["weight"] == 155.0


def test_progression_num_sessions_limit():
    """Respects num_sessions and only analyzes the most recent N sessions."""
    history = [
        {"session_date": f"2026-0{i}-01", "weight": float(100 + i * 10)}
        for i in range(1, 8)
    ]
    result = compute_progression(history, num_sessions=3)
    assert result["sessions_analyzed"] == 3


# --- compute_plateau ---

def test_plateau_insufficient_data():
    """Returns plateau=False when fewer than 3 sessions exist."""
    history = [
        {"session_date": "2026-03-01", "weight": 185.0},
        {"session_date": "2026-03-08", "weight": 185.0},
    ]
    result = compute_plateau(history)
    assert result["plateau"] is False


def test_plateau_detected():
    """Detects a plateau when max weight is unchanged across 3 or more consecutive sessions."""
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
    """Returns plateau=False when weight is consistently increasing."""
    history = [
        {"session_date": "2026-03-01", "weight": 175.0},
        {"session_date": "2026-03-08", "weight": 180.0},
        {"session_date": "2026-03-15", "weight": 185.0},
    ]
    result = compute_plateau(history)
    assert result["plateau"] is False


# --- compute_gaps ---

def make_session(date_str, sets):
    """Helper to build a session dict in the shape returned by get_program_sessions()."""
    return {"date": date_str, "sets": sets}


def make_set(muscle_group):
    """Helper to build a set dict with a muscle_group."""
    return {"muscle_group": muscle_group}


def test_gaps_empty_sessions():
    """Returns an empty list when no sessions have been logged."""
    result = compute_gaps([])
    assert result == []


def test_gaps_inactivity(freezegun_date=None):
    """Flags inactivity when the most recent session was more than 10 days ago."""
    from datetime import date, timedelta
    old_date = (date.today() - timedelta(days=15)).isoformat()
    sessions = [make_session(old_date, [make_set("chest")])]
    result = compute_gaps(sessions)
    types = [suggestion["type"] for suggestion in result]
    assert "inactivity" in types


def test_gaps_insufficient_recovery():
    """Flags insufficient_recovery when the same muscle group is trained less than 48 hours apart."""
    from datetime import date, timedelta
    day1 = (date.today() - timedelta(days=3)).isoformat()
    day2 = (date.today() - timedelta(days=2)).isoformat()
    sessions = [
        make_session(day1, [make_set("chest")]),
        make_session(day2, [make_set("chest")]),
    ]
    result = compute_gaps(sessions)
    types = [suggestion["type"] for suggestion in result]
    assert "insufficient_recovery" in types


def test_gaps_missed_group():
    """Flags missed_group when a muscle group hasn't been trained in more than 7 days."""
    from datetime import date, timedelta
    old_date = (date.today() - timedelta(days=10)).isoformat()
    sessions = [make_session(old_date, [make_set("legs")])]
    result = compute_gaps(sessions)
    types = [suggestion["type"] for suggestion in result]
    assert "missed_group" in types


def test_gaps_no_issues():
    """Does not flag insufficient_recovery when a muscle group only appears in a single session."""
    from datetime import date, timedelta
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    sessions = [make_session(yesterday, [make_set("chest")])]
    result = compute_gaps(sessions)
    types = [suggestion["type"] for suggestion in result]
    assert "insufficient_recovery" not in types
