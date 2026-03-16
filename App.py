import streamlit as st
from datetime import date, datetime, timedelta

from Database import (
    init_db,
    get_student,
    create_student,
    get_tasks_for_student,
    get_task_by_id,
    delete_task,
    delete_all_tasks,
    add_task,
    get_personal_factor,
    log_task_feedback,
    get_history_for_student,
    upsert_availability,
    get_availability_for_range,
    delete_availability,
    save_study_plan,
    get_saved_study_plan,
    get_admin,
    get_all_students,
    get_estimation_accuracy_for_student,
    get_estimation_accuracy_summary,
    get_admin_summary_per_student,
    get_admin_global_summary
)
from Planner import build_study_plan
from LLM_helper import generate_plan_feedback


st.set_page_config(page_title="Personalized Study Planner", layout="wide")
init_db()


# -----------------------------
# Session state
# -----------------------------
if "student_id" not in st.session_state:
    st.session_state.student_id = None

if "student_name" not in st.session_state:
    st.session_state.student_name = None

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if "admin_username" not in st.session_state:
    st.session_state.admin_username = None

if "generated_plan" not in st.session_state:
    st.session_state.generated_plan = None

if "ai_study_advice" not in st.session_state:
    st.session_state.ai_study_advice = None


# -----------------------------
# Helpers
# -----------------------------
def logout_student():
    st.session_state.student_id = None
    st.session_state.student_name = None
    st.session_state.generated_plan = None
    st.session_state.ai_study_advice = None


def logout_admin():
    st.session_state.admin_logged_in = False
    st.session_state.admin_username = None


def render_student_dashboard_home(student_id: str, student_name: str):
    st.title("Personalized Workload-Aware Study Planner")
    st.subheader(f"Welcome, {student_name} ({student_id})")

    tasks = get_tasks_for_student(student_id)
    saved_plan = get_saved_study_plan(student_id)
    history = get_history_for_student(student_id)

    total_tasks = len(tasks)
    planned_tasks = len([t for t in tasks if t[7] == "planned"])
    completed_tasks = len([t for t in tasks if t[7] == "completed"])

    next_deadline = None
    future_tasks = [t for t in tasks if t[7] != "completed"]
    if future_tasks:
        next_deadline = min(t[4] for t in future_tasks)

    total_saved_plan_hours = sum(row[6] for row in saved_plan) if saved_plan else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total tasks", total_tasks)
    col2.metric("Planned tasks", planned_tasks)
    col3.metric("Completed tasks", completed_tasks)
    col4.metric("Saved planned hours", round(total_saved_plan_hours, 2))

    st.markdown("---")

    if next_deadline:
        st.info(f"Next upcoming deadline: {next_deadline}")
    else:
        st.success("No upcoming deadlines.")

    st.markdown("### Current tasks")
    if tasks:
        for task in tasks[:5]:
            st.write(
                f"- **{task[1]}** | {task[2]} | {task[3]} | deadline: {task[4]} | status: {task[7]}"
            )
    else:
        st.info("No tasks yet.")

    st.markdown("---")
    st.markdown("### Task management")

    if tasks:
        st.write("Select one or more tasks to delete:")

        selected_task_ids = []

        for task in tasks:
            task_id, name, ttype, importance, dl, est, adj, status = task
            checkbox_label = (
                f"{name} | {ttype} | {importance} | deadline: {dl} | status: {status}"
            )
            checked = st.checkbox(checkbox_label, key=f"dashboard_delete_task_{task_id}")
            if checked:
                selected_task_ids.append(task_id)

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("Delete selected tasks"):
                if selected_task_ids:
                    for task_id in selected_task_ids:
                        delete_task(task_id)
                    st.success(f"{len(selected_task_ids)} selected task(s) deleted.")
                    st.rerun()
                else:
                    st.warning("Please select at least one task to delete.")

        with col_b:
            confirm_clear_all = st.checkbox(
                "I understand that this will delete all tasks",
                key="confirm_clear_all_tasks"
            )

            if st.button("Clear all tasks"):
                if confirm_clear_all:
                    delete_all_tasks(student_id)
                    st.success("All tasks deleted.")
                    st.rerun()
                else:
                    st.warning("Please confirm that you want to delete all tasks.")
    else:
        st.info("There are no tasks to delete.")

    st.markdown("---")
    st.markdown("### Recent feedback")
    if history:
        for row in history[:5]:
            st.write(
                f"- **{row[1]}** | actual: {row[6]}h | completed: {'Yes' if row[7] else 'No'} | logged: {row[9]}"
            )
    else:
        st.info("No feedback logged yet.")


