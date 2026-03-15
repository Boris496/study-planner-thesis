import psycopg2
import streamlit as st
from datetime import datetime


# -----------------------------
# Database connection
# -----------------------------
def get_connection():
    return psycopg2.connect(st.secrets["database_url"])


# -----------------------------
# Initialize database
# -----------------------------
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id SERIAL PRIMARY KEY,
            student_id TEXT NOT NULL,
            task_name TEXT NOT NULL,
            task_type TEXT NOT NULL,
            importance_level TEXT NOT NULL,
            deadline DATE NOT NULL,
            estimated_hours DOUBLE PRECISION NOT NULL,
            adjusted_hours DOUBLE PRECISION NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned',
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            history_id SERIAL PRIMARY KEY,
            task_id INTEGER NOT NULL,
            student_id TEXT NOT NULL,
            task_name TEXT NOT NULL,
            task_type TEXT NOT NULL,
            importance_level TEXT NOT NULL,
            estimated_hours DOUBLE PRECISION NOT NULL,
            adjusted_hours DOUBLE PRECISION NOT NULL,
            actual_hours DOUBLE PRECISION NOT NULL,
            completed BOOLEAN NOT NULL,
            remaining_hours DOUBLE PRECISION NOT NULL DEFAULT 0,
            logged_at TIMESTAMP NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS availability (
            student_id TEXT NOT NULL,
            study_date DATE NOT NULL,
            available_hours DOUBLE PRECISION NOT NULL,
            PRIMARY KEY (student_id, study_date),
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_plan (
            plan_id SERIAL PRIMARY KEY,
            student_id TEXT NOT NULL,
            task_id INTEGER NOT NULL,
            study_date DATE NOT NULL,
            planned_hours DOUBLE PRECISION NOT NULL,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

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
        """, ("admin", "admin123"))

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
        SELECT student_id, name
        FROM students
        WHERE student_id = %s
    """, (student_id,))

    student = cursor.fetchone()
    cursor.close()
    conn.close()
    return student


def create_student(student_id: str, name: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO students (student_id, name)
        VALUES (%s, %s)
    """, (student_id, name))

    conn.commit()
    cursor.close()
    conn.close()


def get_all_students():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT student_id, name
        FROM students
        ORDER BY student_id ASC
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


# -----------------------------
# Task functions
# -----------------------------
def add_task(
    student_id: str,
    task_name: str,
    task_type: str,
    importance_level: str,
    deadline: str,
    estimated_hours: float,
    adjusted_hours: float
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tasks (
            student_id,
            task_name,
            task_type,
            importance_level,
            deadline,
            estimated_hours,
            adjusted_hours,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'planned')
    """, (
        student_id,
        task_name,
        task_type,
        importance_level,
        deadline,
        estimated_hours,
        adjusted_hours
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
            task_type,
            importance_level,
            TO_CHAR(deadline, 'YYYY-MM-DD') AS deadline,
            estimated_hours,
            adjusted_hours,
            status
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
            task_type,
            importance_level,
            TO_CHAR(deadline, 'YYYY-MM-DD') AS deadline,
            estimated_hours,
            adjusted_hours,
            status
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
            task_type,
            importance_level,
            TO_CHAR(deadline, 'YYYY-MM-DD') AS deadline,
            estimated_hours,
            adjusted_hours,
            status
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
        DELETE FROM tasks
        WHERE student_id = %s
    """, (student_id,))

    cursor.execute("""
        DELETE FROM study_plan
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
    task_type: str,
    importance_level: str,
    estimated_hours: float,
    adjusted_hours: float,
    actual_hours: float,
    completed: bool,
    remaining_hours: float,
    logged_at: str
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO task_history (
            task_id,
            student_id,
            task_name,
            task_type,
            importance_level,
            estimated_hours,
            adjusted_hours,
            actual_hours,
            completed,
            remaining_hours,
            logged_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        task_id,
        student_id,
        task_name,
        task_type,
        importance_level,
        estimated_hours,
        adjusted_hours,
        actual_hours,
        completed,
        remaining_hours,
        logged_at
    ))

    if completed:
        cursor.execute("""
            UPDATE tasks
            SET status = 'completed'
            WHERE task_id = %s
        """, (task_id,))
    else:
        if remaining_hours > 0:
            cursor.execute("""
                UPDATE tasks
                SET adjusted_hours = %s, status = 'planned'
                WHERE task_id = %s
            """, (remaining_hours, task_id))
        else:
            cursor.execute("""
                UPDATE tasks
                SET status = 'incomplete'
                WHERE task_id = %s
            """, (task_id,))

    conn.commit()
    cursor.close()
    conn.close()


# -----------------------------
# History
# -----------------------------
def get_history_for_student(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            history_id,
            task_name,
            task_type,
            importance_level,
            estimated_hours,
            adjusted_hours,
            actual_hours,
            completed,
            remaining_hours,
            TO_CHAR(logged_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS logged_at
        FROM task_history
        WHERE student_id = %s
        ORDER BY logged_at DESC
    """, (student_id,))

    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return history


# -----------------------------
# Personal learning factor
# -----------------------------
def get_personal_factor(student_id: str, task_type: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            estimated_hours,
            actual_hours,
            remaining_hours
        FROM task_history
        WHERE student_id = %s
          AND task_type = %s
    """, (student_id, task_type))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return 1.0

    ratios = []

    for estimated_hours, actual_hours, remaining_hours in rows:
        if estimated_hours and estimated_hours > 0:
            total_needed = actual_hours + remaining_hours
            ratio = total_needed / estimated_hours
            ratios.append(ratio)

    if not ratios:
        return 1.0

    return round(sum(ratios) / len(ratios), 2)


# -----------------------------
# Availability
# -----------------------------
def upsert_availability(student_id: str, study_date: str, available_hours: float):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO availability (
            student_id,
            study_date,
            available_hours
        )
        VALUES (%s, %s, %s)
        ON CONFLICT (student_id, study_date)
        DO UPDATE SET available_hours = EXCLUDED.available_hours
    """, (
        student_id,
        study_date,
        available_hours
    ))

    conn.commit()
    cursor.close()
    conn.close()


def get_availability_for_range(student_id: str, start_date: str, end_date: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            TO_CHAR(study_date, 'YYYY-MM-DD') AS study_date,
            available_hours
        FROM availability
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


def delete_availability(student_id: str, study_date: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM availability
        WHERE student_id = %s
          AND study_date = %s
    """, (student_id, study_date))

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
                    planned_hours,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                student_id,
                task["task_id"],
                study_date,
                task["hours"],
                created_at
            ))

    conn.commit()
    cursor.close()
    conn.close()


