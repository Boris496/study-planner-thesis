import psycopg2
import streamlit as st
from datetime import datetime

TASK_TYPE_TO_INTENSITY = {
    "Study / Learning": "High",
    "Reading": "Medium",
    "Practice": "High",
    "Writing": "High",
    "Review": "Low",
    "Administrative": "Low"
}

VALID_TASK_TYPES = set(TASK_TYPE_TO_INTENSITY.keys())

MIN_RATIO = 0.75
MAX_RATIO = 1.5
SMOOTHING_ALPHA = 0.2
DEFAULT_PLANNING_FACTOR = 1.0


def _normalize_task_type(task_type: str) -> str:
    if task_type in VALID_TASK_TYPES:
        return task_type

    mapping = {
        "Study": "Study / Learning",
        "Learning": "Study / Learning",
        "Learn": "Study / Learning",
        "Read": "Reading",
        "Practice / Exercises": "Practice",
        "Exercises": "Practice",
        "Write": "Writing",
        "Revision": "Review",
        "Admin": "Administrative"
    }

    normalized = mapping.get(task_type, task_type)
    if normalized in VALID_TASK_TYPES:
        return normalized

    return "Study / Learning"


def _derive_task_intensity(task_type: str) -> str:
    normalized_type = _normalize_task_type(task_type)
    return TASK_TYPE_TO_INTENSITY.get(normalized_type, "Medium")


def _clamp_ratio(ratio: float) -> float:
    return max(MIN_RATIO, min(MAX_RATIO, ratio))


# -----------------------------
# Database connection
# -----------------------------
def get_connection():
    return psycopg2.connect(st.secrets["database_url"])

def enable_rls():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        ALTER TABLE students ENABLE ROW LEVEL SECURITY;
        ALTER TABLE student_subjects ENABLE ROW LEVEL SECURITY;
        ALTER TABLE admins ENABLE ROW LEVEL SECURITY;
        ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
        ALTER TABLE task_history ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ai_feedback_reflections ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ai_learning_preferences ENABLE ROW LEVEL SECURITY;
        ALTER TABLE student_task_type_learning ENABLE ROW LEVEL SECURITY;
        ALTER TABLE day_preferences ENABLE ROW LEVEL SECURITY;
        ALTER TABLE activity_slots ENABLE ROW LEVEL SECURITY;
        ALTER TABLE study_plan ENABLE ROW LEVEL SECURITY;
        ALTER TABLE planner_personalization_log ENABLE ROW LEVEL SECURITY;
    """)

    conn.commit()
    cursor.close()
    conn.close()

# -----------------------------
# Initialize database
# -----------------------------
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # -----------------------------
    # Students
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            has_seen_onboarding BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)

    cursor.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE
    """)

    cursor.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS has_seen_onboarding BOOLEAN NOT NULL DEFAULT FALSE
    """)

    # -----------------------------
    # Student subjects
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_subjects (
            student_id TEXT NOT NULL,
            subject_name TEXT NOT NULL,
            PRIMARY KEY (student_id, subject_name),
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    """)

    # -----------------------------
    # Admins
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # -----------------------------
    # Tasks
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id SERIAL PRIMARY KEY,
            student_id TEXT NOT NULL,
            task_name TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT 'General',
            task_type TEXT NOT NULL,
            importance_level TEXT NOT NULL,
            task_intensity TEXT NOT NULL DEFAULT 'Medium',
            deadline DATE NOT NULL,
            estimated_hours DOUBLE PRECISION NOT NULL,
            adjusted_hours DOUBLE PRECISION NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned',
            is_spread_learning BOOLEAN NOT NULL DEFAULT FALSE,
            preferred_study_days INTEGER,
            min_session_hours DOUBLE PRECISION,
            max_session_hours DOUBLE PRECISION,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    """)

    cursor.execute("""
        ALTER TABLE tasks
        ADD COLUMN IF NOT EXISTS task_intensity TEXT NOT NULL DEFAULT 'Medium'
    """)

    cursor.execute("""
        ALTER TABLE tasks
        ADD COLUMN IF NOT EXISTS subject TEXT NOT NULL DEFAULT 'General'
    """)

    cursor.execute("""
        ALTER TABLE tasks
        ADD COLUMN IF NOT EXISTS is_spread_learning BOOLEAN NOT NULL DEFAULT FALSE
    """)

    cursor.execute("""
        ALTER TABLE tasks
        ADD COLUMN IF NOT EXISTS preferred_study_days INTEGER
    """)

    cursor.execute("""
        ALTER TABLE tasks
        ADD COLUMN IF NOT EXISTS min_session_hours DOUBLE PRECISION
    """)

    cursor.execute("""
        ALTER TABLE tasks
        ADD COLUMN IF NOT EXISTS max_session_hours DOUBLE PRECISION
    """)

    # -----------------------------
    # Task history
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            history_id SERIAL PRIMARY KEY,
            task_id INTEGER NOT NULL,
            student_id TEXT NOT NULL,
            task_name TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT 'General',
            task_type TEXT NOT NULL,
            importance_level TEXT NOT NULL,
            estimated_hours DOUBLE PRECISION NOT NULL,
            adjusted_hours DOUBLE PRECISION NOT NULL,
            actual_hours DOUBLE PRECISION NOT NULL,
            completed BOOLEAN NOT NULL,
            remaining_hours DOUBLE PRECISION NOT NULL DEFAULT 0,
            perceived_difficulty INTEGER,
            mental_effort INTEGER,
            confidence_level INTEGER,
            focus_level INTEGER,
            logged_at TIMESTAMP NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        )
    """)

    cursor.execute("""
        ALTER TABLE task_history
        ADD COLUMN IF NOT EXISTS subject TEXT NOT NULL DEFAULT 'General'
    """)

    cursor.execute("""
        ALTER TABLE task_history
        ADD COLUMN IF NOT EXISTS perceived_difficulty INTEGER
    """)

    cursor.execute("""
        ALTER TABLE task_history
        ADD COLUMN IF NOT EXISTS mental_effort INTEGER
    """)

    cursor.execute("""
        ALTER TABLE task_history
        ADD COLUMN IF NOT EXISTS confidence_level INTEGER
    """)

    cursor.execute("""
        ALTER TABLE task_history
        ADD COLUMN IF NOT EXISTS focus_level INTEGER
    """)

    # -----------------------------
    # AI feedback reflections
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_feedback_reflections (
            reflection_id SERIAL PRIMARY KEY,
            student_id TEXT NOT NULL,
            task_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        )
    """)

    # -----------------------------
    # AI accepted learning preferences
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_learning_preferences (
            preference_id SERIAL PRIMARY KEY,
            student_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            subject TEXT NOT NULL,
            preference_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'accepted',
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    """)

    cursor.execute("""
        ALTER TABLE ai_learning_preferences
        ADD COLUMN IF NOT EXISTS add_time_buffer_percent INTEGER DEFAULT 0
    """)

    cursor.execute("""
        ALTER TABLE ai_learning_preferences
        ADD COLUMN IF NOT EXISTS preferred_energy TEXT
    """)

    cursor.execute("""
        ALTER TABLE ai_learning_preferences
        ADD COLUMN IF NOT EXISTS max_session_hours DOUBLE PRECISION
    """)

    cursor.execute("""
        ALTER TABLE ai_learning_preferences
        ADD COLUMN IF NOT EXISTS avoid_after_high_difficulty_task BOOLEAN DEFAULT FALSE
    """)


    # -----------------------------
    # Student learning profiles
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_task_type_learning (
            student_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT 'General',
            planning_factor DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            feedback_count INTEGER NOT NULL DEFAULT 0,
            avg_difficulty DOUBLE PRECISION NOT NULL DEFAULT 0,
            avg_mental_effort DOUBLE PRECISION NOT NULL DEFAULT 0,
            avg_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
            avg_focus DOUBLE PRECISION NOT NULL DEFAULT 0,
            updated_at TIMESTAMP NOT NULL,
            PRIMARY KEY (student_id, task_type, subject),
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    """)

    cursor.execute("""
        ALTER TABLE student_task_type_learning
        ADD COLUMN IF NOT EXISTS subject TEXT NOT NULL DEFAULT 'General'
    """)

    cursor.execute("""
        ALTER TABLE student_task_type_learning
        ADD COLUMN IF NOT EXISTS avg_difficulty DOUBLE PRECISION NOT NULL DEFAULT 0
    """)

    cursor.execute("""
        ALTER TABLE student_task_type_learning
        ADD COLUMN IF NOT EXISTS avg_mental_effort DOUBLE PRECISION NOT NULL DEFAULT 0
    """)

    cursor.execute("""
        ALTER TABLE student_task_type_learning
        ADD COLUMN IF NOT EXISTS avg_confidence DOUBLE PRECISION NOT NULL DEFAULT 0
    """)

    cursor.execute("""
        ALTER TABLE student_task_type_learning
        ADD COLUMN IF NOT EXISTS avg_focus DOUBLE PRECISION NOT NULL DEFAULT 0
    """)

    # -----------------------------
    # Day preferences
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS day_preferences (
            student_id TEXT NOT NULL,
            study_date DATE NOT NULL,
            wake_time TIME NOT NULL,
            sleep_time TIME NOT NULL,
            PRIMARY KEY (student_id, study_date),
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    """)

    # -----------------------------
    # Activity slots
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_slots (
            slot_id SERIAL PRIMARY KEY,
            student_id TEXT NOT NULL,
            study_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            reason TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    """)

    # -----------------------------
    # Study plan
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_plan (
            plan_id SERIAL PRIMARY KEY,
            student_id TEXT NOT NULL,
            task_id INTEGER,
            study_date DATE NOT NULL,
            start_time TIME,
            end_time TIME,
            planned_hours DOUBLE PRECISION NOT NULL,
            energy_level TEXT,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        )
    """)

    cursor.execute("""
        ALTER TABLE study_plan
        ADD COLUMN IF NOT EXISTS start_time TIME
    """)

    cursor.execute("""
        ALTER TABLE study_plan
        ADD COLUMN IF NOT EXISTS end_time TIME
    """)

    cursor.execute("""
        ALTER TABLE study_plan
        ADD COLUMN IF NOT EXISTS energy_level TEXT
    """)

    # -----------------------------
    # Planner personalization log
    # -----------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS planner_personalization_log (
            log_id SERIAL PRIMARY KEY,
            student_id TEXT NOT NULL,
            task_id INTEGER NOT NULL,
            task_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            task_type TEXT NOT NULL,
            add_time_buffer_percent INTEGER NOT NULL DEFAULT 0,
            preferred_energy TEXT,
            max_session_hours DOUBLE PRECISION,
            avoid_after_high_difficulty_task BOOLEAN NOT NULL DEFAULT FALSE,
            reason TEXT,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

    enable_rls()
    create_default_admin()


