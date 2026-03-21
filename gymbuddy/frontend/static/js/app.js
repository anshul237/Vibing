const state = {
    duration: null,
    equipment: null,
    energy: null,
    currentWorkout: null
};

// --- Load suggestion on open ---

async function loadSuggestion() {
    try {
        const res = await fetch("/api/suggestion");
        const data = await res.json();

        if (data.has_suggestion) {
            document.getElementById("suggestion-focus").textContent = data.suggested_focus;
            document.getElementById("suggestion-reason").textContent = data.reason;
            document.getElementById("suggestion-duration").textContent = `${data.suggested_duration} min`;
            document.getElementById("suggestion-equipment").textContent = data.suggested_equipment;

            // Pre-fill state with suggestion values
            state.duration = String(data.suggested_duration);
            state.equipment = data.suggested_equipment;
            state.energy = "moderate"; // default energy, user can adjust

            show("suggestion");
        } else {
            show("setup-form");
        }
    } catch (err) {
        show("setup-form");
    }
}

document.getElementById("suggestion-confirm-btn").addEventListener("click", () => {
    // Energy not set from suggestion — ask only for energy before generating
    state.energy = "moderate";
    fetchWorkout();
});

document.getElementById("suggestion-adjust-btn").addEventListener("click", () => {
    // Pre-select the suggested values in the form
    preselectOption("duration-options", state.duration);
    preselectOption("equipment-options", state.equipment);
    checkReady();
    show("setup-form");
});

function preselectOption(containerId, value) {
    document.getElementById(containerId).querySelectorAll(".option-btn").forEach(btn => {
        btn.classList.toggle("selected", btn.dataset.value === value);
    });
}

// --- Selection logic ---

function setupOptions(containerId, stateKey) {
    document.getElementById(containerId).querySelectorAll(".option-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.getElementById(containerId).querySelectorAll(".option-btn")
                .forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
            state[stateKey] = btn.dataset.value;
            checkReady();
        });
    });
}

function checkReady() {
    const ready = state.duration && state.equipment && state.energy;
    document.getElementById("generate-btn").disabled = !ready;
}

setupOptions("duration-options", "duration");
setupOptions("equipment-options", "equipment");
setupOptions("energy-options", "energy");

// --- Generate workout ---

document.getElementById("generate-btn").addEventListener("click", fetchWorkout);
document.getElementById("regenerate-btn").addEventListener("click", fetchWorkout);

async function fetchWorkout() {
    show("loading");

    try {
        const res = await fetch("/api/workout", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                duration_mins: parseInt(state.duration),
                equipment: state.equipment,
                energy_level: state.energy
            })
        });

        const workout = await res.json();
        state.currentWorkout = workout;
        renderWorkout(workout);
        show("workout-display");
    } catch (err) {
        alert("Something went wrong generating your workout. Try again.");
        show("setup-form");
    }
}

function renderWorkout(workout) {
    document.getElementById("workout-title").textContent = workout.workout_title;
    document.getElementById("workout-focus").textContent = workout.focus;
    document.getElementById("workout-duration").textContent = `~${workout.estimated_duration_mins} min`;
    document.getElementById("coach-note").textContent = workout.coach_note;

    renderWorkoutGraphic(workout.focus);
    renderExercises(workout.exercises);
}

function renderWorkoutGraphic(focus) {
    const el = document.getElementById("workout-graphic");
    const f = focus.toLowerCase();
    let cls, svg, label, desc;

    if (f.includes("upper")) {
        cls = "upper";
        label = "Upper Body Day";
        desc = "Chest, back, shoulders & arms";
        svg = `<svg class="graphic-svg" width="56" height="80" viewBox="0 0 56 80" fill="none">
            <ellipse cx="28" cy="10" rx="9" ry="9" fill="#1e4060" stroke="#4aa8e0" stroke-width="1.5"/>
            <rect x="16" y="22" width="24" height="22" rx="5" fill="#4aa8e0" opacity="0.8"/>
            <rect x="4" y="22" width="11" height="18" rx="4" fill="#4aa8e0" opacity="0.6"/>
            <rect x="41" y="22" width="11" height="18" rx="4" fill="#4aa8e0" opacity="0.6"/>
            <rect x="20" y="44" width="16" height="20" rx="4" fill="#1e4060" stroke="#2a5070" stroke-width="1"/>
            <rect x="20" y="64" width="7" height="14" rx="3" fill="#1e4060" stroke="#2a5070" stroke-width="1"/>
            <rect x="29" y="64" width="7" height="14" rx="3" fill="#1e4060" stroke="#2a5070" stroke-width="1"/>
        </svg>`;
    } else if (f.includes("lower") || f.includes("leg")) {
        cls = "lower";
        label = "Lower Body Day";
        desc = "Quads, hamstrings, glutes & calves";
        svg = `<svg class="graphic-svg" width="56" height="80" viewBox="0 0 56 80" fill="none">
            <ellipse cx="28" cy="10" rx="9" ry="9" fill="#3b1a2e" stroke="#a04080" stroke-width="1.5"/>
            <rect x="16" y="22" width="24" height="22" rx="5" fill="#3b1a2e" stroke="#a04080" stroke-width="1"/>
            <rect x="4" y="22" width="11" height="18" rx="4" fill="#3b1a2e" stroke="#a04080" stroke-width="1"/>
            <rect x="41" y="22" width="11" height="18" rx="4" fill="#3b1a2e" stroke="#a04080" stroke-width="1"/>
            <rect x="20" y="44" width="16" height="20" rx="4" fill="#a04080" opacity="0.8"/>
            <rect x="20" y="64" width="7" height="14" rx="3" fill="#a04080" opacity="0.7"/>
            <rect x="29" y="64" width="7" height="14" rx="3" fill="#a04080" opacity="0.7"/>
        </svg>`;
    } else {
        cls = "full";
        label = "Full Body Day";
        desc = "Every major muscle group";
        svg = `<svg class="graphic-svg" width="56" height="80" viewBox="0 0 56 80" fill="none">
            <ellipse cx="28" cy="10" rx="9" ry="9" fill="#1a3b2e" stroke="#40916c" stroke-width="1.5"/>
            <rect x="16" y="22" width="24" height="22" rx="5" fill="#40916c" opacity="0.8"/>
            <rect x="4" y="22" width="11" height="18" rx="4" fill="#40916c" opacity="0.6"/>
            <rect x="41" y="22" width="11" height="18" rx="4" fill="#40916c" opacity="0.6"/>
            <rect x="20" y="44" width="16" height="20" rx="4" fill="#40916c" opacity="0.7"/>
            <rect x="20" y="64" width="7" height="14" rx="3" fill="#40916c" opacity="0.6"/>
            <rect x="29" y="64" width="7" height="14" rx="3" fill="#40916c" opacity="0.6"/>
        </svg>`;
    }

    el.innerHTML = `
        <div class="workout-graphic ${cls}">
            ${svg}
            <div class="graphic-text">
                <h3>${label}</h3>
                <p>${desc}</p>
            </div>
        </div>`;
}

