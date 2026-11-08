def rate_productivity(focus_minutes, goal_minutes):
    """Rate completed focus time against a daily study goal."""
    if focus_minutes < 0:
        raise ValueError("Focus minutes cannot be negative")
    if goal_minutes <= 0:
        raise ValueError("Goal minutes must be greater than zero")

    score = min(100, round(focus_minutes * 100 / goal_minutes))
    if score >= 100:
        rating = "Excellent"
        message = "You reached your study goal."
    elif score >= 75:
        rating = "Great progress"
        message = "You are close to your study goal."
    elif score >= 40:
        rating = "Building momentum"
        message = "Keep going with another focused session."
    elif score > 0:
        rating = "Getting started"
        message = "Every completed focus session counts."
    else:
        rating = "Ready when you are"
        message = "Complete a focus session to start your rating."

    return {
        "score": score,
        "rating": rating,
        "message": message,
        "goal_reached": focus_minutes >= goal_minutes,
    }