def create_default_admin():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT admin_id
        FROM admins
        WHERE username = %s
    """, ("admin",))

    existing = cursor.fetchone()

    if not existing:
        cursor.execute("""
                        INSERT INTO admins (username, password)
            VALUES (%s, %s)
        """, (st.secrets["admin_username"], st.secrets["admin_password"]))

    conn.commit()
    cursor.close()
    conn.close()


# -----------------------------
# Admin functions
# -----------------------------
def create_admin(username: str, password: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO admins (username, password)
        VALUES (%s, %s)
    """, (username, password))

    conn.commit()
    cursor.close()
    conn.close()


def get_admin(username: str, password: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT admin_id, username
        FROM admins
        WHERE username = %s AND password = %s
    """, (username, password))

    admin = cursor.fetchone()
    cursor.close()
    conn.close()
    return admin


# -----------------------------
# Student functions
# -----------------------------
def get_student(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT student_id, name, is_active, has_seen_onboarding
        FROM students
        WHERE student_id = %s
    """, (student_id,))

    student = cursor.fetchone()
    cursor.close()
    conn.close()
    return student

def mark_onboarding_seen(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE students
        SET has_seen_onboarding = TRUE
        WHERE student_id = %s
    """, (student_id,))

    conn.commit()
    cursor.close()
    conn.close()


def create_student(student_id: str, name: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO students (student_id, name, is_active)
        VALUES (%s, %s, TRUE)
    """, (student_id, name))

    conn.commit()
    cursor.close()
    conn.close()


def get_all_students():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT student_id, name, is_active
        FROM students
        ORDER BY student_id ASC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def deactivate_student(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE students
        SET is_active = FALSE
        WHERE student_id = %s
    """, (student_id,))

    conn.commit()
    cursor.close()
    conn.close()


def activate_student(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE students
        SET is_active = TRUE
        WHERE student_id = %s
    """, (student_id,))

    conn.commit()
    cursor.close()
    conn.close()


def delete_student_account(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM task_history
        WHERE student_id = %s
    """, (student_id,))

    cursor.execute("""
        DELETE FROM study_plan
        WHERE student_id = %s
    """, (student_id,))

    cursor.execute("""
        DELETE FROM activity_slots
        WHERE student_id = %s
    """, (student_id,))

    cursor.execute("""
        DELETE FROM day_preferences
        WHERE student_id = %s
    """, (student_id,))

    cursor.execute("""
        DELETE FROM student_task_type_learning
        WHERE student_id = %s
    """, (student_id,))

    cursor.execute("""
        DELETE FROM student_subjects
        WHERE student_id = %s
    """, (student_id,))

    cursor.execute("""
        DELETE FROM ai_feedback_reflections
        WHERE student_id = %s
    """, (student_id,))

    cursor.execute("""
        DELETE FROM ai_learning_preferences
        WHERE student_id = %s
    """, (student_id,))

    cursor.execute("""
        DELETE FROM planner_personalization_log
        WHERE student_id = %s
    """, (student_id,))

    cursor.execute("""
        DELETE FROM tasks
        WHERE student_id = %s
    """, (student_id,))

    cursor.execute("""
        DELETE FROM students
        WHERE student_id = %s
    """, (student_id,))

    conn.commit()
    cursor.close()
    conn.close()


# -----------------------------
# Subject functions
# -----------------------------
def add_subject(student_id: str, subject_name: str):
    normalized_subject = subject_name.strip().title()

    if not normalized_subject:
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO student_subjects (student_id, subject_name)
        VALUES (%s, %s)
        ON CONFLICT (student_id, subject_name) DO NOTHING
    """, (student_id, normalized_subject))

    conn.commit()
    cursor.close()
    conn.close()