def get_saved_study_plan(student_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            sp.plan_id,
            TO_CHAR(sp.study_date, 'YYYY-MM-DD') AS study_date,
            sp.task_id,
            t.task_name,
            t.task_type,
            t.importance_level,
            sp.planned_hours,
            TO_CHAR(sp.created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS created_at
        FROM study_plan sp
        LEFT JOIN tasks t ON sp.task_id = t.task_id
        WHERE sp.student_id = %s
        ORDER BY sp.study_date ASC, sp.plan_id ASC
    """, (student_id,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


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

        actual_total_hours = float(total_actual_hours) + float(latest_remaining_hours)

        if actual_total_hours == 0:
            student_error = 0.0
            system_error = 0.0
            winner = "No feedback yet"
        else:
            student_error = abs(actual_total_hours - float(estimated_hours))
            system_error = abs(actual_total_hours - float(adjusted_hours))

            if system_error < student_error:
                winner = "System"
            elif student_error < system_error:
                winner = "Student"
            else:
                winner = "Equal"

        results.append({
            "task_id": task_id,
            "task_name": task_name,
            "task_type": task_type,
            "importance_level": importance_level,
            "status": status,
            "estimated_hours": float(estimated_hours),
            "adjusted_hours": float(adjusted_hours),
            "actual_total_hours": round(actual_total_hours, 2),
            "student_error": round(student_error, 2),
            "system_error": round(system_error, 2),
            "winner": winner
        })

    return results


def get_estimation_accuracy_summary(student_id: str):
    rows = get_estimation_accuracy_for_student(student_id)

    comparable_rows = [
        row for row in rows
        if row["actual_total_hours"] > 0
    ]

    if not comparable_rows:
        return {
            "total_tasks_compared": 0,
            "system_wins": 0,
            "student_wins": 0,
            "equal": 0,
            "avg_student_error": 0.0,
            "avg_system_error": 0.0
        }

    system_wins = sum(1 for row in comparable_rows if row["winner"] == "System")
    student_wins = sum(1 for row in comparable_rows if row["winner"] == "Student")
    equal = sum(1 for row in comparable_rows if row["winner"] == "Equal")

    avg_student_error = sum(row["student_error"] for row in comparable_rows) / len(comparable_rows)
    avg_system_error = sum(row["system_error"] for row in comparable_rows) / len(comparable_rows)

    return {
        "total_tasks_compared": len(comparable_rows),
        "system_wins": system_wins,
        "student_wins": student_wins,
        "equal": equal,
        "avg_student_error": round(avg_student_error, 2),
        "avg_system_error": round(avg_system_error, 2)
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

        actual_total_hours = float(total_actual_hours) + float(latest_remaining_hours)

        if actual_total_hours == 0:
            student_error = 0.0
            system_error = 0.0
            winner = "No feedback yet"
        else:
            student_error = abs(actual_total_hours - float(estimated_hours))
            system_error = abs(actual_total_hours - float(adjusted_hours))

            if system_error < student_error:
                winner = "System"
            elif student_error < system_error:
                winner = "Student"
            else:
                winner = "Equal"

        results.append({
            "student_id": student_id,
            "student_name": student_name,
            "task_id": task_id,
            "task_name": task_name,
            "task_type": task_type,
            "importance_level": importance_level,
            "status": status,
            "estimated_hours": float(estimated_hours),
            "adjusted_hours": float(adjusted_hours),
            "actual_total_hours": round(actual_total_hours, 2),
            "student_error": round(student_error, 2),
            "system_error": round(system_error, 2),
            "winner": winner
        })

    return results


def get_admin_summary_per_student():
    rows = get_estimation_accuracy_for_all_students()

    summary = {}

    for row in rows:
        if row["actual_total_hours"] <= 0:
            continue

        student_id = row["student_id"]
        student_name = row["student_name"]

        if student_id not in summary:
            summary[student_id] = {
                "student_name": student_name,
                "tasks_compared": 0,
                "system_wins": 0,
                "student_wins": 0,
                "equal": 0,
                "total_student_error": 0.0,
                "total_system_error": 0.0
            }

        summary[student_id]["tasks_compared"] += 1
        summary[student_id]["total_student_error"] += row["student_error"]
        summary[student_id]["total_system_error"] += row["system_error"]

        if row["winner"] == "System":
            summary[student_id]["system_wins"] += 1
        elif row["winner"] == "Student":
            summary[student_id]["student_wins"] += 1
        elif row["winner"] == "Equal":
            summary[student_id]["equal"] += 1

    result = []

    for student_id, data in summary.items():
        tasks_compared = data["tasks_compared"]

        result.append({
            "student_id": student_id,
            "student_name": data["student_name"],
            "tasks_compared": tasks_compared,
            "system_wins": data["system_wins"],
            "student_wins": data["student_wins"],
            "equal": data["equal"],
            "avg_student_error": round(data["total_student_error"] / tasks_compared, 2),
            "avg_system_error": round(data["total_system_error"] / tasks_compared, 2)
        })

    result.sort(key=lambda x: x["student_id"])
    return result


def get_admin_global_summary():
    rows = get_estimation_accuracy_for_all_students()
    comparable_rows = [row for row in rows if row["actual_total_hours"] > 0]

    if not comparable_rows:
        return {
            "students_with_feedback": 0,
            "tasks_compared": 0,
            "system_wins": 0,
            "student_wins": 0,
            "equal": 0,
            "avg_student_error": 0.0,
            "avg_system_error": 0.0
        }

    unique_students = len(set(row["student_id"] for row in comparable_rows))
    system_wins = sum(1 for row in comparable_rows if row["winner"] == "System")
    student_wins = sum(1 for row in comparable_rows if row["winner"] == "Student")
    equal = sum(1 for row in comparable_rows if row["winner"] == "Equal")

    avg_student_error = sum(row["student_error"] for row in comparable_rows) / len(comparable_rows)
    avg_system_error = sum(row["system_error"] for row in comparable_rows) / len(comparable_rows)

    return {
        "students_with_feedback": unique_students,
        "tasks_compared": len(comparable_rows),
        "system_wins": system_wins,
        "student_wins": student_wins,
        "equal": equal,
        "avg_student_error": round(avg_student_error, 2),
        "avg_system_error": round(avg_system_error, 2)
    }