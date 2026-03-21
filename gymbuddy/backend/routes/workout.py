from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from backend.ai import generate_workout, ALTERNATIVES, MOCK_MODE
import anthropic
import json
import os
from backend.db.database import get_connection

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")


class WorkoutRequest(BaseModel):
    duration_mins: int
    equipment: str
    energy_level: str


class SwapRequest(BaseModel):
    current_exercise: str
    muscle_group: str
    equipment: str
    fitness_level: str = "beginner"


class SessionLog(BaseModel):
    duration_mins: int
    equipment: str
    energy_level: str
    exercises: list[dict]


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/api/workout")
def get_workout(req: WorkoutRequest):
    workout = generate_workout(req.duration_mins, req.equipment, req.energy_level)
    return workout


@router.post("/api/workout/swap")
def swap_exercise(req: SwapRequest):
    if MOCK_MODE:
        options = ALTERNATIVES.get(req.muscle_group, [])
        alternatives = [e for e in options if e != req.current_exercise]
        if not alternatives:
            return {"error": "No alternatives found"}
        import random
        name = random.choice(alternatives)
        return {
            "name": name,
            "muscle_group": req.muscle_group,
            "sets": 3,
            "reps": "10",
            "notes": f"Alternative to {req.current_exercise} targeting the same muscle group.",
            "weight_suggestion": "Start light and adjust based on how the first set feels.",
            "setup_note": "Ask a gym staff member if you're unsure how to set up this exercise."
        }

    client = anthropic.Anthropic()
    prompt = f"""Suggest one alternative exercise to replace "{req.current_exercise}".
Requirements:
- Same muscle group: {req.muscle_group}
- Available equipment: {req.equipment}
- Fitness level: {req.fitness_level}
- Must be different from: {req.current_exercise}

Respond ONLY with a JSON object:
{{
  "name": "string",
  "muscle_group": "{req.muscle_group}",
  "sets": number,
  "reps": "string",
  "notes": "string (brief form tip)",
  "weight_suggestion": "string",
  "setup_note": "string"
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    response_text = message.content[0].text.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
    return json.loads(response_text)


@router.post("/api/session")
def log_session(log: SessionLog):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO sessions (user_id, duration_mins, equipment, energy_level)
        VALUES (1, ?, ?, ?)
    """, (log.duration_mins, log.equipment, log.energy_level))

    session_id = cursor.lastrowid

    for ex in log.exercises:
        cursor.execute("""
            INSERT INTO session_exercises (session_id, user_id, exercise_name, muscle_group, sets, reps, notes)
            VALUES (?, 1, ?, ?, ?, ?, ?)
        """, (session_id, ex.get("name"), ex.get("muscle_group"),
              ex.get("sets"), ex.get("reps"), ex.get("notes", "")))

    conn.commit()
    conn.close()
    return {"status": "logged", "session_id": session_id}


@router.get("/api/suggestion")
def get_suggestion():
    conn = get_connection()

    last_session = conn.execute("""
        SELECT s.id, s.date, s.duration_mins, s.equipment, s.energy_level
        FROM sessions s ORDER BY s.date DESC LIMIT 1
    """).fetchone()

    if not last_session:
        return {
            "has_suggestion": False,
            "reason": "No sessions yet"
        }

    last_exercises = conn.execute("""
        SELECT DISTINCT muscle_group FROM session_exercises
        WHERE session_id = ?
    """, (last_session["id"],)).fetchall()
    conn.close()

    last_muscle_groups = [e["muscle_group"].lower() for e in last_exercises if e["muscle_group"]]

    upper = {"chest", "shoulders", "triceps", "biceps", "back", "upper back", "lats"}
    lower = {"quads", "hamstrings", "glutes", "calves", "legs"}

    last_was_upper = any(m in upper for m in last_muscle_groups)
    last_was_lower = any(m in lower for m in last_muscle_groups)

    if last_was_upper and not last_was_lower:
        suggested_focus = "Lower Body"
        reason = "You hit upper body last session — time to balance it out with legs."
    elif last_was_lower and not last_was_upper:
        suggested_focus = "Upper Body"
        reason = "Legs done last session — upper body today."
    else:
        suggested_focus = "Full Body"
        reason = "Mix it up with a full body session today."

    return {
        "has_suggestion": True,
        "suggested_focus": suggested_focus,
        "suggested_duration": last_session["duration_mins"],
        "suggested_equipment": last_session["equipment"],
        "reason": reason,
        "last_session_date": last_session["date"]
    }


@router.get("/api/history")
def get_history():
    conn = get_connection()
    sessions = conn.execute("""
        SELECT s.id, s.date, s.duration_mins, s.equipment, s.energy_level
        FROM sessions s ORDER BY s.date DESC LIMIT 10
    """).fetchall()

    result = []
    for s in sessions:
        exercises = conn.execute("""
            SELECT exercise_name, muscle_group, sets, reps
            FROM session_exercises WHERE session_id = ?
        """, (s["id"],)).fetchall()
        result.append({**dict(s), "exercises": [dict(e) for e in exercises]})

    conn.close()
    return result