def get_subjects_for_student(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT subject_name
        FROM student_subjects
        WHERE student_id = %s
        ORDER BY subject_name ASC
    """, (student_id,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [row[0] for row in rows]


def delete_subject(student_id: str, subject_name: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM student_subjects
        WHERE student_id = %s
          AND subject_name = %s
    """, (student_id, subject_name))

    conn.commit()
    cursor.close()
    conn.close()


# -----------------------------
# Task functions
# -----------------------------
def add_task(
    student_id: str,
    task_name: str,
    subject: str,
    task_type: str,
    importance_level: str,
    deadline: str,
    estimated_hours: float,
    is_spread_learning: bool = False,
    preferred_study_days: int | None = None,
    min_session_hours: float | None = None,
    max_session_hours: float | None = None
):
    conn = get_connection()
    cursor = conn.cursor()

    normalized_task_type = _normalize_task_type(task_type)
    derived_task_intensity = _derive_task_intensity(normalized_task_type)
    normalized_subject = subject.strip() if subject and subject.strip() else "General"

    if normalized_task_type != "Study / Learning":
        is_spread_learning = False
        preferred_study_days = None
        min_session_hours = None
        max_session_hours = None

    adjusted_hours = round(float(estimated_hours), 2)

    cursor.execute("""
        INSERT INTO tasks (
            student_id,
            task_name,
            subject,
            task_type,
            importance_level,
            task_intensity,
            deadline,
            estimated_hours,
            adjusted_hours,
            status,
            is_spread_learning,
            preferred_study_days,
            min_session_hours,
            max_session_hours
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'planned', %s, %s, %s, %s)
    """, (
        student_id,
        task_name,
        normalized_subject,
        normalized_task_type,
        importance_level,
        derived_task_intensity,
        deadline,
        estimated_hours,
        adjusted_hours,
        is_spread_learning,
        preferred_study_days,
        min_session_hours,
        max_session_hours
    ))

    conn.commit()
    cursor.close()
    conn.close()

def update_task(
    task_id: int,
    task_name: str,
    subject: str,
    task_type: str,
    importance_level: str,
    deadline: str,
    estimated_hours: float,
    is_spread_learning: bool = False,
    preferred_study_days: int | None = None,
    min_session_hours: float | None = None,
    max_session_hours: float | None = None
):
    conn = get_connection()
    cursor = conn.cursor()

    normalized_task_type = _normalize_task_type(task_type)
    derived_task_intensity = _derive_task_intensity(normalized_task_type)
    normalized_subject = subject.strip() if subject and subject.strip() else "General"

    if normalized_task_type != "Study / Learning":
        is_spread_learning = False
        preferred_study_days = None
        min_session_hours = None
        max_session_hours = None

    adjusted_hours = round(float(estimated_hours), 2)

    cursor.execute("""
        UPDATE tasks
        SET task_name = %s,
            subject = %s,
            task_type = %s,
            importance_level = %s,
            task_intensity = %s,
            deadline = %s,
            estimated_hours = %s,
            adjusted_hours = %s,
            is_spread_learning = %s,
            preferred_study_days = %s,
            min_session_hours = %s,
            max_session_hours = %s
        WHERE task_id = %s
    """, (
        task_name,
        normalized_subject,
        normalized_task_type,
        importance_level,
        derived_task_intensity,
        deadline,
        float(estimated_hours),
        adjusted_hours,
        is_spread_learning,
        preferred_study_days,
        min_session_hours,
        max_session_hours,
        task_id
    ))

    conn.commit()
    cursor.close()
    conn.close()

def get_tasks_for_student(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            task_id,
            task_name,
            subject,
            task_type,
            importance_level,
            task_intensity,
            TO_CHAR(deadline, 'YYYY-MM-DD') AS deadline,
            estimated_hours,
            adjusted_hours,
            status,
            is_spread_learning,
            preferred_study_days,
            min_session_hours,
            max_session_hours
        FROM tasks
        WHERE student_id = %s
        ORDER BY deadline ASC
    """, (student_id,))

    tasks = cursor.fetchall()
    cursor.close()
    conn.close()
    return tasks


def get_plannable_tasks_for_student(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            task_id,
            task_name,
            subject,
            task_type,
            importance_level,
            task_intensity,
            TO_CHAR(deadline, 'YYYY-MM-DD') AS deadline,
            estimated_hours,
            adjusted_hours,
            status,
            is_spread_learning,
            preferred_study_days,
            min_session_hours,
            max_session_hours
        FROM tasks
        WHERE student_id = %s
          AND status = 'planned'
        ORDER BY deadline ASC
    """, (student_id,))

    tasks = cursor.fetchall()
    cursor.close()
    conn.close()
    return tasks


def get_task_by_id(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            task_id,
            student_id,
            task_name,
            subject,
            task_type,
            importance_level,
            task_intensity,
            TO_CHAR(deadline, 'YYYY-MM-DD') AS deadline,
            estimated_hours,
            adjusted_hours,
            status,
            is_spread_learning,
            preferred_study_days,
            min_session_hours,
            max_session_hours
        FROM tasks
        WHERE task_id = %s
    """, (task_id,))

    task = cursor.fetchone()
    cursor.close()
    conn.close()
    return task


def delete_task(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM study_plan
        WHERE task_id = %s
    """, (task_id,))

    cursor.execute("""
        DELETE FROM task_history
        WHERE task_id = %s
    """, (task_id,))

    cursor.execute("""
        DELETE FROM tasks
        WHERE task_id = %s
    """, (task_id,))

    conn.commit()
    cursor.close()
    conn.close()