def render_planning_setup_page(student_id: str):
    st.title("Planning Setup")

    section = st.radio(
        "Choose setup section",
        ["Task Setup", "Availability Setup", "Generate Study Plan"],
        horizontal=True
    )

    # -----------------------------
    # Task Setup
    # -----------------------------
    if section == "Task Setup":
        st.subheader("Add Task")

        task_name = st.text_input("Task name")
        task_type = st.selectbox(
            "Task type",
            ["Reading", "Practice", "Writing", "Review", "Administrative"]
        )
        importance_level = st.selectbox("Importance level", ["High", "Medium", "Low"])
        deadline = st.date_input("Deadline", value=date.today() + timedelta(days=7))
        estimated_hours = st.number_input(
            "Estimated hours",
            min_value=0.5,
            max_value=200.0,
            value=2.0,
            step=0.5
        )

        personal_factor = get_personal_factor(student_id, task_type)
        adjusted_hours_preview = round(estimated_hours * personal_factor, 2)

        st.info(f"Personal factor for {task_type}: {personal_factor}")
        st.info(f"Adjusted hours prediction: {adjusted_hours_preview}")

        if st.button("Add Task"):
            if task_name.strip():
                add_task(
                    student_id=student_id,
                    task_name=task_name.strip(),
                    task_type=task_type,
                    importance_level=importance_level,
                    deadline=deadline.isoformat(),
                    estimated_hours=float(estimated_hours),
                    adjusted_hours=float(adjusted_hours_preview)
                )
                st.success("Task added successfully.")
                st.rerun()
            else:
                st.warning("Please enter a task name.")

        st.markdown("---")
        st.subheader("Current Tasks")

        tasks = get_tasks_for_student(student_id)

        if tasks:
            for task in tasks:
                task_id, name, ttype, importance, dl, est, adj, status = task
                st.markdown("---")
                st.write(f"**Task ID:** {task_id}")
                st.write(f"**Task name:** {name}")
                st.write(f"Task type: {ttype}")
                st.write(f"Importance: {importance}")
                st.write(f"Deadline: {dl}")
                st.write(f"Estimated hours: {est}")
                st.write(f"Adjusted hours: {adj}")
                st.write(f"Status: {status}")
        else:
            st.info("No tasks found.")

    # -----------------------------
    # Availability Setup
    # -----------------------------
    elif section == "Availability Setup":
        st.subheader("Set Study Availability")

        availability_date = st.date_input(
            "Study date",
            value=date.today(),
            key="availability_date"
        )
        available_hours = st.number_input(
            "Available study hours",
            min_value=0.0,
            max_value=24.0,
            value=2.0,
            step=0.5,
            key="available_hours_input"
        )

        if st.button("Save Availability"):
            upsert_availability(student_id, availability_date.isoformat(), float(available_hours))
            st.success("Availability saved.")
            st.rerun()

        st.markdown("---")
        st.subheader("Quick fill next 7 days")
        st.caption(
            "This will save the same number of available study hours for today and the next 6 days."
        )

        quick_hours = st.number_input(
            "Same available hours per day",
            min_value=0.0,
            max_value=24.0,
            value=2.0,
            step=0.5,
            key="quick_fill_hours"
        )

        if st.button("Apply to next 7 days"):
            for i in range(7):
                d = date.today() + timedelta(days=i)
                upsert_availability(student_id, d.isoformat(), float(quick_hours))
            st.success("Availability saved for the next 7 days.")
            st.rerun()

        st.markdown("---")
        st.subheader("Saved availability")

        availability_rows = get_availability_for_range(
            student_id,
            date.today().isoformat(),
            (date.today() + timedelta(days=30)).isoformat()
        )

        if availability_rows:
            selected_dates_to_delete = []

            for study_date, hours in availability_rows:
                col1, col2 = st.columns([4, 1])

                with col1:
                    checked = st.checkbox(
                        f"{study_date} → {hours} hours",
                        key=f"availability_checkbox_{study_date}"
                    )
                    if checked:
                        selected_dates_to_delete.append(study_date)

                with col2:
                    if st.button("Delete", key=f"delete_availability_{study_date}"):
                        delete_availability(student_id, study_date)
                        st.success(f"Availability for {study_date} deleted.")
                        st.rerun()

            st.markdown("---")
            confirm_delete_selected = st.checkbox(
                "I understand that selected availability dates will be deleted",
                key="confirm_delete_selected_availability"
            )

            if st.button("Delete selected availability"):
                if not selected_dates_to_delete:
                    st.warning("Please select at least one availability date.")
                elif not confirm_delete_selected:
                    st.warning("Please confirm deletion of selected availability dates.")
                else:
                    for study_date in selected_dates_to_delete:
                        delete_availability(student_id, study_date)
                    st.success(f"{len(selected_dates_to_delete)} availability date(s) deleted.")
                    st.rerun()
        else:
            st.info("No availability has been saved yet.")

    # -----------------------------
    # Generate Study Plan
    # -----------------------------
    elif section == "Generate Study Plan":
        st.subheader("Generate Study Plan")

        if st.button("Build Study Plan"):
            plan_result = build_study_plan(student_id)
            st.session_state.generated_plan = plan_result
            st.session_state.ai_study_advice = None

        plan_result = st.session_state.generated_plan

        if plan_result:
            daily_plan = plan_result["daily_plan"]
            unscheduled_tasks = plan_result["unscheduled_tasks"]
            total_required_hours = plan_result["total_required_hours"]
            total_available_hours = plan_result["total_available_hours"]

            st.write(f"**Planning start:** {plan_result['planning_start']}")
            st.write(f"**Planning end:** {plan_result['planning_end']}")
            st.write(f"**Total required hours:** {total_required_hours}")
            st.write(f"**Total available hours:** {total_available_hours}")

            if total_required_hours > total_available_hours:
                st.warning(
                    f"⚠ You scheduled {total_required_hours} hours but only "
                    f"{total_available_hours} hours are available before the deadline."
                )
            else:
                st.success("Workload appears feasible within current availability.")

            st.markdown("---")
            st.subheader("Generated Plan")

            if daily_plan:
                for study_day, items in daily_plan.items():
                    st.write(f"### {study_day}")
                    for item in items:
                        st.write(
                            f"- {item['task_name']} ({item['task_type']}, "
                            f"{item['importance_level']}) — {item['hours']}h "
                            f"(deadline: {item['deadline']})"
                        )
            else:
                st.info("No study plan could be generated.")

            if unscheduled_tasks:
                st.markdown("---")
                st.subheader("Unscheduled Task Hours")
                for item in unscheduled_tasks:
                    st.write(
                        f"- {item['task_name']} — remaining {item['remaining_hours']}h "
                        f"(deadline: {item['deadline']}, importance: {item['importance_level']})"
                    )

            st.markdown("---")
            if st.button("Generate AI Study Advice"):
                with st.spinner("Generating AI study advice..."):
                    advice = generate_plan_feedback(
                        student_name=st.session_state.student_name,
                        plan_result=plan_result
                    )
                    st.session_state.ai_study_advice = advice

            if st.session_state.ai_study_advice:
                st.subheader("AI Study Advice")
                st.write(st.session_state.ai_study_advice)

            if daily_plan and st.button("Save Generated Study Plan"):
                save_study_plan(student_id, daily_plan)
                st.success("Study plan saved to database.")
        else:
            st.info("Click 'Build Study Plan' to generate a new plan.")