function renderExercises(exercises) {
    const list = document.getElementById("exercises-list");
    list.innerHTML = "";

    exercises.forEach((ex, i) => {
        const card = document.createElement("div");
        card.className = "exercise-card";
        card.dataset.index = i;
        card.innerHTML = `
            <div class="exercise-header">
                <span class="exercise-number">${i + 1}</span>
                <div class="exercise-info">
                    <div class="exercise-name">${ex.name}</div>
                    <div class="exercise-muscle">${ex.muscle_group}</div>
                </div>
                <span class="exercise-sets">${ex.sets} × ${ex.reps}</span>
            </div>
            <div class="exercise-hint">Tap for tips & demo</div>
            <button class="swap-btn" data-index="${i}">↻ Swap</button>
        `;

        card.addEventListener("click", (e) => {
            if (e.target.classList.contains("swap-btn")) return;
            openExerciseModal(ex);
        });

        card.querySelector(".swap-btn").addEventListener("click", (e) => {
            e.stopPropagation();
            swapExercise(i, ex);
        });

        list.appendChild(card);
    });
}

function openExerciseModal(ex) {
    document.getElementById("modal-exercise-name").textContent = ex.name;
    document.getElementById("modal-muscle").textContent = ex.muscle_group;
    document.getElementById("modal-notes").textContent = ex.notes;
    document.getElementById("modal-weight").textContent = ex.weight_suggestion || "Adjust based on how the first set feels.";
    document.getElementById("modal-setup").textContent = ex.setup_note || "Standard setup for this exercise.";

    const query = encodeURIComponent(`${ex.name} proper form short tutorial`);
    document.getElementById("modal-video-link").href = `https://www.youtube.com/results?search_query=${query}&sp=EgIQAQ%3D%3D`;

    document.getElementById("exercise-modal").classList.remove("hidden");
}

document.getElementById("modal-close").addEventListener("click", () => {
    document.getElementById("exercise-modal").classList.add("hidden");
});

document.getElementById("exercise-modal").addEventListener("click", (e) => {
    if (e.target === document.getElementById("exercise-modal")) {
        document.getElementById("exercise-modal").classList.add("hidden");
    }
});

async function swapExercise(index, ex) {
    const card = document.querySelector(`.exercise-card[data-index="${index}"]`);
    const swapBtn = card.querySelector(".swap-btn");
    swapBtn.textContent = "...";
    swapBtn.disabled = true;

    try {
        const res = await fetch("/api/workout/swap", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                current_exercise: ex.name,
                muscle_group: ex.muscle_group,
                equipment: state.equipment,
                fitness_level: "beginner"
            })
        });

        const newEx = await res.json();
        if (newEx.error) { swapBtn.textContent = "↻ Swap"; swapBtn.disabled = false; return; }

        state.currentWorkout.exercises[index] = newEx;
        renderExercises(state.currentWorkout.exercises);
    } catch (err) {
        swapBtn.textContent = "↻ Swap";
        swapBtn.disabled = false;
    }
}

// --- Log session ---

document.getElementById("done-btn").addEventListener("click", async () => {
    if (!state.currentWorkout) return;

    try {
        await fetch("/api/session", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                duration_mins: parseInt(state.duration),
                equipment: state.equipment,
                energy_level: state.energy,
                exercises: state.currentWorkout.exercises
            })
        });

        show("logged-confirmation");
    } catch (err) {
        alert("Could not log session. Try again.");
    }
});

// --- New session ---

document.getElementById("new-session-btn").addEventListener("click", () => {
    state.duration = null;
    state.equipment = null;
    state.energy = null;
    state.currentWorkout = null;

    document.querySelectorAll(".option-btn").forEach(b => b.classList.remove("selected"));
    document.getElementById("generate-btn").disabled = true;
    loadSuggestion();
});

// --- Utility ---

function show(sectionId) {
    ["suggestion", "setup-form", "loading", "workout-display", "logged-confirmation"].forEach(id => {
        document.getElementById(id).classList.add("hidden");
    });
    document.getElementById(sectionId).classList.remove("hidden");
}

// Boot
loadSuggestion();