def delete_all_tasks(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM task_history
        WHERE student_id = %s
    """, (student_id,))

    cursor.execute("""
        DELETE FROM study_plan
        WHERE student_id = %s
    """, (student_id,))

    cursor.execute("""
        DELETE FROM tasks
        WHERE student_id = %s
    """, (student_id,))

    conn.commit()
    cursor.close()
    conn.close()


# -----------------------------
# Task feedback / learning
# -----------------------------
def log_task_feedback(
    task_id: int,
    student_id: str,
    task_name: str,
    subject: str,
    task_type: str,
    importance_level: str,
    estimated_hours: float,
    adjusted_hours: float,
    actual_hours: float,
    completed: bool,
    remaining_hours: float,
    logged_at: str,
    did_not_start: bool = False,
    perceived_difficulty: int | None = None,
    mental_effort: int | None = None,
    confidence_level: int | None = None,
    focus_level: int | None = None
):
    conn = get_connection()
    cursor = conn.cursor()

    normalized_task_type = _normalize_task_type(task_type)
    normalized_subject = subject.strip() if subject and subject.strip() else "General"

    if did_not_start:
        cursor.execute("""
            INSERT INTO task_history (
                task_id,
                student_id,
                task_name,
                subject,
                task_type,
                importance_level,
                estimated_hours,
                adjusted_hours,
                actual_hours,
                completed,
                remaining_hours,
                logged_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            task_id,
            student_id,
            task_name,
            normalized_subject,
            normalized_task_type,
            importance_level,
            float(estimated_hours),
            float(adjusted_hours),
            0.0,
            False,
            float(adjusted_hours),
            logged_at
        ))

        cursor.execute("""
            UPDATE tasks
            SET adjusted_hours = %s,
                status = 'planned'
            WHERE task_id = %s
        """, (float(adjusted_hours), task_id))

        conn.commit()
        cursor.close()
        conn.close()
        return

    cursor.execute("""
        INSERT INTO task_history (
            task_id,
            student_id,
            task_name,
            subject,
            task_type,
            importance_level,
            estimated_hours,
            adjusted_hours,
            actual_hours,
            completed,
            remaining_hours,
            perceived_difficulty,
            mental_effort,
            confidence_level,
            focus_level,
            logged_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        task_id,
        student_id,
        task_name,
        normalized_subject,
        normalized_task_type,
        importance_level,
        float(estimated_hours),
        float(adjusted_hours),
        float(actual_hours),
        completed,
        float(remaining_hours),
        perceived_difficulty,
        mental_effort,
        confidence_level,
        focus_level,
        logged_at
    ))

    if completed:
        cursor.execute("""
            SELECT COALESCE(SUM(actual_hours), 0)
            FROM task_history
            WHERE task_id = %s
        """, (task_id,))

        total_actual_hours = float(cursor.fetchone()[0] or 0.0)

        if float(estimated_hours) > 0 and total_actual_hours > 0:
            ratio = total_actual_hours / float(estimated_hours)
            clamped_ratio = _clamp_ratio(ratio)

            cursor.execute("""
                SELECT
                    planning_factor,
                    feedback_count,
                    avg_difficulty,
                    avg_mental_effort,
                    avg_confidence,
                    avg_focus
                FROM student_task_type_learning
                WHERE student_id = %s
                  AND task_type = %s
                  AND subject = %s
            """, (student_id, normalized_task_type, normalized_subject))

            existing = cursor.fetchone()
            now = datetime.now()

            if existing:
                (
                    old_factor,
                    old_feedback_count,
                    old_avg_difficulty,
                    old_avg_mental_effort,
                    old_avg_confidence,
                    old_avg_focus
                ) = existing

                old_factor = float(old_factor)
                old_feedback_count = int(old_feedback_count)
                old_avg_difficulty = float(old_avg_difficulty)
                old_avg_mental_effort = float(old_avg_mental_effort)
                old_avg_confidence = float(old_avg_confidence)
                old_avg_focus = float(old_avg_focus)

                new_smoothed_factor = (SMOOTHING_ALPHA * clamped_ratio) + ((1 - SMOOTHING_ALPHA) * old_factor)

                def smooth_metric(old_value: float, new_value):
                    if new_value is None:
                        return old_value
                    return (SMOOTHING_ALPHA * float(new_value)) + ((1 - SMOOTHING_ALPHA) * old_value)

                new_avg_difficulty = smooth_metric(old_avg_difficulty, perceived_difficulty)
                new_avg_mental_effort = smooth_metric(old_avg_mental_effort, mental_effort)
                new_avg_confidence = smooth_metric(old_avg_confidence, confidence_level)
                new_avg_focus = smooth_metric(old_avg_focus, focus_level)

                cursor.execute("""
                    UPDATE student_task_type_learning
                    SET planning_factor = %s,
                        feedback_count = %s,
                        avg_difficulty = %s,
                        avg_mental_effort = %s,
                        avg_confidence = %s,
                        avg_focus = %s,
                        updated_at = %s
                    WHERE student_id = %s
                      AND task_type = %s
                      AND subject = %s
                """, (
                    round(new_smoothed_factor, 4),
                    old_feedback_count + 1,
                    round(new_avg_difficulty, 4),
                    round(new_avg_mental_effort, 4),
                    round(new_avg_confidence, 4),
                    round(new_avg_focus, 4),
                    now,
                    student_id,
                    normalized_task_type,
                    normalized_subject
                ))

            else:
                cursor.execute("""
                    INSERT INTO student_task_type_learning (
                        student_id,
                        task_type,
                        subject,
                        planning_factor,
                        feedback_count,
                        avg_difficulty,
                        avg_mental_effort,
                        avg_confidence,
                        avg_focus,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    student_id,
                    normalized_task_type,
                    normalized_subject,
                    round(clamped_ratio, 4),
                    1,
                    float(perceived_difficulty) if perceived_difficulty is not None else 0.0,
                    float(mental_effort) if mental_effort is not None else 0.0,
                    float(confidence_level) if confidence_level is not None else 0.0,
                    float(focus_level) if focus_level is not None else 0.0,
                    now
                ))

        cursor.execute("""
            UPDATE tasks
            SET status = 'completed',
                adjusted_hours = 0
            WHERE task_id = %s
        """, (task_id,))

    else:
        if float(remaining_hours) > 0:
            new_adjusted_hours = round(float(remaining_hours), 2)

            cursor.execute("""
                UPDATE tasks
                SET adjusted_hours = %s,
                    status = 'planned'
                WHERE task_id = %s
            """, (new_adjusted_hours, task_id))
        else:
            cursor.execute("""
                UPDATE tasks
                SET status = 'incomplete',
                    adjusted_hours = 0
                WHERE task_id = %s
            """, (task_id,))

    conn.commit()
    cursor.close()
    conn.close()


def get_student_task_type_planning_factor(student_id: str, task_type: str, subject: str = "General") -> float:
    conn = get_connection()
    cursor = conn.cursor()

    normalized_task_type = _normalize_task_type(task_type)
    normalized_subject = subject.strip() if subject and subject.strip() else "General"

    cursor.execute("""
        SELECT planning_factor
        FROM student_task_type_learning
        WHERE student_id = %s
          AND task_type = %s
          AND subject = %s
    """, (student_id, normalized_task_type, normalized_subject))

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return DEFAULT_PLANNING_FACTOR

    try:
        return float(row[0])
    except (TypeError, ValueError):
        return DEFAULT_PLANNING_FACTOR