def render_saved_plan_page(student_id: str):
    st.title("Saved Study Plan")

    saved_plan = get_saved_study_plan(student_id)

    if saved_plan:
        grouped = {}
        created_at_value = None

        for row in saved_plan:
            _, study_date, task_id, task_name, task_type, importance_level, planned_hours, created_at = row
            created_at_value = created_at
            grouped.setdefault(study_date, []).append({
                "task_id": task_id,
                "task_name": task_name,
                "task_type": task_type,
                "importance_level": importance_level,
                "planned_hours": planned_hours
            })

        if created_at_value:
            st.caption(f"Plan created at: {created_at_value}")

        for study_date, items in grouped.items():
            st.write(f"### {study_date}")
            for item in items:
                st.write(
                    f"- {item['task_name']} ({item['task_type']}, {item['importance_level']}) "
                    f"— {item['planned_hours']}h"
                )
    else:
        st.info("No saved study plan found.")


def render_feedback_page(student_id: str):
    st.title("Task Feedback")

    tasks = get_tasks_for_student(student_id)
    active_tasks = [t for t in tasks if t[7] != "completed"]

    if active_tasks:
        task_options = {
            f"{task[0]} - {task[1]} ({task[7]})": task[0]
            for task in active_tasks
        }

        selected_task_label = st.selectbox("Select task", list(task_options.keys()))
        selected_task_id = task_options[selected_task_label]

        task = get_task_by_id(selected_task_id)

        if task:
            (
                task_id,
                task_student_id,
                task_name,
                task_type,
                importance_level,
                deadline,
                estimated_hours,
                adjusted_hours,
                status
            ) = task

            st.write(f"**Task:** {task_name}")
            st.write(f"Task type: {task_type}")
            st.write(f"Importance: {importance_level}")
            st.write(f"Estimated hours: {estimated_hours}")
            st.write(f"Adjusted hours: {adjusted_hours}")
            st.write(f"Status: {status}")

            actual_hours = st.number_input(
                "Actual hours worked",
                min_value=0.0,
                max_value=200.0,
                value=1.0,
                step=0.5,
                key=f"actual_hours_{task_id}"
            )

            completed = st.checkbox("Completed?", key=f"completed_{task_id}")

            remaining_hours = 0.0
            if not completed:
                remaining_hours = st.number_input(
                    "Remaining hours",
                    min_value=0.0,
                    max_value=200.0,
                    value=0.0,
                    step=0.5,
                    key=f"remaining_hours_{task_id}"
                )

            if st.button("Submit Feedback"):
                log_task_feedback(
                    task_id=task_id,
                    student_id=task_student_id,
                    task_name=task_name,
                    task_type=task_type,
                    importance_level=importance_level,
                    estimated_hours=float(estimated_hours),
                    adjusted_hours=float(adjusted_hours),
                    actual_hours=float(actual_hours),
                    completed=completed,
                    remaining_hours=float(remaining_hours),
                    logged_at=datetime.now().isoformat()
                )
                st.success("Feedback logged successfully.")
                st.rerun()
    else:
        st.info("No active tasks available for feedback.")


