from datetime import date


def compute_progression(history: list[dict], num_sessions: int = 5) -> dict:
    """
    Takes the output of get_exercise_history() and returns a trend over the last N sessions.
    history: list of set dicts, each with 'session_date' and 'weight'.
    """
    session_max: dict[str, float] = {}
    for row in history:
        session_date = row["session_date"]
        session_max[session_date] = max(session_max.get(session_date, 0.0), row["weight"])

    sorted_dates = sorted(session_max.keys())
    recent_dates = sorted_dates[-num_sessions:]
    max_weights = [session_max[session_date] for session_date in recent_dates]

    if len(max_weights) < 2:
        trend = "insufficient_data"
    elif max_weights[-1] > max_weights[0]:
        trend = "improving"
    elif max_weights[-1] < max_weights[0]:
        trend = "declining"
    else:
        trend = "stalling"

    return {
        "sessions_analyzed": len(max_weights),
        "trend": trend,
        "max_weights": [
            {"date": session_date, "weight": weight}
            for session_date, weight in zip(recent_dates, max_weights)
        ],
    }


def compute_plateau(history: list[dict]) -> dict:
    """
    Returns plateau info for an exercise.
    A plateau is 3+ consecutive sessions with no increase in max weight.
    """
    session_max: dict[str, float] = {}
    for row in history:
        session_date = row["session_date"]
        session_max[session_date] = max(session_max.get(session_date, 0.0), row["weight"])

    sorted_dates = sorted(session_max.keys())
    max_weights = [session_max[session_date] for session_date in sorted_dates]

    if len(max_weights) < 3:
        return {"plateau": False, "sessions_stalled": 0, "stuck_weight": None}

    stalled = 1
    peak = max_weights[-1]
    for weight in reversed(max_weights[:-1]):
        if weight >= peak:
            stalled += 1
            peak = weight
        else:
            break

    plateau = stalled >= 3
    return {
        "plateau": plateau,
        "sessions_stalled": stalled if plateau else 0,
        "stuck_weight": peak if plateau else None,
    }


def compute_gaps(sessions: list[dict]) -> list[dict]:
    """
    Takes the output of get_program_sessions() and returns a list of suggestions.
    Each session dict has a 'date' and 'sets' list, each set has 'muscle_group'.
    """
    suggestions = []
    today = date.today()

    # Build a map of muscle_group -> sorted list of session dates
    muscle_dates: dict[str, list[date]] = {}
    session_dates: list[date] = []

    for session in sessions:
        session_date = date.fromisoformat(session["date"])
        session_dates.append(session_date)
        for workout_set in session.get("sets", []):
            muscle_group = workout_set.get("muscle_group")
            if muscle_group:
                muscle_dates.setdefault(muscle_group, []).append(session_date)

    for muscle_group in muscle_dates:
        muscle_dates[muscle_group] = sorted(set(muscle_dates[muscle_group]))

    # Flag muscle groups not hit in the last 7 days
    all_groups = {"chest", "back", "legs", "shoulders", "arms", "core"}
    for group in all_groups:
        if group not in muscle_dates:
            continue
        last_hit = muscle_dates[group][-1]
        days_since = (today - last_hit).days
        if days_since > 7:
            suggestions.append({
                "type": "missed_group",
                "muscle_group": group,
                "days_since": days_since,
                "suggestion": f"You haven't trained {group} in {days_since} days. Consider adding it to your next session.",
            })

    # Flag insufficient recovery (<48hrs between same muscle group)
    for group, dates in muscle_dates.items():
        for idx in range(1, len(dates)):
            gap = (dates[idx] - dates[idx - 1]).days
            if gap < 2:
                suggestions.append({
                    "type": "insufficient_recovery",
                    "muscle_group": group,
                    "days_between": gap,
                    "suggestion": f"{group.capitalize()} was trained {gap} day(s) apart. Allow at least 48 hours before training the same muscle group.",
                })

    # Flag general inactivity (session gap > 10 days)
    if session_dates:
        sorted_session_dates = sorted(session_dates)
        last_session = sorted_session_dates[-1]
        days_inactive = (today - last_session).days
        if days_inactive > 10:
            suggestions.append({
                "type": "inactivity",
                "muscle_group": None,
                "days_since": days_inactive,
                "suggestion": f"Your last session was {days_inactive} days ago. Time to get back in the gym.",
            })

    return suggestions