def upsert_student_task_type_learning(
    student_id: str,
    task_type: str,
    new_ratio: float,
    subject: str = "General"
):
    conn = get_connection()
    cursor = conn.cursor()

    normalized_task_type = _normalize_task_type(task_type)
    normalized_subject = subject.strip() if subject and subject.strip() else "General"
    clamped_ratio = _clamp_ratio(float(new_ratio))
    now = datetime.now()

    cursor.execute("""
        SELECT planning_factor, feedback_count
        FROM student_task_type_learning
        WHERE student_id = %s
          AND task_type = %s
          AND subject = %s
    """, (student_id, normalized_task_type, normalized_subject))

    existing = cursor.fetchone()

    if existing:
        old_factor = float(existing[0])
        old_feedback_count = int(existing[1])

        new_smoothed_factor = (SMOOTHING_ALPHA * clamped_ratio) + ((1 - SMOOTHING_ALPHA) * old_factor)

        cursor.execute("""
            UPDATE student_task_type_learning
            SET planning_factor = %s,
                feedback_count = %s,
                updated_at = %s
            WHERE student_id = %s
              AND task_type = %s
              AND subject = %s
        """, (
            round(new_smoothed_factor, 4),
            old_feedback_count + 1,
            now,
            student_id,
            normalized_task_type,
            normalized_subject
        ))
    else:
        cursor.execute("""
            INSERT INTO student_task_type_learning (
                student_id,
                task_type,
                subject,
                planning_factor,
                feedback_count,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            student_id,
            normalized_task_type,
            normalized_subject,
            round(clamped_ratio, 4),
            1,
            now
        ))

    conn.commit()
    cursor.close()
    conn.close()


def get_learning_profile_for_student(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            task_type,
            subject,
            planning_factor,
            feedback_count,
            avg_difficulty,
            avg_mental_effort,
            avg_confidence,
            avg_focus
        FROM student_task_type_learning
        WHERE student_id = %s
        ORDER BY task_type ASC, subject ASC
    """, (student_id,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


# -----------------------------
# History
# -----------------------------
def get_history_for_student(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            history_id,
            task_id,
            task_name,
            subject,
            task_type,
            importance_level,
            estimated_hours,
            adjusted_hours,
            actual_hours,
            completed,
            remaining_hours,
            perceived_difficulty,
            mental_effort,
            confidence_level,
            focus_level,
            TO_CHAR(logged_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS logged_at
        FROM task_history
        WHERE student_id = %s
        ORDER BY logged_at DESC
    """, (student_id,))

    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return history


def get_task_learning_rows(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            task_name,
            subject,
            task_type,
            importance_level,
            estimated_hours,
            actual_hours,
            remaining_hours,
            completed,
            perceived_difficulty,
            mental_effort,
            confidence_level,
            focus_level,
            TO_CHAR(logged_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS logged_at
        FROM task_history
        WHERE student_id = %s
        ORDER BY logged_at DESC
    """, (student_id,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def save_ai_feedback_reflection(student_id: str, task_id: int, role: str, content: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO ai_feedback_reflections (
            student_id,
            task_id,
            role,
            content,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        student_id,
        task_id,
        role,
        content,
        datetime.now()
    ))

    conn.commit()
    cursor.close()
    conn.close()


def get_ai_feedback_reflections(student_id: str, task_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT role, content, TO_CHAR(created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS created_at
        FROM ai_feedback_reflections
        WHERE student_id = %s
          AND task_id = %s
        ORDER BY created_at ASC
    """, (
        student_id,
        task_id
    ))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


# -----------------------------
# Day preferences (sleep / wake)
# -----------------------------
def upsert_day_preference(student_id: str, study_date: str, wake_time: str, sleep_time: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO day_preferences (
            student_id,
            study_date,
            wake_time,
            sleep_time
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (student_id, study_date)
        DO UPDATE SET
            wake_time = EXCLUDED.wake_time,
            sleep_time = EXCLUDED.sleep_time
    """, (
        student_id,
        study_date,
        wake_time,
        sleep_time
    ))

    conn.commit()
    cursor.close()
    conn.close()


def delete_day_preference(student_id: str, study_date: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM day_preferences
        WHERE student_id = %s
          AND study_date = %s
    """, (student_id, study_date))

    conn.commit()
    cursor.close()
    conn.close()


def get_day_preferences_for_range(student_id: str, start_date: str, end_date: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            TO_CHAR(study_date, 'YYYY-MM-DD') AS study_date,
            TO_CHAR(wake_time, 'HH24:MI') AS wake_time,
            TO_CHAR(sleep_time, 'HH24:MI') AS sleep_time
        FROM day_preferences
        WHERE student_id = %s
          AND study_date BETWEEN %s AND %s
        ORDER BY study_date ASC
    """, (
        student_id,
        start_date,
        end_date
    ))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


# -----------------------------
# Activity slots
# -----------------------------
def add_activity_slot(student_id: str, study_date: str, start_time: str, end_time: str, reason: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO activity_slots (
            student_id,
            study_date,
            start_time,
            end_time,
            reason
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        student_id,
        study_date,
        start_time,
        end_time,
        reason
    ))

    conn.commit()
    cursor.close()
    conn.close()

def update_activity_slot(slot_id: int, study_date: str, start_time: str, end_time: str, reason: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE activity_slots
        SET study_date = %s,
            start_time = %s,
            end_time = %s,
            reason = %s
        WHERE slot_id = %s
    """, (
        study_date,
        start_time,
        end_time,
        reason,
        slot_id
    ))

    conn.commit()
    cursor.close()
    conn.close()

def get_activity_slots_for_range(student_id: str, start_date: str, end_date: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            slot_id,
            TO_CHAR(study_date, 'YYYY-MM-DD') AS study_date,
            TO_CHAR(start_time, 'HH24:MI') AS start_time,
            TO_CHAR(end_time, 'HH24:MI') AS end_time,
            reason
        FROM activity_slots
        WHERE student_id = %s
          AND study_date BETWEEN %s AND %s
        ORDER BY study_date ASC, start_time ASC
    """, (
        student_id,
        start_date,
        end_date
    ))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def delete_activity_slot(slot_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM activity_slots
        WHERE slot_id = %s
    """, (slot_id,))

    conn.commit()
    cursor.close()
    conn.close()


# -----------------------------
# Study plan storage
# -----------------------------
def clear_saved_study_plan(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM study_plan
        WHERE student_id = %s
    """, (student_id,))

    conn.commit()
    cursor.close()
    conn.close()


def save_study_plan(student_id: str, daily_plan: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM study_plan
        WHERE student_id = %s
    """, (student_id,))

    created_at = datetime.now()

    for study_date, task_items in daily_plan.items():
        for task in task_items:
            cursor.execute("""
                INSERT INTO study_plan (
                    student_id,
                    task_id,
                    study_date,
                    start_time,
                    end_time,
                    planned_hours,
                    energy_level,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                student_id,
                task.get("task_id"),
                study_date,
                task.get("start_time"),
                task.get("end_time"),
                task["hours"],
                task.get("energy_level"),
                created_at
            ))

    conn.commit()
    cursor.close()
    conn.close()

def save_planner_personalization_log(student_id: str, task_rows: list, planner_advice: dict):
    conn = get_connection()
    cursor = conn.cursor()

    advice_map = {
        item["task_id"]: item
        for item in planner_advice.get("task_recommendations", [])
    }

    cursor.execute("""
        DELETE FROM planner_personalization_log
        WHERE student_id = %s
    """, (student_id,))

    created_at = datetime.now()

    for task in task_rows:
        (
            task_id,
            task_name,
            subject,
            task_type,
            importance_level,
            task_intensity,
            deadline,
            estimated_hours,
            adjusted_hours,
            status,
            is_spread_learning,
            preferred_study_days,
            min_session_hours,
            max_session_hours
        ) = task

        advice = advice_map.get(task_id, {})

        cursor.execute("""
            INSERT INTO planner_personalization_log (
                student_id,
                task_id,
                task_name,
                subject,
                task_type,
                add_time_buffer_percent,
                preferred_energy,
                max_session_hours,
                avoid_after_high_difficulty_task,
                reason,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            student_id,
            task_id,
            task_name,
            subject,
            task_type,
            int(advice.get("add_time_buffer_percent", 0)),
            advice.get("preferred_energy"),
            advice.get("max_session_hours"),
            bool(advice.get("avoid_after_high_difficulty_task", False)),
            advice.get("reason", ""),
            created_at
        ))

    conn.commit()
    cursor.close()
    conn.close()

def save_ai_learning_preference(
    student_id: str,
    task_type: str,
    subject: str,
    preference_text: str,
    add_time_buffer_percent: int = 0,
    preferred_energy: str | None = None,
    max_session_hours: float | None = None,
    avoid_after_high_difficulty_task: bool = False,
    status: str = "accepted"
):
    conn = get_connection()
    cursor = conn.cursor()

    normalized_task_type = _normalize_task_type(task_type)
    normalized_subject = subject.strip() if subject and subject.strip() else "General"
    now = datetime.now()

    cursor.execute("""
        INSERT INTO ai_learning_preferences (
            student_id,
            task_type,
            subject,
            preference_text,
            add_time_buffer_percent,
            preferred_energy,
            max_session_hours,
            avoid_after_high_difficulty_task,
            status,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        student_id,
        normalized_task_type,
        normalized_subject,
        preference_text,
        int(add_time_buffer_percent),
        preferred_energy,
        max_session_hours,
        bool(avoid_after_high_difficulty_task),
        status,
        now,
        now
    ))

    conn.commit()
    cursor.close()
    conn.close()


def get_ai_learning_preferences_for_student(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            preference_id,
            task_type,
            subject,
            preference_text,
            status,
            TO_CHAR(created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS created_at,
            TO_CHAR(updated_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS updated_at
        FROM ai_learning_preferences
        WHERE student_id = %s
          AND status = 'accepted'
        ORDER BY updated_at DESC
    """, (student_id,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_ai_learning_preferences_for_task(student_id: str, task_type: str, subject: str):
    conn = get_connection()
    cursor = conn.cursor()

    normalized_task_type = _normalize_task_type(task_type)
    normalized_subject = subject.strip() if subject and subject.strip() else "General"

    cursor.execute("""
        SELECT
            preference_id,
            preference_text,
            status,
            TO_CHAR(created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS created_at,
            TO_CHAR(updated_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS updated_at,
            add_time_buffer_percent,
            preferred_energy,
            max_session_hours,
            avoid_after_high_difficulty_task
        FROM ai_learning_preferences
        WHERE student_id = %s
          AND task_type = %s
          AND subject = %s
          AND status = 'accepted'
        ORDER BY updated_at DESC
    """, (
        student_id,
        normalized_task_type,
        normalized_subject
    ))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_saved_study_plan(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            sp.plan_id,
            TO_CHAR(sp.study_date, 'YYYY-MM-DD') AS study_date,
            sp.task_id,
            COALESCE(t.task_name, 'Break') AS task_name,
            COALESCE(t.subject, '-') AS subject,
            COALESCE(t.task_type, 'Break') AS task_type,
            COALESCE(t.importance_level, 'Low') AS importance_level,
            TO_CHAR(t.deadline, 'YYYY-MM-DD') AS deadline,
            TO_CHAR(sp.start_time, 'HH24:MI') AS start_time,
            TO_CHAR(sp.end_time, 'HH24:MI') AS end_time,
            sp.planned_hours,
            COALESCE(sp.energy_level, 'Recovery') AS energy_level,
            TO_CHAR(sp.created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS created_at
        FROM study_plan sp
        LEFT JOIN tasks t ON sp.task_id = t.task_id
        WHERE sp.student_id = %s
        ORDER BY sp.study_date ASC, sp.start_time ASC, sp.plan_id ASC
    """, (student_id,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_due_feedback_tasks(student_id: str, current_dt: datetime | None = None):
    if current_dt is None:
        current_dt = datetime.now()

    current_date = current_dt.date().isoformat()
    current_time = current_dt.strftime("%H:%M")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        WITH latest_task_block AS (
            SELECT DISTINCT ON (sp.task_id)
                sp.task_id,
                sp.student_id,
                sp.study_date,
                sp.end_time
            FROM study_plan sp
            WHERE sp.student_id = %s
              AND sp.task_id IS NOT NULL
            ORDER BY
                sp.task_id,
                sp.study_date DESC,
                sp.end_time DESC NULLS LAST
        )
        SELECT
            ltb.task_id,
            t.task_name,
            t.subject,
            t.task_type,
            t.importance_level,
            TO_CHAR(ltb.study_date, 'YYYY-MM-DD') AS latest_due_date,
            TO_CHAR(ltb.end_time, 'HH24:MI') AS latest_due_time
        FROM latest_task_block ltb
        JOIN tasks t
            ON ltb.task_id = t.task_id
        WHERE t.status = 'planned'
          AND (
                ltb.study_date < %s::date
                OR (
                    ltb.study_date = %s::date
                    AND ltb.end_time IS NOT NULL
                    AND ltb.end_time <= %s::time
                )
              )
          AND NOT EXISTS (
                SELECT 1
                FROM task_history th
                WHERE th.task_id = ltb.task_id
                  AND th.logged_at >= (
                        ltb.study_date::timestamp +
                        COALESCE(ltb.end_time, TIME '00:00')
                  )
          )
        ORDER BY ltb.study_date ASC, ltb.end_time ASC
    """, (
        student_id,
        current_date,
        current_date,
        current_time
    ))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


# -----------------------------
# Estimation analysis helpers
# -----------------------------
def _classify_estimation_pattern(actual_total_hours: float, estimated_hours: float):
    if estimated_hours <= 0:
        return "No estimate"

    ratio = actual_total_hours / estimated_hours

    if ratio > 1.10:
        return "Underestimated"
    elif ratio < 0.90:
        return "Overestimated"
    return "Accurate"


# -----------------------------
# Accuracy / Admin analytics
# -----------------------------
def get_estimation_accuracy_for_student(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            t.task_id,
            t.task_name,
            t.task_type,
            t.importance_level,
            t.estimated_hours,
            t.adjusted_hours,
            t.status,
            COALESCE(SUM(th.actual_hours), 0) AS total_actual_hours,
            COALESCE(MAX(th.remaining_hours), 0) AS latest_remaining_hours
        FROM tasks t
        LEFT JOIN task_history th
            ON t.task_id = th.task_id
        WHERE t.student_id = %s
        GROUP BY
            t.task_id,
            t.task_name,
            t.task_type,
            t.importance_level,
            t.estimated_hours,
            t.adjusted_hours,
            t.status
        ORDER BY t.task_id DESC
    """, (student_id,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    results = []

    for row in rows:
        (
            task_id,
            task_name,
            task_type,
            importance_level,
            estimated_hours,
            adjusted_hours,
            status,
            total_actual_hours,
            latest_remaining_hours
        ) = row

        estimated_hours = float(estimated_hours)
        adjusted_hours = float(adjusted_hours)

        if status == "completed":
            actual_total_hours = float(total_actual_hours)
        else:
            actual_total_hours = float(total_actual_hours) + float(adjusted_hours)

        if actual_total_hours == 0 or estimated_hours <= 0:
            estimation_error = 0.0
            estimation_ratio = 0.0
            pattern = "No feedback yet"
        else:
            estimation_error = abs(actual_total_hours - estimated_hours)
            estimation_ratio = actual_total_hours / estimated_hours
            pattern = _classify_estimation_pattern(actual_total_hours, estimated_hours)

        results.append({
            "task_id": task_id,
            "task_name": task_name,
            "task_type": task_type,
            "importance_level": importance_level,
            "status": status,
            "estimated_hours": round(estimated_hours, 2),
            "adjusted_hours": round(adjusted_hours, 2),
            "actual_total_hours": round(actual_total_hours, 2),
            "estimation_error": round(estimation_error, 2),
            "estimation_ratio": round(estimation_ratio, 2),
            "pattern": pattern
        })

    return results


def get_estimation_accuracy_summary(student_id: str):
    rows = get_estimation_accuracy_for_student(student_id)

    comparable_rows = [
        row for row in rows
        if row["actual_total_hours"] > 0 and row["estimated_hours"] > 0
    ]

    if not comparable_rows:
        return {
            "total_tasks_compared": 0,
            "underestimated": 0,
            "overestimated": 0,
            "accurate": 0,
            "avg_estimation_error": 0.0,
            "avg_estimation_ratio": 0.0
        }

    underestimated = sum(1 for row in comparable_rows if row["pattern"] == "Underestimated")
    overestimated = sum(1 for row in comparable_rows if row["pattern"] == "Overestimated")
    accurate = sum(1 for row in comparable_rows if row["pattern"] == "Accurate")

    avg_estimation_error = sum(row["estimation_error"] for row in comparable_rows) / len(comparable_rows)
    avg_estimation_ratio = sum(row["estimation_ratio"] for row in comparable_rows) / len(comparable_rows)

    return {
        "total_tasks_compared": len(comparable_rows),
        "underestimated": underestimated,
        "overestimated": overestimated,
        "accurate": accurate,
        "avg_estimation_error": round(avg_estimation_error, 2),
        "avg_estimation_ratio": round(avg_estimation_ratio, 2)
    }


def get_estimation_accuracy_for_all_students():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            t.student_id,
            s.name,
            t.task_id,
            t.task_name,
            t.task_type,
            t.importance_level,
            t.estimated_hours,
            t.adjusted_hours,
            t.status,
            COALESCE(SUM(th.actual_hours), 0) AS total_actual_hours,
            COALESCE(MAX(th.remaining_hours), 0) AS latest_remaining_hours
        FROM tasks t
        LEFT JOIN students s
            ON t.student_id = s.student_id
        LEFT JOIN task_history th
            ON t.task_id = th.task_id
        GROUP BY
            t.student_id,
            s.name,
            t.task_id,
            t.task_name,
            t.task_type,
            t.importance_level,
            t.estimated_hours,
            t.adjusted_hours,
            t.status
        ORDER BY t.student_id ASC, t.task_id DESC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    results = []

    for row in rows:
        (
            student_id,
            student_name,
            task_id,
            task_name,
            task_type,
            importance_level,
            estimated_hours,
            adjusted_hours,
            status,
            total_actual_hours,
            latest_remaining_hours
        ) = row

        estimated_hours = float(estimated_hours)
        adjusted_hours = float(adjusted_hours)

        if status == "completed":
            actual_total_hours = float(total_actual_hours)
        else:
            continue

        if actual_total_hours == 0 or estimated_hours <= 0:
            estimation_error = 0.0
            estimation_ratio = 0.0
            pattern = "No feedback yet"
        else:
            estimation_error = abs(actual_total_hours - estimated_hours)
            estimation_ratio = actual_total_hours / estimated_hours
            pattern = _classify_estimation_pattern(actual_total_hours, estimated_hours)

        results.append({
            "student_id": student_id,
            "student_name": student_name,
            "task_id": task_id,
            "task_name": task_name,
            "task_type": task_type,
            "importance_level": importance_level,
            "status": status,
            "estimated_hours": round(estimated_hours, 2),
            "adjusted_hours": round(adjusted_hours, 2),
            "actual_total_hours": round(actual_total_hours, 2),
            "estimation_error": round(estimation_error, 2),
            "estimation_ratio": round(estimation_ratio, 2),
            "pattern": pattern
        })

    return results


def get_admin_summary_per_student():
    rows = get_estimation_accuracy_for_all_students()

    summary = {}

    for row in rows:
        if row["actual_total_hours"] <= 0 or row["estimated_hours"] <= 0:
            continue

        student_id = row["student_id"]
        student_name = row["student_name"]

        if student_id not in summary:
            summary[student_id] = {
                "student_name": student_name,
                "tasks_compared": 0,
                "underestimated": 0,
                "overestimated": 0,
                "accurate": 0,
                "total_estimation_error": 0.0,
                "total_estimation_ratio": 0.0
            }

        summary[student_id]["tasks_compared"] += 1
        summary[student_id]["total_estimation_error"] += row["estimation_error"]
        summary[student_id]["total_estimation_ratio"] += row["estimation_ratio"]

        if row["pattern"] == "Underestimated":
            summary[student_id]["underestimated"] += 1
        elif row["pattern"] == "Overestimated":
            summary[student_id]["overestimated"] += 1
        elif row["pattern"] == "Accurate":
            summary[student_id]["accurate"] += 1

    result = []

    for student_id, data in summary.items():
        tasks_compared = data["tasks_compared"]

        result.append({
            "student_id": student_id,
            "student_name": data["student_name"],
            "tasks_compared": tasks_compared,
            "underestimated": data["underestimated"],
            "overestimated": data["overestimated"],
            "accurate": data["accurate"],
            "avg_estimation_error": round(data["total_estimation_error"] / tasks_compared, 2),
            "avg_estimation_ratio": round(data["total_estimation_ratio"] / tasks_compared, 2)
        })

    result.sort(key=lambda x: x["student_id"])
    return result


def get_admin_global_summary():
    rows = get_estimation_accuracy_for_all_students()
    comparable_rows = [
        row for row in rows
        if row["actual_total_hours"] > 0 and row["estimated_hours"] > 0
    ]

    if not comparable_rows:
        return {
            "students_with_feedback": 0,
            "tasks_compared": 0,
            "underestimated": 0,
            "overestimated": 0,
            "accurate": 0,
            "avg_estimation_error": 0.0,
            "avg_estimation_ratio": 0.0
        }

    unique_students = len(set(row["student_id"] for row in comparable_rows))
    underestimated = sum(1 for row in comparable_rows if row["pattern"] == "Underestimated")
    overestimated = sum(1 for row in comparable_rows if row["pattern"] == "Overestimated")
    accurate = sum(1 for row in comparable_rows if row["pattern"] == "Accurate")

    avg_estimation_error = sum(row["estimation_error"] for row in comparable_rows) / len(comparable_rows)
    avg_estimation_ratio = sum(row["estimation_ratio"] for row in comparable_rows) / len(comparable_rows)

    return {
        "students_with_feedback": unique_students,
        "tasks_compared": len(comparable_rows),
        "underestimated": underestimated,
        "overestimated": overestimated,
        "accurate": accurate,
        "avg_estimation_error": round(avg_estimation_error, 2),
        "avg_estimation_ratio": round(avg_estimation_ratio, 2)
    }


def get_task_type_analysis():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            t.task_type,
            COUNT(*) AS total_tasks,
            AVG(t.estimated_hours) AS avg_estimated_hours,
            AVG(t.adjusted_hours) AS avg_adjusted_hours,
            AVG(COALESCE(actuals.total_actual_hours, 0)) AS avg_actual_hours
        FROM tasks t
        LEFT JOIN (
            SELECT
                task_id,
                SUM(actual_hours) AS total_actual_hours
            FROM task_history
            GROUP BY task_id
        ) actuals
            ON t.task_id = actuals.task_id
        GROUP BY t.task_type
        ORDER BY t.task_type ASC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    results = []

    for row in rows:
        task_type, total_tasks, avg_estimated, avg_adjusted, avg_actual = row

        avg_estimated = float(avg_estimated or 0.0)
        avg_adjusted = float(avg_adjusted or 0.0)
        avg_actual = float(avg_actual or 0.0)

        raw_ratio = round(avg_actual / avg_estimated, 2) if avg_estimated > 0 else 0.0
        adjusted_ratio = round(avg_actual / avg_adjusted, 2) if avg_adjusted > 0 else 0.0

        results.append({
            "task_type": task_type,
            "total_tasks": int(total_tasks),
            "avg_estimated_hours": round(avg_estimated, 2),
            "avg_adjusted_hours": round(avg_adjusted, 2),
            "avg_actual_hours": round(avg_actual, 2),
            "raw_ratio": raw_ratio,
            "adjusted_ratio": adjusted_ratio
        })

    return results


def get_subject_analysis():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            t.subject,
            COUNT(*) AS total_tasks,
            AVG(t.estimated_hours) AS avg_estimated_hours,
            AVG(t.adjusted_hours) AS avg_adjusted_hours,
            AVG(COALESCE(actuals.total_actual_hours, 0)) AS avg_actual_hours,
            AVG(COALESCE(lp.avg_difficulty, 0)) AS avg_difficulty,
            AVG(COALESCE(lp.avg_mental_effort, 0)) AS avg_mental_effort,
            AVG(COALESCE(lp.avg_confidence, 0)) AS avg_confidence,
            AVG(COALESCE(lp.avg_focus, 0)) AS avg_focus
        FROM tasks t
        LEFT JOIN (
            SELECT
                task_id,
                SUM(actual_hours) AS total_actual_hours
            FROM task_history
            GROUP BY task_id
        ) actuals
            ON t.task_id = actuals.task_id
        LEFT JOIN student_task_type_learning lp
            ON t.student_id = lp.student_id
           AND t.task_type = lp.task_type
           AND t.subject = lp.subject
        GROUP BY t.subject
        ORDER BY t.subject ASC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    results = []

    for row in rows:
        (
            subject,
            total_tasks,
            avg_estimated,
            avg_adjusted,
            avg_actual,
            avg_difficulty,
            avg_mental_effort,
            avg_confidence,
            avg_focus
        ) = row

        avg_estimated = float(avg_estimated or 0.0)
        avg_adjusted = float(avg_adjusted or 0.0)
        avg_actual = float(avg_actual or 0.0)

        raw_ratio = round(avg_actual / avg_estimated, 2) if avg_estimated > 0 else 0.0
        adjusted_ratio = round(avg_actual / avg_adjusted, 2) if avg_adjusted > 0 else 0.0

        results.append({
            "subject": subject,
            "total_tasks": int(total_tasks),
            "avg_estimated_hours": round(avg_estimated, 2),
            "avg_adjusted_hours": round(avg_adjusted, 2),
            "avg_actual_hours": round(avg_actual, 2),
            "raw_ratio": raw_ratio,
            "adjusted_ratio": adjusted_ratio,
            "avg_difficulty": round(float(avg_difficulty or 0.0), 2),
            "avg_mental_effort": round(float(avg_mental_effort or 0.0), 2),
            "avg_confidence": round(float(avg_confidence or 0.0), 2),
            "avg_focus": round(float(avg_focus or 0.0), 2)
        })

    return results


def get_all_learning_profiles():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            l.student_id,
            s.name,
            l.task_type,
            l.subject,
            l.planning_factor,
            l.feedback_count,
            l.avg_difficulty,
            l.avg_mental_effort,
            l.avg_confidence,
            l.avg_focus,
            TO_CHAR(l.updated_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS updated_at
        FROM student_task_type_learning l
        LEFT JOIN students s
            ON l.student_id = s.student_id
        ORDER BY l.student_id ASC, l.task_type ASC, l.subject ASC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return rows


def get_adaptive_planner_evaluation():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            t.student_id,
            s.name,
            t.task_id,
            t.task_name,
            t.task_type,
            t.estimated_hours,
            t.adjusted_hours,
            t.status,
            COALESCE(actuals.total_actual_hours, 0) AS total_actual_hours
        FROM tasks t
        LEFT JOIN students s
            ON t.student_id = s.student_id
        LEFT JOIN (
            SELECT
                task_id,
                SUM(actual_hours) AS total_actual_hours
            FROM task_history
            GROUP BY task_id
        ) actuals
            ON t.task_id = actuals.task_id
        ORDER BY t.student_id ASC, t.task_id DESC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    results = []

    for row in rows:
        (
            student_id,
            student_name,
            task_id,
            task_name,
            task_type,
            estimated_hours,
            adjusted_hours,
            status,
            total_actual_hours
        ) = row

        estimated_hours = float(estimated_hours or 0.0)
        adjusted_hours = float(adjusted_hours or 0.0)
        total_actual_hours = float(total_actual_hours or 0.0)

        raw_error = abs(total_actual_hours - estimated_hours) if total_actual_hours > 0 else 0.0
        adjusted_error = abs(total_actual_hours - adjusted_hours) if total_actual_hours > 0 else 0.0

        results.append({
            "student_id": student_id,
            "student_name": student_name,
            "task_id": task_id,
            "task_name": task_name,
            "task_type": task_type,
            "status": status,
            "estimated_hours": round(estimated_hours, 2),
            "adjusted_hours": round(adjusted_hours, 2),
            "actual_total_hours": round(total_actual_hours, 2),
            "raw_error": round(raw_error, 2),
            "adjusted_error": round(adjusted_error, 2)
        })

    return results


def get_adaptive_planner_summary():
    rows = get_adaptive_planner_evaluation()

    comparable_rows = [
        row for row in rows
        if row["actual_total_hours"] > 0
    ]

    if not comparable_rows:
        return {
            "tasks_compared": 0,
            "avg_raw_error": 0.0,
            "avg_adjusted_error": 0.0,
            "adjusted_better_count": 0,
            "raw_better_count": 0,
            "equal_count": 0
        }

    avg_raw_error = sum(row["raw_error"] for row in comparable_rows) / len(comparable_rows)
    avg_adjusted_error = sum(row["adjusted_error"] for row in comparable_rows) / len(comparable_rows)

    adjusted_better_count = sum(1 for row in comparable_rows if row["adjusted_error"] < row["raw_error"])
    raw_better_count = sum(1 for row in comparable_rows if row["adjusted_error"] > row["raw_error"])
    equal_count = sum(1 for row in comparable_rows if row["adjusted_error"] == row["raw_error"])

    return {
        "tasks_compared": len(comparable_rows),
        "avg_raw_error": round(avg_raw_error, 2),
        "avg_adjusted_error": round(avg_adjusted_error, 2),
        "adjusted_better_count": adjusted_better_count,
        "raw_better_count": raw_better_count,
        "equal_count": equal_count
    }