def render_history_page(student_id: str):
    st.title("Task History")

    history = get_history_for_student(student_id)

    if history:
        for row in history:
            (
                history_id,
                task_name,
                task_type,
                importance_level,
                estimated_hours,
                adjusted_hours,
                actual_hours,
                completed,
                remaining_hours,
                logged_at
            ) = row

            st.markdown("---")
            st.write(f"**Task:** {task_name}")
            st.write(f"Task type: {task_type}")
            st.write(f"Importance: {importance_level}")
            st.write(f"Estimated hours: {estimated_hours}")
            st.write(f"Adjusted hours: {adjusted_hours}")
            st.write(f"Actual hours: {actual_hours}")
            st.write(f"Completed: {'Yes' if completed else 'No'}")
            st.write(f"Remaining hours: {remaining_hours}")
            st.write(f"Logged at: {logged_at}")
    else:
        st.info("No task history available.")


def render_admin_dashboard():
    st.title("Admin Dashboard")

    global_summary = get_admin_global_summary()
    per_student_summary = get_admin_summary_per_student()
    students = get_all_students()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registered students", len(students))
    col2.metric("Students with feedback", global_summary["students_with_feedback"])
    col3.metric("Tasks compared", global_summary["tasks_compared"])
    col4.metric("System wins", global_summary["system_wins"])

    st.markdown("---")
    st.write(f"Student wins: {global_summary['student_wins']}")
    st.write(f"Equal: {global_summary['equal']}")
    st.write(f"Average student error: {global_summary['avg_student_error']} h")
    st.write(f"Average system error: {global_summary['avg_system_error']} h")

    st.markdown("## Per Student Summary")
    if per_student_summary:
        for row in per_student_summary:
            st.markdown("---")
            st.write(f"**Student:** {row['student_name']} ({row['student_id']})")
            st.write(f"Tasks compared: {row['tasks_compared']}")
            st.write(f"System wins: {row['system_wins']}")
            st.write(f"Student wins: {row['student_wins']}")
            st.write(f"Equal: {row['equal']}")
            st.write(f"Average student error: {row['avg_student_error']} h")
            st.write(f"Average system error: {row['avg_system_error']} h")
    else:
        st.info("No student feedback data available yet.")


