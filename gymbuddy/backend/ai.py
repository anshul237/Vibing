import anthropic
import json
import os
from backend.db.database import get_connection

MOCK_MODE = not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") == "your_api_key_here"

SAMPLE_WORKOUT = {
    "workout_title": "Push Day Starter",
    "focus": "Upper Body",
    "estimated_duration_mins": 40,
    "exercises": [
        {
            "name": "Dumbbell Row",
            "muscle_group": "Back",
            "sets": 3,
            "reps": "10",
            "notes": "Pull your elbow back like you're starting a lawnmower. Keep your back flat.",
            "weight_suggestion": "Start with 8–10 kg. Should feel challenging by rep 8 but not break form.",
            "setup_note": "Place one knee and hand on a bench for support. Keep your back parallel to the floor."
        },
        {
            "name": "Dumbbell Shoulder Press",
            "muscle_group": "Shoulders",
            "sets": 3,
            "reps": "10",
            "notes": "Press straight up, don't flare your elbows too wide.",
            "weight_suggestion": "Start with 6–8 kg. Shoulders fatigue faster than chest — go lighter than you think.",
            "setup_note": "Sit on a bench with back support. Dumbbells start at ear height, palms facing forward."
        },
        {
            "name": "Push-up",
            "muscle_group": "Chest",
            "sets": 3,
            "reps": "10",
            "notes": "Keep your core tight and lower slowly — 2 seconds down, push up fast.",
            "weight_suggestion": "Bodyweight only. If too easy, elevate your feet on a bench.",
            "setup_note": "Hands slightly wider than shoulder-width. Body forms a straight line from head to heels."
        },
        {
            "name": "Tricep Dips",
            "muscle_group": "Triceps",
            "sets": 3,
            "reps": "8-12",
            "notes": "Keep elbows pointing back, not flaring out.",
            "weight_suggestion": "Bodyweight only to start. Add a weight plate on your lap once you can do 15 reps easily.",
            "setup_note": "Use a flat bench. Hands grip the edge, fingers forward. Lower until elbows hit 90 degrees."
        },
        {
            "name": "Plank",
            "muscle_group": "Core",
            "sets": 3,
            "reps": "30 seconds",
            "notes": "Squeeze your glutes and brace your abs. Don't let your hips sag.",
            "weight_suggestion": "Bodyweight only.",
            "setup_note": "Forearms on the floor, elbows under shoulders. Look at the floor, not forward."
        }
    ],
    "coach_note": "Good choice showing up. These are all exercises you can own quickly — focus on form over weight today and the strength will come."
}

ALTERNATIVES = {
    "Chest": ["Push-up", "Dumbbell Bench Press", "Chest Dip", "Diamond Push-up", "Incline Push-up"],
    "Back": ["Dumbbell Row", "Resistance Band Row", "Superman Hold", "Lat Pulldown", "Seated Cable Row"],
    "Shoulders": ["Dumbbell Shoulder Press", "Lateral Raise", "Arnold Press", "Pike Push-up", "Front Raise"],
    "Triceps": ["Tricep Dips", "Overhead Tricep Extension", "Tricep Kickback", "Close-grip Push-up", "Cable Pushdown"],
    "Biceps": ["Dumbbell Curl", "Hammer Curl", "Resistance Band Curl", "Concentration Curl", "Chin-up"],
    "Quads": ["Squat", "Goblet Squat", "Leg Press", "Lunge", "Step-up", "Wall Sit"],
    "Hamstrings": ["Romanian Deadlift", "Leg Curl", "Nordic Curl", "Good Morning", "Glute Bridge"],
    "Glutes": ["Hip Thrust", "Glute Bridge", "Bulgarian Split Squat", "Sumo Squat", "Donkey Kick"],
    "Calves": ["Standing Calf Raise", "Seated Calf Raise", "Single-leg Calf Raise", "Jump Rope"],
    "Core": ["Plank", "Dead Bug", "Hollow Hold", "Ab Wheel Rollout", "Bicycle Crunch", "Leg Raise"],
    "Legs": ["Squat", "Lunge", "Romanian Deadlift", "Leg Press", "Step-up"],
}

if not MOCK_MODE:
    client = anthropic.Anthropic()


def get_recent_sessions(limit=5):
    conn = get_connection()
    cursor = conn.cursor()

    sessions = cursor.execute("""
        SELECT s.id, s.date, s.duration_mins, s.equipment, s.energy_level
        FROM sessions s
        ORDER BY s.date DESC
        LIMIT ?
    """, (limit,)).fetchall()

    history = []
    for s in sessions:
        exercises = cursor.execute("""
            SELECT exercise_name, muscle_group, sets, reps
            FROM session_exercises
            WHERE session_id = ?
        """, (s["id"],)).fetchall()

        history.append({
            "date": s["date"],
            "duration_mins": s["duration_mins"],
            "equipment": s["equipment"],
            "energy_level": s["energy_level"],
            "exercises": [dict(e) for e in exercises]
        })

    conn.close()
    return history


def get_fitness_level():
    conn = get_connection()
    level = conn.execute("SELECT fitness_level FROM user_profile WHERE id = 1").fetchone()
    conn.close()
    return level["fitness_level"] if level else "beginner"


def generate_workout(duration_mins: int, equipment: str, energy_level: str):
    if MOCK_MODE:
        return SAMPLE_WORKOUT

    history = get_recent_sessions()
    fitness_level = get_fitness_level()

    history_text = json.dumps(history, indent=2) if history else "No previous sessions yet."

    prompt = f"""You are a personal trainer generating a workout for someone.

User profile:
- Fitness level: {fitness_level}
- Today's available time: {duration_mins} minutes
- Available equipment: {equipment}
- Energy level today: {energy_level}

Recent workout history (last 5 sessions):
{history_text}

Rules:
1. Match complexity to fitness level — beginners get simple, familiar movements
2. Avoid muscle groups heavily worked in the last 1-2 sessions
3. If fitness level is beginner, introduce at most 1 unfamiliar exercise per session
4. Keep it achievable given the energy level (tired = lower volume/intensity)
5. Only use exercises possible with the available equipment
6. Do not repeat the exact same workout as any recent session
7. Order exercises correctly: large compound movements first, isolation exercises after, core last
8. Include realistic beginner weight suggestions and machine/equipment setup instructions per exercise

Respond ONLY with a JSON object in this exact format:
{{
  "workout_title": "string",
  "focus": "string (e.g. Upper Body, Full Body, Legs)",
  "estimated_duration_mins": number,
  "exercises": [
    {{
      "name": "string",
      "muscle_group": "string",
      "sets": number,
      "reps": "string (e.g. '10' or '8-12' or '30 seconds')",
      "notes": "string (brief form tip)",
      "weight_suggestion": "string (e.g. 'Start with 8-10 kg. Should feel challenging by rep 8.')",
      "setup_note": "string (how to set up the equipment or position for this exercise)"
    }}
  ],
  "coach_note": "string (one motivational or practical tip for today's session)"
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]

    return json.loads(response_text)