def render_admin_detailed_page():
    st.title("Detailed Accuracy Comparison")

    students = get_all_students()

    if not students:
        st.info("No students registered yet.")
        return

    student_options = [f"{student_id} - {name}" for student_id, name in students]
    selected_student = st.selectbox("Select student", student_options)
    selected_student_id = selected_student.split(" - ")[0]

    selected_summary = get_estimation_accuracy_summary(selected_student_id)
    selected_rows = get_estimation_accuracy_for_student(selected_student_id)

    st.write(f"**Tasks compared:** {selected_summary['total_tasks_compared']}")
    st.write(f"**System wins:** {selected_summary['system_wins']}")
    st.write(f"**Student wins:** {selected_summary['student_wins']}")
    st.write(f"**Equal:** {selected_summary['equal']}")
    st.write(f"**Average student error:** {selected_summary['avg_student_error']} h")
    st.write(f"**Average system error:** {selected_summary['avg_system_error']} h")

    if selected_rows:
        for row in selected_rows:
            st.markdown("---")
            st.write(f"**Task:** {row['task_name']}")
            st.write(f"Task type: {row['task_type']}")
            st.write(f"Importance: {row['importance_level']}")
            st.write(f"Status: {row['status']}")
            st.write(f"Student estimate: {row['estimated_hours']} h")
            st.write(f"System estimate: {row['adjusted_hours']} h")
            st.write(f"Actual needed: {row['actual_total_hours']} h")
            st.write(f"Student error: {row['student_error']} h")
            st.write(f"System error: {row['system_error']} h")
            st.write(f"Closer prediction: **{row['winner']}**")
    else:
        st.info("No task data available for this student.")


# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("Navigation")
mode = st.sidebar.radio("Role", ["Student", "Admin"])

if mode == "Student":
    if st.session_state.student_id is None:
        st.title("Student Login")

        login_tab, register_tab = st.tabs(["Load Existing Account", "Create New Account"])

        with login_tab:
            existing_student_id = st.text_input("Student ID")
            if st.button("Load Account"):
                student = get_student(existing_student_id.strip())
                if student:
                    st.session_state.student_id = student[0]
                    st.session_state.student_name = student[1]
                    st.success("Student account loaded.")
                    st.rerun()
                else:
                    st.error("Student not found.")

        with register_tab:
            new_student_id = st.text_input("New student ID")
            new_student_name = st.text_input("Name")

            if st.button("Create Student Account"):
                if new_student_id.strip() and new_student_name.strip():
                    existing = get_student(new_student_id.strip())
                    if existing:
                        st.warning("A student with this ID already exists.")
                    else:
                        create_student(new_student_id.strip(), new_student_name.strip())
                        st.success("Student account created. You can now load it.")
                else:
                    st.warning("Please enter both student ID and name.")
    else:
        st.sidebar.success(f"Student: {st.session_state.student_name}")
        if st.sidebar.button("Logout Student"):
            logout_student()
            st.rerun()

        student_page = st.sidebar.radio(
            "Student menu",
            ["Dashboard", "Planning Setup", "Saved Plan", "Feedback", "History"]
        )

        if student_page == "Dashboard":
            render_student_dashboard_home(st.session_state.student_id, st.session_state.student_name)
        elif student_page == "Planning Setup":
            render_planning_setup_page(st.session_state.student_id)
        elif student_page == "Saved Plan":
            render_saved_plan_page(st.session_state.student_id)
        elif student_page == "Feedback":
            render_feedback_page(st.session_state.student_id)
        elif student_page == "History":
            render_history_page(st.session_state.student_id)

elif mode == "Admin":
    if not st.session_state.admin_logged_in:
        st.title("Admin Login")

        admin_username = st.text_input("Admin username")
        admin_password = st.text_input("Admin password", type="password")

        if st.button("Login as Admin"):
            admin = get_admin(admin_username.strip(), admin_password)
            if admin:
                st.session_state.admin_logged_in = True
                st.session_state.admin_username = admin[1]
                st.success("Admin login successful.")
                st.rerun()
            else:
                st.error("Invalid admin credentials.")
    else:
        st.sidebar.success(f"Admin: {st.session_state.admin_username}")
        if st.sidebar.button("Logout Admin"):
            logout_admin()
            st.rerun()

        admin_page = st.sidebar.radio(
            "Admin menu",
            ["Admin Dashboard", "Detailed Accuracy"]
        )

        if admin_page == "Admin Dashboard":
            render_admin_dashboard()
        elif admin_page == "Detailed Accuracy":
            render_admin_detailed_page()