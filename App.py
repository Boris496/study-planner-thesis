
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from streamlit_calendar import calendar

from Database import (
    get_student,
    create_student,
    get_tasks_for_student,
    get_task_by_id,
    delete_task,
    add_task,
    log_task_feedback,
    get_history_for_student,
    get_task_learning_rows,
    save_study_plan,
    get_saved_study_plan,
    get_admin,
    get_all_students,
    get_estimation_accuracy_for_student,
    get_estimation_accuracy_summary,
    get_admin_summary_per_student,
    get_admin_global_summary,
    get_subject_analysis,
    deactivate_student,
    activate_student,
    delete_student_account,
    add_activity_slot,
    get_activity_slots_for_range,
    delete_activity_slot,
    upsert_day_preference,
    get_day_preferences_for_range,
    delete_day_preference,
    save_ai_feedback_reflection,
    get_ai_feedback_reflections,
    get_task_type_analysis,
    get_all_learning_profiles,
    get_learning_profile_for_student,
    add_subject,
    get_subjects_for_student,
    delete_subject,
    get_due_feedback_tasks,
    save_ai_learning_preference,
    get_ai_learning_preferences_for_student,
    get_ai_learning_preferences_for_task,
    update_task,
    update_activity_slot,
    mark_onboarding_seen,
    save_ai_reflection_summary,
    get_ai_reflection_summaries_for_student,

)

from Planner import build_study_plan
from LLM_helper import (
    build_student_context,
    chat_with_study_coach,
    chat_with_system_guide,
    check_reflection_completion,
    generate_learning_preference_proposal,
    generate_feedback_reflection,
    generate_reflection_summary,
)

st.set_page_config(page_title="Personalized Study Planner", layout="wide")

# Database bestaat al, dus niet steeds opnieuw initialiseren
# init_db()


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

if "llm_chat_history" not in st.session_state:
    st.session_state.llm_chat_history = []

if "system_help_chat" not in st.session_state:
    st.session_state.system_help_chat = []

if "feedback_reflection_task_id" not in st.session_state:
    st.session_state.feedback_reflection_task_id = None

if "pending_ai_preference_proposal" not in st.session_state:
    st.session_state.pending_ai_preference_proposal = None

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
.block-card {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 12px;
    color: #0f172a;
}
.soft-card {
    background-color: #ffffff;
    border: 1px solid #dbeafe;
    border-radius: 14px;
    padding: 14px;
    margin-bottom: 10px;
    color: #0f172a;
}
.metric-card {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 14px;
    padding: 12px 16px;
    margin-bottom: 10px;
    color: #0f172a;
}
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    margin-right: 6px;
}
.badge-high {
    background-color: #fee2e2;
    color: #b91c1c;
}
.badge-medium {
    background-color: #fef3c7;
    color: #b45309;
}
.badge-low {
    background-color: #dcfce7;
    color: #15803d;
}
.badge-planned {
    background-color: #dbeafe;
    color: #1d4ed8;
}
.badge-completed {
    background-color: #dcfce7;
    color: #15803d;
}
.badge-incomplete {
    background-color: #ffedd5;
    color: #c2410c;
}
.badge-active {
    background-color: #dcfce7;
    color: #15803d;
}
.badge-inactive {
    background-color: #fee2e2;
    color: #b91c1c;
}
.legend-item {
    display: inline-block;
    margin-right: 16px;
    margin-bottom: 8px;
    color: #0f172a;
}
.legend-dot {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 999px;
    margin-right: 6px;
}
.small-muted {
    color: #475569;
    font-size: 0.92rem;
}
</style>
""", unsafe_allow_html=True)


# -----------------------------
# Helpers
# -----------------------------
def logout_student():
    st.session_state.student_id = None
    st.session_state.student_name = None
    st.session_state.generated_plan = None
    st.session_state.ai_study_advice = None
    st.session_state.llm_chat_history = []
    st.session_state.system_help_chat = []


def logout_admin():
    st.session_state.admin_logged_in = False
    st.session_state.admin_username = None


def importance_to_color(importance_level: str) -> str:
    if importance_level == "High":
        return "#EF4444"
    elif importance_level == "Medium":
        return "#F59E0B"
    return "#10B981"


def importance_badge(importance_level: str) -> str:
    if importance_level == "High":
        return '<span class="badge badge-high">High</span>'
    elif importance_level == "Medium":
        return '<span class="badge badge-medium">Medium</span>'
    return '<span class="badge badge-low">Low</span>'


def intensity_badge(intensity: str) -> str:
    if intensity == "High":
        return '<span class="badge badge-high">High intensity</span>'
    elif intensity == "Medium":
        return '<span class="badge badge-medium">Medium intensity</span>'
    return '<span class="badge badge-low">Low intensity</span>'


def energy_badge(energy: str) -> str:
    if energy == "High":
        return '<span class="badge badge-completed">High energy</span>'
    elif energy == "Medium":
        return '<span class="badge badge-medium">Medium energy</span>'
    return '<span class="badge badge-incomplete">Low energy</span>'


def status_badge(status: str) -> str:
    if status == "completed":
        return '<span class="badge badge-completed">Completed</span>'
    elif status == "planned":
        return '<span class="badge badge-planned">Planned</span>'
    return '<span class="badge badge-incomplete">Incomplete</span>'


def student_active_badge(is_active: bool) -> str:
    if is_active:
        return '<span class="badge badge-active">Active</span>'
    return '<span class="badge badge-inactive">Inactive</span>'


def render_task_card(task_id, name, subject, task_type, importance, intensity, deadline, est, adj, status):
    st.markdown(
        f"""
        <div class="block-card">
            <h4 style="margin-bottom:8px;">{name}</h4>
            <div style="margin-bottom:8px;">
                {importance_badge(importance)}
                {intensity_badge(intensity)}
                {status_badge(status)}
            </div>
            <div><b>Subject:</b> {subject}</div>
            <div><b>Task type:</b> {task_type}</div>
            <div><b>Deadline:</b> {deadline}</div>
            <div><b>Estimated hours:</b> {est}</div>
            <div><b>Remaining / plannable hours:</b> {adj}</div>
            <div class="small-muted" style="margin-top:8px;">Task ID: {task_id}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_history_card(task_name, task_type, subject, importance, estimated, adjusted, actual, completed, remaining):
    completed_text = "Yes" if completed else "No"
    badge_html = importance_badge(importance)
    status_html = (
        '<span class="badge badge-completed">Completed</span>'
        if completed
        else '<span class="badge badge-incomplete">Open / Partial</span>'
    )

    st.markdown(
        f"""
          <div class="soft-card">
              <h4 style="margin-bottom:8px;">{task_name}</h4>
              <div style="margin-bottom:8px;">
                  {badge_html}
                  {status_html}
              </div>
              <div><b>Subject:</b> {subject}</div>
              <div><b>Task type:</b> {task_type}</div>
              <div><b>Estimated:</b> {estimated} h</div>
              <div><b>Remaining / plannable at that moment:</b> {adjusted} h</div>
              <div><b>Actual worked:</b> {actual} h</div>
              <div><b>Completed:</b> {completed_text}</div>
              <div><b>Remaining:</b> {remaining} h</div>
          </div>
          """,
        unsafe_allow_html=True
    )


def format_block_duration(hours: float) -> str:
    minutes = round(hours * 60)

    if minutes < 60:
        return f"{minutes} min"

    whole_hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes == 0:
        return f"{whole_hours}h"

    return f"{whole_hours}h {remaining_minutes}min"


def convert_plan_to_calendar_events(daily_plan: dict):
    events = []

    for study_day, items in daily_plan.items():
        for item in items:
            start_time = item.get("start_time")
            end_time = item.get("end_time")
            is_break = item.get("is_break", False)
            duration_label = format_block_duration(float(item["hours"]))

            if start_time and end_time:
                start_value = f"{study_day}T{start_time}:00"
                end_value = f"{study_day}T{end_time}:00"
                all_day_value = False

                if is_break:
                    event_title = "Break"
                else:
                    event_title = f"{item.get('subject', 'N/A')} | {item['task_name']} • {duration_label}"
            else:
                start_value = study_day
                end_value = study_day
                all_day_value = True

                if is_break:
                    event_title = "Break"
                else:
                    event_title = f"{item.get('subject', 'N/A')} | {item['task_name']} • {duration_label}"

            if is_break:
                event_color = "#94A3B8"
            else:
                event_color = importance_to_color(item["importance_level"])

            events.append({
                "title": event_title,
                "start": start_value,
                "end": end_value,
                "allDay": all_day_value,
                "color": event_color,
                "extendedProps": {
                    "task_id": item.get("task_id"),
                    "task_type": item.get("task_type", "N/A"),
                    "subject": item.get("subject", "N/A"),
                    "importance": item.get("importance_level", "N/A"),
                    "intensity": item.get("task_intensity", "N/A"),
                    "deadline": item.get("deadline", "N/A"),
                    "hours": item.get("hours", "N/A"),
                    "start_time": item.get("start_time", "N/A"),
                    "end_time": item.get("end_time", "N/A"),
                    "energy_level": item.get("energy_level", "N/A"),
                    "is_break": is_break
                }
            })

    return events


def remove_task_from_generated_plan(task_id: int):
    plan = st.session_state.get("generated_plan")

    if not plan:
        return

    daily_plan = plan.get("daily_plan", {})
    unscheduled_tasks = plan.get("unscheduled_tasks", [])

    updated_daily_plan = {}
    for study_day, items in daily_plan.items():
        filtered_items = [item for item in items if item["task_id"] != task_id]
        if filtered_items:
            updated_daily_plan[study_day] = filtered_items

    updated_unscheduled_tasks = [
        item for item in unscheduled_tasks if item["task_id"] != task_id
    ]

    plan["daily_plan"] = updated_daily_plan
    plan["unscheduled_tasks"] = updated_unscheduled_tasks

    planned_hours = sum(
        item["hours"]
        for items in updated_daily_plan.values()
        for item in items
    )
    unscheduled_hours = sum(
        item["remaining_hours"]
        for item in updated_unscheduled_tasks
    )

    plan["total_required_hours"] = round(planned_hours + unscheduled_hours, 2)
    st.session_state.generated_plan = plan


def compute_plan_summary(daily_plan: dict, unscheduled_tasks: list):
    unscheduled_total = round(sum(item["remaining_hours"] for item in unscheduled_tasks), 2)

    busiest_day = None
    busiest_hours = 0.0
    total_planned_hours = 0.0
    total_blocks = 0

    for study_day, items in daily_plan.items():
        day_total = round(sum(item["hours"] for item in items), 2)
        total_planned_hours += day_total
        total_blocks += len(items)
        if day_total > busiest_hours:
            busiest_hours = day_total
            busiest_day = study_day

    return {
        "unscheduled_total": unscheduled_total,
        "busiest_day": busiest_day,
        "busiest_hours": round(busiest_hours, 2),
        "total_planned_hours": round(total_planned_hours, 2),
        "total_blocks": total_blocks
    }


def compute_saved_plan_feasibility(tasks, saved_daily_plan: dict):
    planned_hours_by_task = {}

    for study_date, items in saved_daily_plan.items():
        for item in items:
            task_id = item["task_id"]
            planned_hours_by_task[task_id] = planned_hours_by_task.get(task_id, 0.0) + float(item["hours"])

    partially_planned_tasks = []
    fully_planned_tasks = 0

    for task in tasks:
        task_id, name, subject, ttype, importance, intensity, dl, est, adj, status, is_spread_learning, preferred_study_days, min_session_hours, max_session_hours = task

        if status == "completed":
            continue

        adjusted_hours = float(adj)
        planned_hours = round(planned_hours_by_task.get(task_id, 0.0), 2)
        missing_hours = round(max(adjusted_hours - planned_hours, 0.0), 2)

        if 0 < missing_hours <= 0.25:
            missing_hours = 0.0

        if missing_hours > 0:
            partially_planned_tasks.append({
                "task_id": task_id,
                "task_name": name,
                "task_type": ttype,
                "importance_level": importance,
                "task_intensity": intensity,
                "deadline": dl,
                "planned_hours": planned_hours,
                "required_hours": adjusted_hours,
                "missing_hours": missing_hours
            })
        else:
            fully_planned_tasks += 1

    return {
        "fully_planned_tasks": fully_planned_tasks,
        "partially_planned_tasks": partially_planned_tasks
    }


def get_today_and_week_stats(daily_plan: dict):
    today_str = date.today().isoformat()
    today_hours = 0.0
    today_tasks = 0

    week_start = date.today()
    week_end = week_start + timedelta(days=6)

    week_hours = 0.0
    week_tasks = 0

    for day_str, items in daily_plan.items():
        day_obj = datetime.strptime(day_str, "%Y-%m-%d").date()
        total = sum(item["hours"] for item in items)

        if day_str == today_str:
            today_hours += total
            today_tasks += len(items)

        if week_start <= day_obj <= week_end:
            week_hours += total
            week_tasks += len(items)

    return {
        "today_hours": round(today_hours, 2),
        "today_tasks": today_tasks,
        "week_hours": round(week_hours, 2),
        "week_tasks": week_tasks
    }


def get_next_deadline_from_tasks(tasks):
    future_tasks = [t for t in tasks if t[9] != "completed"]
    if not future_tasks:
        return None
    return min(t[6] for t in future_tasks)


def render_calendar_legend():
    st.markdown("### Calendar legend")
    st.markdown(
        """
        <div>
            <span class="legend-item"><span class="legend-dot" style="background:#EF4444;"></span>High priority</span>
            <span class="legend-item"><span class="legend-dot" style="background:#F59E0B;"></span>Medium priority</span>
            <span class="legend-item"><span class="legend-dot" style="background:#10B981;"></span>Low priority</span>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_plan_calendar(daily_plan: dict, calendar_key: str = "study_plan_calendar"):
    if not daily_plan:
        st.info("No study plan to display yet.")
        return

    calendar_events = convert_plan_to_calendar_events(daily_plan)
    first_plan_date = sorted(daily_plan.keys())[0]

    calendar_options = {
        "initialDate": first_plan_date,
        "initialView": "timeGridWeek",

        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,listWeek"
        },

        "height": 1200,
        "contentHeight": 1100,

        "editable": False,
        "selectable": False,
        "dayMaxEvents": True,

        "slotMinTime": "06:00:00",
        "slotMaxTime": "24:00:00",
        "slotDuration": "00:15:00",
        "expandRows": True,
        "allDaySlot": True,
        "nowIndicator": True,

        "eventTimeFormat": {
            "hour": "2-digit",
            "minute": "2-digit",
            "hour12": False
        },

        "slotLabelFormat": {
            "hour": "2-digit",
            "minute": "2-digit",
            "hour12": False
        },
    }

    calendar_state = calendar(
        events=calendar_events,
        options=calendar_options,
        custom_css="""
        .fc {
            font-size: 1rem;
        }

        .fc-toolbar-title {
            font-size: 1.8rem;
            font-weight: 800;
        }

        .fc-button {
            font-size: 0.95rem !important;
            padding: 0.55rem 0.9rem !important;
            border-radius: 8px !important;
        }

        .fc-col-header-cell-cushion {
            font-size: 1rem;
            font-weight: 700;
            padding: 8px 4px;
        }

        .fc-timegrid-slot {
            height: 50px !important;
        }

        .fc-timegrid-axis-cushion,
        .fc-timegrid-slot-label-cushion {
            font-size: 0.95rem;
            font-weight: 600;
        }

        .fc-event {
            border-radius: 10px !important;
            padding: 4px 6px !important;
            border: none !important;
            margin: 0 !important;
        }

        .fc-event-title {
            font-weight: 700 !important;
            font-size: 0.82rem !important;
            line-height: 1.15 !important;
            white-space: normal !important;
            overflow: visible !important;
        }

        .fc-event-time {
            font-size: 0.9rem !important;
            font-weight: 600 !important;
        }

        .fc-daygrid-event {
            white-space: normal !important;
            padding: 4px 6px !important;
        }

        .fc-list-event-title,
        .fc-list-event-time {
            font-size: 0.98rem;
        }
        """,
        key=calendar_key
    )

    if calendar_state:
        clicked = calendar_state.get("eventClick")
        if clicked and "event" in clicked:
            event_data = clicked["event"]
            props = event_data.get("extendedProps", {})

            st.markdown("---")
            st.subheader("Selected Study Block")

            if props.get("is_break"):
                st.markdown(
                    f"""
                    <div class="soft-card">
                        <div><b>Break:</b> Recovery moment</div>
                        <div><b>Date:</b> {event_data.get('start', 'N/A')}</div>
                        <div><b>Start time:</b> {props.get('start_time', 'N/A')}</div>
                        <div><b>End time:</b> {props.get('end_time', 'N/A')}</div>
                        <div><b>Duration:</b> {props.get('hours', 'N/A')} h</div>
                        <div><b>Energy effect:</b> {props.get('energy_level', 'N/A')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div class="soft-card">
                        <div><b>Task:</b> {event_data.get('title', 'N/A')}</div>
                        <div><b>Date:</b> {event_data.get('start', 'N/A')}</div>
                        <div><b>Start time:</b> {props.get('start_time', 'N/A')}</div>
                        <div><b>End time:</b> {props.get('end_time', 'N/A')}</div>
                        <div><b>Subject:</b> {props.get('subject', 'N/A')}</div>
                        <div><b>Task type:</b> {props.get('task_type', 'N/A')}</div>
                        <div><b>Importance:</b> {props.get('importance', 'N/A')}</div>
                        <div><b>Intensity:</b> {props.get('intensity', 'N/A')}</div>
                        <div><b>Energy level:</b> {props.get('energy_level', 'N/A')}</div>
                        <div><b>Hours:</b> {props.get('hours', 'N/A')}</div>
                        <div><b>Deadline:</b> {props.get('deadline', 'N/A')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


def render_workload_chart(daily_plan: dict):
    if not daily_plan:
        st.info("No planned workload yet.")
        return

    rows = []
    for study_day, items in daily_plan.items():
        rows.append({
            "date": study_day,
            "planned_hours": round(sum(item["hours"] for item in items), 2)
        })

    df = pd.DataFrame(rows).sort_values("date")
    st.bar_chart(df.set_index("date"))


def render_plan_details(daily_plan: dict):
    if not daily_plan:
        st.info("No plan details yet.")
        return

    for study_day, items in daily_plan.items():
        st.markdown(f"### {study_day}")
        for item in items:
            st.markdown(
                f"""
                <div class="soft-card">
                    <div style="font-weight:700; margin-bottom:6px;">{item['task_name']}</div>
                    <div>{importance_badge(item['importance_level'])}{intensity_badge(item.get('task_intensity', 'Medium'))}{energy_badge(item.get('energy_level', 'Medium'))}</div>
                    <div><b>Task type:</b> {item['task_type']}</div>
                    <div><b>Time:</b> {item.get('start_time', 'N/A')} - {item.get('end_time', 'N/A')}</div>
                    <div><b>Planned hours:</b> {item['hours']} h</div>
                    <div><b>Deadline:</b> {item['deadline']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )


def render_unscheduled_tasks(unscheduled_tasks: list):
    if not unscheduled_tasks:
        st.success("No unscheduled task hours.")
        return

    st.warning(
        "Some task hours could not be planned within the current sleep/wake window, "
        "activity setup, deadlines, or minimum session length rules."
    )

    has_short_slot_issue = any(
        item["task_type"] in ["Study / Learning", "Practice", "Writing"]
        for item in unscheduled_tasks
    )

    if has_short_slot_issue:
        st.info(
            "Some remaining free time slots may be too short for these task types. "
            "For example, Study / Learning, Practice, and Writing blocks need at least 30 minutes."
        )

    for item in unscheduled_tasks:
        st.markdown(
            f"""
            <div class="block-card">
                <div style="font-weight:700; margin-bottom:8px;">{item['task_name']}</div>
                <div>{importance_badge(item['importance_level'])}{intensity_badge(item.get('task_intensity', 'Medium'))}</div>
                <div><b>Subject:</b> {item.get('subject', 'N/A')}</div>
                <div><b>Task type:</b> {item['task_type']}</div>
                <div><b>Remaining hours:</b> {item['remaining_hours']} h</div>
                <div><b>Deadline:</b> {item['deadline']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_student_overview_cards(tasks, daily_plan):
    total_tasks = len(tasks)
    active_tasks = len([t for t in tasks if t[9] != "completed"])
    completed_tasks = len([t for t in tasks if t[9] == "completed"])
    next_deadline = get_next_deadline_from_tasks(tasks)
    plan_stats = get_today_and_week_stats(daily_plan) if daily_plan else {
        "today_hours": 0.0,
        "today_tasks": 0,
        "week_hours": 0.0,
        "week_tasks": 0
    }

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active tasks", active_tasks)
    c2.metric("Completed tasks", completed_tasks)
    c3.metric("Planned today", f"{plan_stats['today_hours']} h", f"{plan_stats['today_tasks']} blocks")
    c4.metric("Planned this week", f"{plan_stats['week_hours']} h", f"{plan_stats['week_tasks']} blocks")

    st.markdown("---")

    left, right = st.columns(2)

    with left:
        st.markdown(
            f"""
            <div class="metric-card">
                <h4 style="margin-bottom:8px;">Next deadline</h4>
                <div>{next_deadline if next_deadline else 'No upcoming deadlines'}</div>
                <div class="small-muted" style="margin-top:8px;">Based on active tasks</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with right:
        progress = 0.0
        if total_tasks > 0:
            progress = completed_tasks / total_tasks

        st.markdown("#### Task completion progress")
        st.progress(progress)
        st.caption(f"{completed_tasks} of {total_tasks} tasks completed")


def group_history_by_task(history):
    grouped = {}

    for row in history:
        (
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
            logged_at
        ) = row

        key = (task_name, subject, task_type, importance_level, estimated_hours)

        if key not in grouped:
            grouped[key] = {
                "task_name": task_name,
                "subject": subject,
                "task_type": task_type,
                "importance_level": importance_level,
                "estimated_hours": float(estimated_hours),
                "latest_adjusted_hours": float(adjusted_hours),
                "total_actual_hours": 0.0,
                "completed": False,
                "latest_remaining_hours": float(remaining_hours),
                "latest_logged_at": logged_at,
                "feedback_count": 0
            }

        grouped[key]["total_actual_hours"] += float(actual_hours)
        grouped[key]["feedback_count"] += 1

        if logged_at >= grouped[key]["latest_logged_at"]:
            grouped[key]["latest_adjusted_hours"] = float(adjusted_hours)
            grouped[key]["latest_remaining_hours"] = float(remaining_hours)
            grouped[key]["latest_logged_at"] = logged_at

        if completed:
            grouped[key]["completed"] = True
            grouped[key]["latest_remaining_hours"] = 0.0

    result = list(grouped.values())
    result.sort(key=lambda x: x["latest_logged_at"], reverse=True)
    return result


def get_feedback_reminder_tasks(student_id: str):
    saved_plan = get_saved_study_plan(student_id)
    tasks = get_tasks_for_student(student_id)
    history = get_history_for_student(student_id)

    if not saved_plan:
        return []

    today_str = date.today().isoformat()

    last_planned_per_task = {}

    for row in saved_plan:
        _, study_date, task_id, task_name, subject, task_type, importance_level, _deadline, start_time, end_time, planned_hours, energy_level, created_at = row
        if study_date < today_str:
            if task_id not in last_planned_per_task or study_date > last_planned_per_task[task_id]["planned_date"]:
                last_planned_per_task[task_id] = {
                    "planned_date": study_date,
                    "task_name": task_name,
                    "subject": subject,
                    "task_type": task_type,
                    "importance_level": importance_level
                }

    if not last_planned_per_task:
        return []

    task_status_map = {}
    for task in tasks:
        task_id, name, subject, ttype, importance, intensity, dl, est, adj, status, is_spread_learning, preferred_study_days, min_session_hours, max_session_hours = task
        task_status_map[task_id] = {
            "task_name": name,
            "task_type": ttype,
            "importance_level": importance,
            "status": status
        }

    last_feedback_per_task_id = {}

    for row in history:
        (
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
            logged_at
        ) = row

        feedback_date = logged_at[:10]

        if task_id not in last_feedback_per_task_id or feedback_date > last_feedback_per_task_id[task_id]:
            last_feedback_per_task_id[task_id] = feedback_date

    reminders = []

    for task_id, plan_info in last_planned_per_task.items():
        if task_id not in task_status_map:
            continue

        task_info = task_status_map[task_id]

        if task_info["status"] == "completed":
            continue

        task_name = task_info["task_name"]
        planned_date = plan_info["planned_date"]
        last_feedback_date = last_feedback_per_task_id.get(task_id)

        if last_feedback_date is None or last_feedback_date < planned_date:
            reminders.append({
                "task_id": task_id,
                "task_name": task_name,
                "task_type": task_info["task_type"],
                "importance_level": task_info["importance_level"],
                "planned_date": planned_date,
                "status": task_info["status"]
            })

    return reminders


def render_ai_help_section():
    st.markdown("---")
    st.subheader("AI Help Assistant")
    st.caption("Ask questions about how the app works, where to find features, or what certain terms mean.")

    st.markdown("""
**Example questions:**
- Where do I set my wake and sleep time?
- Where do I add daily activities?
- What do estimated hours mean?
- Where can I submit feedback?
- How do I generate a study plan?
""")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Start AI Help"):
            with st.spinner("Opening AI help assistant..."):
                welcome_reply = chat_with_system_guide(
                    chat_history=[],
                    user_message="Give me a short overview of what I can do in this app."
                )
                st.session_state.system_help_chat = [
                    {"role": "assistant", "content": welcome_reply}
                ]
            st.rerun()

    with col2:
        if st.button("Reset AI Help Chat"):
            st.session_state.system_help_chat = []
            st.rerun()

    for msg in st.session_state.system_help_chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    help_question = st.chat_input(
        "Ask something about how the system works...",
        key="system_help_input"
    )

    if help_question:
        st.session_state.system_help_chat.append({
            "role": "user",
            "content": help_question
        })

        recent_help_history = st.session_state.system_help_chat[-10:]

        with st.spinner("Thinking..."):
            help_reply = chat_with_system_guide(
                chat_history=recent_help_history,
                user_message=help_question
            )

        st.session_state.system_help_chat.append({
            "role": "assistant",
            "content": help_reply
        })

        st.rerun()


# -----------------------------
# Student pages
# -----------------------------

@st.dialog("Welcome to the Personalized Study Planner")
def render_onboarding_dialog(student_id: str, student_name: str):
    st.markdown(f"""
Welcome **{student_name}**!

This study planner helps you create realistic study schedules based on your tasks, deadlines, availability, and study preferences.

### How to use the planner

**1. Add tasks**
- Go to Planning Setup → Task Setup
- Enter your assignments, exams, deadlines, and estimated hours

**2. Add daily availability**
- Go to Planning Setup → Daily Context Setup
- Enter wake/sleep times and activities such as work, classes, sports, or social events

**3. Generate a study plan**
- Review your information
- Click Build Study Plan

**4. Follow your plan**
- View your calendar in Saved Study Plan

**5. Submit feedback**
- After studying, provide feedback about concentration, confidence, difficulty, and actual study time

The planner uses this information to generate more personalized schedules over time.

### Need help?

If you have questions:
- Ask the AI Assistant on the Dashboard
- Use the Help Navigator page

Enjoy planning!
""")

    if st.button("Start using the planner"):
        mark_onboarding_seen(student_id)
        st.rerun()


def render_student_dashboard_home(student_id: str, student_name: str):
    st.title("Personalized Workload-Aware Study Planner")
    st.subheader(f"Welcome, {student_name} ({student_id})")

    student_row = get_student(student_id)

    if student_row:
        has_seen_onboarding = student_row[3]

        if not has_seen_onboarding:
            render_onboarding_dialog(student_id, student_name)

    st.markdown("### Today's Study Plan")

    today_str = date.today().isoformat()
    today_items = []

    current_plan = st.session_state.generated_plan

    if current_plan:
        daily_plan = current_plan["daily_plan"]
        if today_str in daily_plan:
            today_items = daily_plan[today_str]
    else:
        saved_plan = get_saved_study_plan(student_id)
        for row in saved_plan:
            _, study_date, task_id, task_name, subject, task_type, importance_level, deadline, start_time, end_time, planned_hours, energy_level, created_at = row

            if study_date == today_str:
                today_items.append({
                    "task_id": task_id,
                    "task_name": task_name,
                    "subject": subject,
                    "task_type": task_type,
                    "importance_level": importance_level,
                    "hours": planned_hours,
                    "deadline": deadline if deadline else study_date
                })

    if today_items:
        total_today_hours = sum(item["hours"] for item in today_items)

        st.markdown(
            f"""
            <div class="metric-card">
                <b>Total planned today:</b> {round(total_today_hours, 2)} hours
            </div>
            """,
            unsafe_allow_html=True
        )

        for item in today_items:
            st.markdown(
                f"""
                <div class="soft-card">
                    <b>{item['task_name']}</b> — {item['hours']}h <br>
                    <span class="small-muted">Deadline: {item['deadline']}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("No tasks scheduled for today.")

    st.markdown("---")
    st.markdown("### Feedback Reminders")

    reminder_tasks = get_feedback_reminder_tasks(student_id)

    if reminder_tasks:
        st.warning("You still need to log feedback for previously scheduled tasks.")

        for item in reminder_tasks:
            st.markdown(
                f"""
                <div class="soft-card">
                    <b>{item['task_name']}</b><br>
                    <span class="small-muted">
                        Last planned day: {item['planned_date']} |
                        Task type: {item['task_type']} |
                        Status: {item['status']}
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.info("Go to the Feedback page to update your progress.")
    else:
        st.success("No pending feedback reminders.")

    tasks = get_tasks_for_student(student_id)
    open_tasks = [task for task in tasks if task[9] != "completed"]
    history = get_history_for_student(student_id)
    current_plan = st.session_state.generated_plan["daily_plan"] if st.session_state.generated_plan else {}

    render_student_overview_cards(tasks, current_plan)

    dashboard_tab1, dashboard_tab2, dashboard_tab3 = st.tabs(["Current Tasks", "This Week", "Recent Feedback"])

    with dashboard_tab1:
        st.markdown("### Current tasks")
        if open_tasks:
            for task in open_tasks[:8]:
                task_id, name, subject, ttype, importance, intensity, dl, est, adj, status, is_spread_learning, preferred_study_days, min_session_hours, max_session_hours = task
                render_task_card(task_id, name, subject, ttype, importance, intensity, dl, est, adj, status)
        else:
            st.success("No current open tasks. Nice work!")

    with dashboard_tab2:
        st.markdown("### This week overview")
        if current_plan:
            render_workload_chart(current_plan)
        else:
            st.info("No generated plan yet. Build a study plan to see this week's workload.")

    with dashboard_tab3:
        st.markdown("### Recent feedback")
        if history:
            grouped_history = group_history_by_task(history)
            for item in grouped_history[:5]:
                status_html = (
                    '<span class="badge badge-completed">Completed</span>'
                    if item["completed"]
                    else '<span class="badge badge-incomplete">Open / Partial</span>'
                )

                st.markdown(
                    f"""
                    <div class="soft-card">
                        <b>{item['task_name']}</b><br>
                        {importance_badge(item['importance_level'])}
                        {status_html}
                        <div style="margin-top:8px;">
                            Total worked: {round(item['total_actual_hours'], 2)} h |
                            Remaining: {round(item['latest_remaining_hours'], 2)} h |
                            Updates: {item['feedback_count']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No feedback logged yet.")

    render_ai_help_section()


def render_planning_setup_page(student_id: str):
    st.title("Planning Setup")

    section = st.radio(
        "Choose setup section",
        ["Task Setup", "Daily Context Setup", "Generate Study Plan"],
        horizontal=True
    )

    if section == "Task Setup":
        st.subheader("Manage Subjects / Courses")

        subject_col1, subject_col2 = st.columns([2, 1])

        with subject_col1:
            new_subject = st.text_input(
                "Add a subject / course that you are currently following",
                key="new_subject_input"
            )

        with subject_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Add Subject"):
                if new_subject.strip():
                    add_subject(student_id, new_subject.strip())
                    st.success(f"Subject '{new_subject.strip().title()}' added.")
                    st.rerun()
                else:
                    st.warning("Please enter a subject name.")

        subjects = get_subjects_for_student(student_id)

        if subjects:
            st.markdown("#### Your subjects")

            selected_subjects_to_delete = []

            for subject_item in subjects:
                checked = st.checkbox(
                    f"{subject_item}",
                    key=f"subject_checkbox_{subject_item}"
                )

                if checked:
                    selected_subjects_to_delete.append(subject_item)

            st.markdown("---")

            confirm_delete_subjects = st.checkbox(
                "I understand that selected subjects will be deleted",
                key="confirm_delete_subjects"
            )

            if st.button("Delete selected subjects"):
                if not selected_subjects_to_delete:
                    st.warning("Please select at least one subject.")
                elif not confirm_delete_subjects:
                    st.warning("Please confirm deletion of the selected subjects.")
                else:
                    for subject_item in selected_subjects_to_delete:
                        delete_subject(student_id, subject_item)

                    st.success(f"{len(selected_subjects_to_delete)} subject(s) deleted.")
                    st.rerun()
        else:
            st.info("No subjects added yet. Please add at least one subject before creating tasks.")

        st.markdown("---")
        st.subheader("Add Task")

        # Rij 1
        col1, col2 = st.columns(2)

        with col1:
            task_name = st.text_input("Task name")

        with col2:
            deadline = st.date_input("Deadline", value=date.today() + timedelta(days=7))

        # Rij 2
        col1, col2 = st.columns(2)

        with col1:
            if subjects:
                subject = st.selectbox("Subject / Course", subjects)
            else:
                subject = None
                st.selectbox(
                    "Subject / Course",
                    ["No subjects available"],
                    disabled=True
                )

        with col2:
            task_type = st.selectbox(
                "Task type",
                [
                    "Study / Learning",
                    "Reading",
                    "Practice",
                    "Writing",
                    "Review",
                    "Administrative"
                ]
            )

        # Rij 3
        col1, col2 = st.columns(2)

        with col1:
            estimated_hours = st.number_input(
                "Estimated hours",
                min_value=0.5,
                max_value=200.0,
                value=2.0,
                step=0.5
            )

        with col2:
            importance_level = st.selectbox(
                "Importance level",
                ["High", "Medium", "Low"]
            )

        is_spread_learning = False
        preferred_study_days = None
        min_session_hours = None
        max_session_hours = None

        if task_type == "Study / Learning":
            st.markdown("### Spread-learning options")

            is_spread_learning = st.checkbox(
                "Spread this learning task over multiple days",
                value=False
            )

            if is_spread_learning:
                spread_col1, spread_col2, spread_col3 = st.columns(3)

                with spread_col1:
                    preferred_study_days = st.number_input(
                        "Preferred number of study days",
                        min_value=2,
                        max_value=14,
                        value=4,
                        step=1
                    )

                with spread_col2:
                    min_session_hours = st.number_input(
                        "Minimum session length (hours)",
                        min_value=0.5,
                        max_value=4.0,
                        value=1.0,
                        step=0.5
                    )

                with spread_col3:
                    max_session_hours = st.number_input(
                        "Maximum session length (hours)",
                        min_value=0.5,
                        max_value=4.0,
                        value=2.0,
                        step=0.5
                    )

                max_feasible_days = int(float(estimated_hours) // float(min_session_hours))

                if max_feasible_days < 1:
                    max_feasible_days = 1

                if preferred_study_days > max_feasible_days:
                    st.warning(
                        f"With {float(estimated_hours):.1f} estimated hours and a minimum session length "
                        f"of {float(min_session_hours):.1f} hour(s), this task can be spread over at most "
                        f"{max_feasible_days} study day(s)."
                    )

        if st.button("Add Task"):
            if not subjects:
                st.error("Please add at least one subject first.")
            elif not task_name.strip():
                st.warning("Please enter a task name.")
            elif is_spread_learning and min_session_hours is not None and max_session_hours is not None and min_session_hours > max_session_hours:
                st.warning("Minimum session length cannot be greater than maximum session length.")
            else:
                add_task(
                    student_id=student_id,
                    task_name=task_name.strip(),
                    subject=subject,
                    task_type=task_type,
                    importance_level=importance_level,
                    deadline=deadline.isoformat(),
                    estimated_hours=float(estimated_hours),
                    is_spread_learning=is_spread_learning,
                    preferred_study_days=int(preferred_study_days) if preferred_study_days is not None else None,
                    min_session_hours=float(min_session_hours) if min_session_hours is not None else None,
                    max_session_hours=float(max_session_hours) if max_session_hours is not None else None
                )
                st.success("Task added successfully.")
                st.rerun()

        st.markdown("---")
        st.subheader("Current Open Tasks")

        tasks = get_tasks_for_student(student_id)
        open_tasks = [task for task in tasks if task[9] != "completed"]

        if open_tasks:
            for task in open_tasks:

                task_id, name, subject, ttype, importance, intensity, dl, est, adj, status, is_spread_learning, preferred_study_days, min_session_hours, max_session_hours = task

                col_task, col_edit = st.columns([8, 1])

                with col_task:
                    render_task_card(
                        task_id,
                        name,
                        subject,
                        ttype,
                        importance,
                        intensity,
                        dl,
                        est,
                        adj,
                        status
                    )

                with col_edit:
                    if st.button("Edit", key=f"edit_task_{task_id}"):
                        st.session_state[f"editing_task_{task_id}"] = True

                if st.session_state.get(f"editing_task_{task_id}", False):

                    with st.form(f"edit_task_form_{task_id}"):

                        edit_name = st.text_input(
                            "Task name",
                            value=name
                        )

                        edit_deadline = st.date_input(
                            "Deadline",
                            value=datetime.strptime(dl, "%Y-%m-%d").date()
                        )

                        edit_hours = st.number_input(
                            "Estimated hours",
                            min_value=0.5,
                            max_value=200.0,
                            value=float(est),
                            step=0.5
                        )

                        edit_importance = st.selectbox(
                            "Importance level",
                            ["High", "Medium", "Low"],
                            index=["High", "Medium", "Low"].index(importance)
                        )

                        save_col, cancel_col = st.columns(2)

                        with save_col:
                            save_clicked = st.form_submit_button("Save changes")

                        with cancel_col:
                            cancel_clicked = st.form_submit_button("Cancel")

                        if save_clicked:
                            update_task(
                                task_id=task_id,
                                task_name=edit_name,
                                subject=subject,
                                task_type=ttype,
                                importance_level=edit_importance,
                                deadline=edit_deadline.isoformat(),
                                estimated_hours=float(edit_hours),
                                is_spread_learning=is_spread_learning,
                                preferred_study_days=preferred_study_days,
                                min_session_hours=min_session_hours,
                                max_session_hours=max_session_hours
                            )

                            st.session_state.generated_plan = None
                            st.session_state.ai_study_advice = None
                            st.session_state.llm_chat_history = []

                            st.session_state[f"editing_task_{task_id}"] = False

                            st.success("Task updated successfully.")
                            st.rerun()

                        if cancel_clicked:
                            st.session_state[f"editing_task_{task_id}"] = False
                            st.rerun()

            st.markdown("### Delete open tasks")

            selected_open_task_ids = []

            for task in open_tasks:
                task_id, name, subject, ttype, importance, intensity, dl, est, adj, status, is_spread_learning, preferred_study_days, min_session_hours, max_session_hours = task
                checkbox_label = f"{name} | {subject} | {ttype} | {importance} | auto intensity: {intensity} | deadline: {dl} | status: {status}"
                checked = st.checkbox(checkbox_label, key=f"planning_delete_task_{task_id}")
                if checked:
                    selected_open_task_ids.append(task_id)

            confirm_delete_selected_open_tasks = st.checkbox(
                "I understand that selected open tasks will be deleted",
                key="confirm_delete_selected_open_tasks"
            )

            if st.button("Delete selected open tasks", key="delete_selected_open_tasks_planning"):
                if not selected_open_task_ids:
                    st.warning("Please select at least one open task.")
                elif not confirm_delete_selected_open_tasks:
                    st.warning("Please confirm deletion of the selected open tasks.")
                else:
                    for task_id in selected_open_task_ids:
                        delete_task(task_id)
                        remove_task_from_generated_plan(task_id)

                    st.session_state.ai_study_advice = None
                    st.session_state.llm_chat_history = []
                    st.success(f"{len(selected_open_task_ids)} open task(s) deleted.")
                    st.rerun()
        else:
            st.info("No open tasks found.")



    elif section == "Daily Context Setup":

        st.subheader("Daily Context Setup")

        tasks = get_tasks_for_student(student_id)

        open_tasks = [task for task in tasks if task[9] != "completed"]

        if open_tasks:

            latest_deadline = max(task[6] for task in open_tasks)

            st.info(

                f"It is useful to enter your daily context up to **{latest_deadline}**, "

                f"because this is the latest deadline among your current open tasks."

            )

        else:

            st.info(

                "You do not have any open tasks yet. After adding tasks, this page will show "

                "how far ahead it is useful to enter your daily context."

            )

        st.caption(

            "Set when your day starts and ends, and add activities that fill your day. "

            "The remaining gaps will be treated as possible study time."

        )

        st.markdown("### Sleep / wake window")

        st.warning(
            "Sleep should be entered using the sleep / wake window below. "
            "Use 'Rest' only for awake rest moments such as breaks, recovery, "
            "or moments where you do not want to study."
        )

        p1, p2, p3 = st.columns(3)

        with p1:

            pref_date = st.date_input(

                "Date for sleep/wake preference",

                value=date.today(),

                key="pref_date"

            )

        with p2:

            wake_time = st.time_input(

                "Wake time",

                value=datetime.strptime("07:00", "%H:%M").time(),

                key="wake_time"

            )

        with p3:

            sleep_time = st.time_input(

                "Sleep time",

                value=datetime.strptime("23:00", "%H:%M").time(),

                key="sleep_time"

            )

        if st.button("Save sleep / wake window"):

            if wake_time >= sleep_time:

                st.warning("Sleep time must be later than wake time within the same day.")

            else:

                upsert_day_preference(

                    student_id=student_id,

                    study_date=pref_date.isoformat(),

                    wake_time=wake_time.strftime("%H:%M"),

                    sleep_time=sleep_time.strftime("%H:%M")

                )

                st.success("Sleep / wake window saved.")

                st.rerun()

        st.markdown("---")

        st.subheader("Saved sleep / wake")

        pref_rows = get_day_preferences_for_range(

            student_id,

            date.today().isoformat(),

            (date.today() + timedelta(days=30)).isoformat()

        )

        if pref_rows:

            pref_display = pd.DataFrame([

                {

                    "date": study_date,

                    "wake_time": wake_str,

                    "sleep_time": sleep_str

                }

                for study_date, wake_str, sleep_str in pref_rows

            ])

            st.dataframe(pref_display, width="stretch", hide_index=True)

            selected_pref_dates_to_delete = []

            for study_date, wake_str, sleep_str in pref_rows:

                col_a, col_b = st.columns([5, 1])

                with col_a:

                    checked = st.checkbox(

                        f"{study_date} | Wake: {wake_str} | Sleep: {sleep_str}",

                        key=f"day_preference_checkbox_{study_date}"

                    )

                    if checked:
                        selected_pref_dates_to_delete.append(study_date)

                with col_b:

                    if st.button("Delete", key=f"delete_day_preference_{study_date}"):
                        delete_day_preference(student_id, study_date)

                        st.success(f"Sleep / wake preference deleted for {study_date}")

                        st.rerun()

            st.markdown("---")

            confirm_delete_selected_prefs = st.checkbox(

                "I understand that selected sleep / wake preferences will be deleted",

                key="confirm_delete_selected_day_preferences"

            )

            if st.button("Delete selected sleep / wake preferences"):

                if not selected_pref_dates_to_delete:

                    st.warning("Please select at least one sleep / wake preference.")

                elif not confirm_delete_selected_prefs:

                    st.warning("Please confirm deletion of selected sleep / wake preferences.")

                else:

                    for study_date in selected_pref_dates_to_delete:
                        delete_day_preference(student_id, study_date)

                    st.success(f"{len(selected_pref_dates_to_delete)} sleep / wake preference(s) deleted.")

                    st.rerun()

        else:

            st.info("No sleep / wake preferences saved yet.")

        st.markdown("---")

        st.markdown("### Add daily activity")

        col1, col2 = st.columns(2)

        with col1:
            activity_date = st.date_input(
                "Activity date",
                value=date.today(),
                key="activity_slot_date"
            )

        with col2:
            reason = st.selectbox(
                "Activity type",
                ["Work/School", "Physical activity", "Social", "Rest", "Study-free day", "Other"],
                key="activity_reason"
            )

        if reason != "Study-free day":
            col3, col4 = st.columns(2)

            with col3:
                start_time = st.time_input(
                    "Start time",
                    value=datetime.strptime("09:00", "%H:%M").time(),
                    key="activity_slot_start"
                )

            with col4:
                end_time = st.time_input(
                    "End time",
                    value=datetime.strptime("11:00", "%H:%M").time(),
                    key="activity_slot_end"
                )

        st.info(
            "Short study breaks are automatically added by the planner. "
            "You do not need to enter them here. "
            "Use 'Rest' for longer awake rest periods. "
            "Use 'Study-free day' if you want to keep a whole day free from studying."
        )

        if reason == "Study-free day":
            st.info(
                f"The full day {activity_date.isoformat()} will be kept free from studying."
            )

        if st.button("Save activity slot"):

            if reason == "Study-free day":
                start_time_to_save = "00:00"
                end_time_to_save = "23:59"

            else:
                if start_time >= end_time:
                    st.warning("End time must be later than start time.")
                    return

                start_time_to_save = start_time.strftime("%H:%M")
                end_time_to_save = end_time.strftime("%H:%M")

            add_activity_slot(
                student_id=student_id,
                study_date=activity_date.isoformat(),
                start_time=start_time_to_save,
                end_time=end_time_to_save,
                reason=reason
            )

            st.success(
                f"Activity saved for {activity_date.isoformat()}: "
                f"{start_time_to_save} - {end_time_to_save} ({reason})"
            )

            st.rerun()

        st.markdown("---")

        st.subheader("Saved activity slots")

        slot_rows = get_activity_slots_for_range(

            student_id,

            date.today().isoformat(),

            (date.today() + timedelta(days=30)).isoformat()

        )

        if slot_rows:

            slot_display_rows = []

            for slot_id, study_date, start_time_str, end_time_str, reason in slot_rows:
                start_dt = datetime.strptime(start_time_str, "%H:%M")

                end_dt = datetime.strptime(end_time_str, "%H:%M")

                duration_hours = round((end_dt - start_dt).seconds / 3600, 2)

                slot_display_rows.append({

                    "slot_id": slot_id,

                    "study_date": study_date,

                    "start_time": start_time_str,

                    "end_time": end_time_str,

                    "reason": reason,

                    "duration_hours": duration_hours

                })

            slot_df = pd.DataFrame(slot_display_rows)

            st.dataframe(

                slot_df[["study_date", "start_time", "end_time", "reason", "duration_hours"]],

                width="stretch",

                hide_index=True

            )

            selected_slot_ids_to_delete = []

            for slot_id, study_date, start_time_str, end_time_str, reason in slot_rows:

                col_a, col_b, col_c = st.columns([5, 1, 1])

                with col_a:
                    checked = st.checkbox(
                        f"{study_date} | {start_time_str} - {end_time_str} | {reason}",
                        key=f"activity_slot_checkbox_{slot_id}"
                    )

                    if checked:
                        selected_slot_ids_to_delete.append(slot_id)

                with col_b:
                    if st.button("Edit", key=f"edit_activity_slot_{slot_id}"):
                        st.session_state[f"editing_activity_slot_{slot_id}"] = True

                with col_c:
                    if st.button("Delete", key=f"delete_activity_slot_{slot_id}"):
                        delete_activity_slot(slot_id)
                        st.success(f"Activity slot deleted: {study_date} {start_time_str}-{end_time_str}")
                        st.rerun()

                if st.session_state.get(f"editing_activity_slot_{slot_id}", False):
                    with st.form(f"edit_activity_form_{slot_id}"):

                        edit_activity_date = st.date_input(
                            "Activity date",
                            value=datetime.strptime(study_date, "%Y-%m-%d").date(),
                            key=f"edit_activity_date_{slot_id}"
                        )

                        activity_reason_options = [
                            "Work/School",
                            "Physical activity",
                            "Social",
                            "Rest",
                            "Study-free day",
                            "Other"
                        ]

                        edit_reason = st.selectbox(
                            "Activity type",
                            activity_reason_options,
                            index=activity_reason_options.index(reason) if reason in activity_reason_options else 0,
                            key=f"edit_activity_reason_{slot_id}"
                        )

                        if edit_reason != "Study-free day":
                            ec1, ec2 = st.columns(2)

                            with ec1:
                                edit_start_time = st.time_input(
                                    "Start time",
                                    value=datetime.strptime(start_time_str, "%H:%M").time(),
                                    key=f"edit_activity_start_{slot_id}"
                                )

                            with ec2:
                                edit_end_time = st.time_input(
                                    "End time",
                                    value=datetime.strptime(end_time_str, "%H:%M").time(),
                                    key=f"edit_activity_end_{slot_id}"
                                )

                        save_col, cancel_col = st.columns(2)

                        with save_col:
                            save_clicked = st.form_submit_button("Save changes")

                        with cancel_col:
                            cancel_clicked = st.form_submit_button("Cancel")

                        if save_clicked:
                            if edit_reason == "Study-free day":
                                start_time_to_save = "00:00"
                                end_time_to_save = "23:59"
                            else:
                                if edit_start_time >= edit_end_time:
                                    st.warning("End time must be later than start time.")
                                    return

                                start_time_to_save = edit_start_time.strftime("%H:%M")
                                end_time_to_save = edit_end_time.strftime("%H:%M")

                            update_activity_slot(
                                slot_id=slot_id,
                                study_date=edit_activity_date.isoformat(),
                                start_time=start_time_to_save,
                                end_time=end_time_to_save,
                                reason=edit_reason
                            )

                            st.session_state.generated_plan = None
                            st.session_state.ai_study_advice = None
                            st.session_state.llm_chat_history = []
                            st.session_state[f"editing_activity_slot_{slot_id}"] = False

                            st.success("Activity slot updated successfully.")
                            st.rerun()

                        if cancel_clicked:
                            st.session_state[f"editing_activity_slot_{slot_id}"] = False
                            st.rerun()

            st.markdown("---")

            confirm_delete_selected_slots = st.checkbox(
                "I understand that selected activity slots will be deleted",
                key="confirm_delete_selected_activity_slots"
            )

            if st.button("Delete selected activity slots"):

                if not selected_slot_ids_to_delete:
                    st.warning("Please select at least one activity slot.")

                elif not confirm_delete_selected_slots:
                    st.warning("Please confirm deletion of selected activity slots.")

                else:
                    for slot_id in selected_slot_ids_to_delete:
                        delete_activity_slot(slot_id)

                    st.success(f"{len(selected_slot_ids_to_delete)} activity slot(s) deleted.")
                    st.rerun()

        else:

            st.info("No activity slots have been saved yet.")



    elif section == "Generate Study Plan":

        st.subheader("Generate Study Plan")

        due_feedback_tasks = get_due_feedback_tasks(student_id)

        if due_feedback_tasks:

            st.markdown("### Tasks that need feedback first")

            st.warning(

                "You still have scheduled study tasks that have already taken place and do not yet have feedback. "

                "Please submit feedback first before generating a new study plan."

            )

            st.markdown("### Tasks that need feedback first")

            for task_id, task_name, subject, task_type, importance_level, latest_due_date, latest_due_time in due_feedback_tasks:
                st.markdown(
                    f"""
                    <div class="soft-card">
                        <h4 style="margin-bottom:8px;">{task_name}</h4>
                        <div style="margin-bottom:8px;">
                            {importance_badge(importance_level)}
                        </div>
                        <div><b>Subject:</b> {subject}</div>
                        <div><b>Task type:</b> {task_type}</div>
                        <div><b>Planned block ended:</b> {latest_due_date} {latest_due_time if latest_due_time else ''}</div>
                        <div class="small-muted" style="margin-top:8px;">Task ID: {task_id}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.info(
                "Go to the Feedback page first and submit feedback for these tasks. "
                "After that, you can generate a new study plan."
            )

        else:

            st.markdown("### Review before planning")
            st.caption("Check your tasks, sleep/wake settings, and activity slots before generating the study plan.")

            tasks = get_tasks_for_student(student_id)
            open_tasks = [task for task in tasks if task[9] != "completed"]

            if open_tasks:
                latest_deadline = max(task[6] for task in open_tasks)
            else:
                latest_deadline = date.today().isoformat()

            review_tab1, review_tab2, review_tab3 = st.tabs(
                ["Tasks", "Sleep / Wake", "Activity Slots"]
            )

            with review_tab1:
                if open_tasks:
                    for task in open_tasks:
                        task_id, name, subject, ttype, importance, intensity, dl, est, adj, status, is_spread_learning, preferred_study_days, min_session_hours, max_session_hours = task
                        render_task_card(task_id, name, subject, ttype, importance, intensity, dl, est, adj, status)
                else:
                    st.info("No open tasks found.")

            with review_tab2:
                pref_rows = get_day_preferences_for_range(
                    student_id,
                    date.today().isoformat(),
                    latest_deadline
                )

                if pref_rows:
                    pref_display = pd.DataFrame([
                        {
                            "date": study_date,
                            "wake_time": wake_str,
                            "sleep_time": sleep_str
                        }
                        for study_date, wake_str, sleep_str in pref_rows
                    ])
                    st.dataframe(pref_display, width="stretch", hide_index=True)
                else:
                    st.info("No sleep / wake preferences saved for this planning period.")

            with review_tab3:
                slot_rows = get_activity_slots_for_range(
                    student_id,
                    date.today().isoformat(),
                    latest_deadline
                )

                if slot_rows:
                    slot_display_rows = []

                    for slot_id, study_date, start_time_str, end_time_str, reason in slot_rows:
                        start_dt = datetime.strptime(start_time_str, "%H:%M")
                        end_dt = datetime.strptime(end_time_str, "%H:%M")
                        duration_hours = round((end_dt - start_dt).seconds / 3600, 2)

                        slot_display_rows.append({
                            "study_date": study_date,
                            "start_time": start_time_str,
                            "end_time": end_time_str,
                            "reason": reason,
                            "duration_hours": duration_hours
                        })

                    slot_df = pd.DataFrame(slot_display_rows)
                    st.dataframe(slot_df, width="stretch", hide_index=True)
                else:
                    st.info("No activity slots saved for this planning period.")

            st.markdown("---")

            if st.button("Build Study Plan"):

                plan_result = build_study_plan(student_id)

                st.session_state.generated_plan = plan_result

                st.session_state.ai_study_advice = None

                st.session_state.llm_chat_history = []

                if plan_result["daily_plan"]:
                    save_study_plan(student_id, plan_result["daily_plan"])

            plan_result = st.session_state.generated_plan

            if plan_result:

                daily_plan = plan_result["daily_plan"]
                unscheduled_tasks = plan_result["unscheduled_tasks"]

                total_required_hours = plan_result["total_required_hours"]
                total_available_hours = plan_result["total_available_hours"]

                render_plan_summary_cards(plan_result)

                if unscheduled_tasks:
                    unscheduled_total = round(
                        sum(float(item.get("remaining_hours", 0.0)) for item in unscheduled_tasks),
                        2
                    )

                    st.warning(
                        f"⚠ This plan is only partially feasible. "
                        f"{unscheduled_total} hours could not be scheduled."
                    )

                    has_short_slot_issue = any(
                        item.get("task_type") in ["Study / Learning", "Practice", "Writing"]
                        for item in unscheduled_tasks
                    )

                    if has_short_slot_issue:
                        st.info(
                            "Some available time slots may be too short for these task types. "
                            "Study / Learning, Practice, and Writing blocks need at least 30 minutes."
                        )

                elif total_required_hours > total_available_hours:
                    st.warning(
                        f"⚠ You need {total_required_hours} hours but only {total_available_hours} hours are available."
                    )

                else:
                    st.success("Workload appears feasible within current daily context setup.")

                plan_tab1, plan_tab2, plan_tab3 = st.tabs(
                    ["Calendar", "Daily Details", "Unscheduled"]
                )

                with plan_tab1:
                    render_calendar_legend()
                    render_plan_calendar(daily_plan, calendar_key="generated_study_plan_calendar")

                with plan_tab2:
                    st.markdown("### Planned workload per day")
                    render_workload_chart(daily_plan)
                    st.markdown("---")
                    render_plan_details(daily_plan)

                with plan_tab3:
                    render_unscheduled_tasks(unscheduled_tasks)

                st.markdown("---")

                if daily_plan:
                    if unscheduled_tasks:
                        st.warning("Study plan generated and saved, but some task hours remain unscheduled.")
                    else:
                        st.success("Study plan generated and saved to the database.")

            else:
                st.info("Click 'Build Study Plan' to generate a new plan.")


def render_plan_summary_cards(plan_result: dict):
    daily_plan = plan_result.get("daily_plan", {})
    unscheduled_tasks = plan_result.get("unscheduled_tasks", [])

    total_required_hours = round(float(plan_result.get("total_required_hours", 0.0)), 2)
    total_available_hours = round(float(plan_result.get("total_available_hours", 0.0)), 2)
    planning_start = plan_result.get("planning_start", "N/A")
    planning_end = plan_result.get("planning_end", "N/A")

    planned_hours = 0.0
    planned_blocks = 0
    planned_today = 0.0
    blocks_today = 0

    today_str = date.today().isoformat()
    hours_by_day = {}

    for study_day, items in daily_plan.items():
        day_total = 0.0

        for item in items:
            if item.get("is_break"):
                continue

            hours = float(item.get("hours", 0.0))
            planned_hours += hours
            planned_blocks += 1
            day_total += hours

            if study_day == today_str:
                planned_today += hours
                blocks_today += 1

        hours_by_day[study_day] = day_total

    busiest_day = "N/A"
    busiest_day_hours = 0.0

    if hours_by_day:
        busiest_day = max(hours_by_day, key=hours_by_day.get)
        busiest_day_hours = round(hours_by_day[busiest_day], 2)

    unscheduled_hours = round(
        sum(float(item.get("remaining_hours", 0.0)) for item in unscheduled_tasks),
        2
    )

    st.markdown(f"**Planning start:** {planning_start}")
    st.markdown(f"**Planning end:** {planning_end}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total required hours", total_required_hours)
    col2.metric("Total available hours", total_available_hours)
    col3.metric("Unscheduled hours", unscheduled_hours)
    col4.metric("Busiest day", busiest_day, f"↑ {busiest_day_hours}h")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Planned today", f"{round(planned_today, 2)} h", f"↑ {blocks_today} blocks")
    col6.metric("This week", f"{round(planned_hours, 2)} h", f"↑ {planned_blocks} blocks")
    col7.metric("Planned blocks", planned_blocks)
    col8.metric("Planned hours", round(planned_hours, 2))


def render_saved_plan_page(student_id: str):
    st.title("Saved Study Plan")

    saved_plan = get_saved_study_plan(student_id)

    if not saved_plan:
        st.info("No saved study plan found.")
        return

    grouped = {}
    created_at_value = None

    for row in saved_plan:
        (
            _,
            study_date,
            task_id,
            task_name,
            subject,
            task_type,
            importance_level,
            deadline,
            start_time,
            end_time,
            planned_hours,
            energy_level,
            created_at
        ) = row

        created_at_value = created_at

        grouped.setdefault(study_date, []).append({
            "task_id": task_id,
            "task_name": task_name,
            "subject": subject,
            "task_type": task_type,
            "importance_level": importance_level,
            "deadline": deadline if deadline else study_date,
            "planned_hours": planned_hours,
            "start_time": start_time,
            "end_time": end_time,
            "energy_level": energy_level,
            "is_break": task_type == "Break"
        })

    if created_at_value:
        st.caption(f"Plan created at: {created_at_value}")

    saved_daily_plan = {}
    total_required_hours = 0.0

    for study_date, items in grouped.items():
        saved_daily_plan[study_date] = []

        for item in items:
            total_required_hours += float(item["planned_hours"])

            saved_daily_plan[study_date].append({
                "task_id": item["task_id"],
                "task_name": item["task_name"],
                "subject": item["subject"],
                "task_type": item["task_type"],
                "importance_level": item["importance_level"],
                "hours": float(item["planned_hours"]),
                "deadline": item["deadline"],
                "start_time": item.get("start_time"),
                "end_time": item.get("end_time"),
                "energy_level": item.get("energy_level"),
                "is_break": item.get("is_break", False)
            })

    saved_tab_calendar, saved_tab_details = st.tabs(["Calendar", "Daily Details"])

    with saved_tab_calendar:
        render_calendar_legend()
        render_plan_calendar(saved_daily_plan, calendar_key="saved_study_plan_calendar")

    with saved_tab_details:
        for study_date, items in grouped.items():
            st.markdown(f"### {study_date}")

            for item in items:
                if item.get("is_break"):
                    st.markdown(
                        f"""
                        <div class="soft-card">
                            <div style="font-weight:700; margin-bottom:6px;">Break</div>
                            <div><b>Time:</b> {item.get('start_time', 'N/A')} - {item.get('end_time', 'N/A')}</div>
                            <div><b>Duration:</b> {item['planned_hours']} h</div>
                            <div><b>Purpose:</b> Recovery</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"""
                        <div class="soft-card">
                            <div style="font-weight:700; margin-bottom:6px;">{item['task_name']}</div>
                            <div>{importance_badge(item['importance_level'])}{energy_badge(item.get('energy_level', 'Medium'))}</div>
                            <div><b>Subject:</b> {item['subject']}</div>
                            <div><b>Task type:</b> {item['task_type']}</div>
                            <div><b>Time:</b> {item.get('start_time', 'N/A')} - {item.get('end_time', 'N/A')}</div>
                            <div><b>Planned hours:</b> {item['planned_hours']} h</div>
                            <div><b>Deadline:</b> {item['deadline']}</div>
                            <div><b>Energy level:</b> {item.get('energy_level', 'N/A')}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    st.markdown("---")

    planning_start = min(grouped.keys())
    planning_end = max(grouped.keys())

    # Prefer the original generated plan metadata if available.
    # This prevents Saved Plan from recalculating availability differently.
    if st.session_state.generated_plan:
        total_available_hours = float(
            st.session_state.generated_plan.get("total_available_hours", 0.0)
        )

        saved_plan_result = {
            "daily_plan": saved_daily_plan,
            "unscheduled_tasks": st.session_state.generated_plan.get("unscheduled_tasks", []),
            "planning_start": st.session_state.generated_plan.get("planning_start", planning_start),
            "planning_end": st.session_state.generated_plan.get("planning_end", planning_end),
            "total_required_hours": round(
                float(st.session_state.generated_plan.get("total_required_hours", total_required_hours)),
                2
            ),
            "total_available_hours": round(total_available_hours, 2),
            "day_limit_hours": st.session_state.generated_plan.get("day_limit_hours", None)
        }
    else:
        # Fallback when the app was refreshed and generated_plan is no longer in session state.
        # We avoid showing a misleading 0-hour feasibility warning.
        total_available_hours = None

        saved_plan_result = {
            "daily_plan": saved_daily_plan,
            "unscheduled_tasks": [],
            "planning_start": planning_start,
            "planning_end": planning_end,
            "total_required_hours": round(total_required_hours, 2),
            "total_available_hours": 0.0,
            "day_limit_hours": None
        }

    render_plan_summary_cards(saved_plan_result)

    tasks = get_tasks_for_student(student_id)
    feasibility = compute_saved_plan_feasibility(tasks, saved_daily_plan)
    partially_planned_tasks = feasibility["partially_planned_tasks"]

    st.subheader("Saved plan feasibility")

    if total_available_hours is None:
        st.info(
            "This page shows your currently saved study plan and workload distribution."
        )

    elif partially_planned_tasks:

        missing_hours = round(
            sum(float(item.get("missing_hours", 0.0)) for item in partially_planned_tasks),
            2
        )

        st.warning(
            f"⚠ This saved plan is only partially feasible. "
            f"{missing_hours} hours are still unscheduled."
        )

    elif total_required_hours > total_available_hours:

        shortage = round(total_required_hours - total_available_hours, 2)

        st.warning(
            f"⚠ This saved plan may not fit the generated availability. "
            f"You need {round(total_required_hours, 2)} hours, but only about {round(total_available_hours, 2)} hours are available. "
            f"Shortage: {shortage} hours."
        )

    else:
        st.success("The saved plan fits within the generated available study hours.")

    if partially_planned_tasks:

        st.warning(
            "Some active tasks are not fully planned in the saved study plan."
        )

        has_short_slot_issue = any(
            item["task_type"] in ["Study / Learning", "Practice", "Writing"]
            for item in partially_planned_tasks
        )

        if has_short_slot_issue:
            st.info(
                "Some remaining free time slots were too short for the "
                "minimum session length requirements of certain tasks."
            )

        for item in partially_planned_tasks:
            st.markdown(
                f"""
                <div class="block-card">
                    <div style="font-weight:700; margin-bottom:8px;">{item['task_name']}</div>
                    <div>{importance_badge(item['importance_level'])}{intensity_badge(item['task_intensity'])}</div>
                    <div><b>Task type:</b> {item['task_type']}</div>
                    <div><b>Deadline:</b> {item['deadline']}</div>
                    <div><b>Required / remaining hours:</b> {item['required_hours']} h</div>
                    <div><b>Planned in saved plan:</b> {item['planned_hours']} h</div>
                    <div><b>Still missing:</b> {item['missing_hours']} h</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    else:
        st.success("All active tasks in this saved plan are fully scheduled.")

    history_rows = get_task_learning_rows(student_id)
    learning_profile_rows = get_learning_profile_for_student(student_id)

    plan_for_ai = (
        st.session_state.generated_plan
        if st.session_state.generated_plan
        else saved_plan_result
    )

    ai_learning_preferences = get_ai_learning_preferences_for_student(student_id)

    student_context = build_student_context(
        plan_result=plan_for_ai,
        history_rows=history_rows,
        tasks=tasks,
        learning_profile_rows=learning_profile_rows,
        ai_learning_preferences=ai_learning_preferences
    )

    st.subheader("AI Study Coach")
    st.caption("Ask follow-up questions about your study plan, workload, and your past study behavior.")

    if not st.session_state.ai_study_advice and not st.session_state.llm_chat_history:
        with st.spinner("Analysing your saved study plan..."):
            first_prompt = (
                "Analyse my saved study plan. "
                "Tell me if it is realistic, where the risks are, "
                "and use my previous feedback patterns if relevant."
            )

            reply = chat_with_study_coach(
                student_context=student_context,
                chat_history=[],
                user_message=first_prompt
            )

            st.session_state.llm_chat_history = [
                {"role": "assistant", "content": reply}
            ]
            st.session_state.ai_study_advice = reply

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Refresh AI Analysis", key="saved_plan_refresh_ai"):
            with st.spinner("Refreshing AI analysis..."):
                first_prompt = (
                    "Analyse my saved study plan. "
                    "Tell me if it is realistic, where the risks are, "
                    "and use my previous feedback patterns if relevant."
                )

                reply = chat_with_study_coach(
                    student_context=student_context,
                    chat_history=[],
                    user_message=first_prompt
                )

                st.session_state.llm_chat_history = [
                    {"role": "assistant", "content": reply}
                ]
                st.session_state.ai_study_advice = reply

            st.rerun()

    with col2:
        if st.button("Reset AI Chat", key="saved_plan_reset_ai_chat"):
            st.session_state.llm_chat_history = []
            st.session_state.ai_study_advice = None
            st.rerun()

    if st.session_state.ai_study_advice and not st.session_state.llm_chat_history:
        st.session_state.llm_chat_history = [
            {"role": "assistant", "content": st.session_state.ai_study_advice}
        ]

    for msg in st.session_state.llm_chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_message = st.chat_input("Ask your study coach something...")

    if user_message:
        st.session_state.llm_chat_history.append({
            "role": "user",
            "content": user_message
        })

        recent_history = st.session_state.llm_chat_history[-10:]

        with st.spinner("Thinking..."):
            reply = chat_with_study_coach(
                student_context=student_context,
                chat_history=recent_history,
                user_message=user_message
            )

        st.session_state.llm_chat_history.append({
            "role": "assistant", "content": reply
        })

        st.rerun()


def render_feedback_page(student_id: str):
    st.title("Task Feedback")

    if "show_rebuild_option" not in st.session_state:
        st.session_state.show_rebuild_option = False

    if "pending_rebuild_task_id" not in st.session_state:
        st.session_state.pending_rebuild_task_id = None

    if "feedback_reflection_task_id" not in st.session_state:
        st.session_state.feedback_reflection_task_id = None

    if "pending_ai_preference_proposal" not in st.session_state:
        st.session_state.pending_ai_preference_proposal = None

    def build_current_reflection_context(subject=None, task_type=None):
        current_history_rows = get_task_learning_rows(student_id)
        current_learning_profile_rows = get_learning_profile_for_student(student_id)
        current_tasks_for_context = get_tasks_for_student(student_id)
        current_ai_preferences = get_ai_learning_preferences_for_student(student_id)

        current_reflection_summaries = get_ai_reflection_summaries_for_student(
            student_id=student_id,
            subject=subject,
            task_type=task_type,
            limit=5
        )

        return build_student_context(
            plan_result=st.session_state.generated_plan if st.session_state.generated_plan else {
                "daily_plan": {},
                "unscheduled_tasks": [],
                "planning_start": None,
                "planning_end": None,
                "total_required_hours": 0.0,
                "total_available_hours": 0.0,
                "day_limit_hours": None
            },
            history_rows=current_history_rows,
            tasks=current_tasks_for_context,
            learning_profile_rows=current_learning_profile_rows,
            ai_learning_preferences=current_ai_preferences,
            reflection_summary_rows=current_reflection_summaries
        )

    def create_pending_proposal(
            proposal_task_id,
            proposal_task_name,
            proposal_subject,
            proposal_task_type,
            proposal_context_text
    ):
        proposal_rows = get_ai_feedback_reflections(student_id, proposal_task_id)

        proposal_chat_history = [
            {"role": row[0], "content": row[1]}
            for row in proposal_rows
        ]

        latest_assistant_message = ""

        for row in reversed(proposal_rows):
            if row[0] == "assistant":
                latest_assistant_message = row[1]
                break

        if "?" in latest_assistant_message:
            return

        completion_check = check_reflection_completion(
            task_name=proposal_task_name,
            subject=proposal_subject,
            task_type=proposal_task_type,
            student_context=proposal_context_text,
            chat_history=proposal_chat_history
        )

        if not completion_check.get("enough_information"):
            latest_assistant_message = ""

            for row in reversed(proposal_rows):
                if row[0] == "assistant":
                    latest_assistant_message = row[1]
                    break

            assistant_is_asking_question = "?" in latest_assistant_message

            if not assistant_is_asking_question:
                st.session_state.pending_ai_preference_proposal = {
                    "task_id": proposal_task_id,
                    "subject": proposal_subject,
                    "task_type": proposal_task_type,
                    "proposal_text": None,
                    "change_time_buffer": False,
                    "add_time_buffer_percent": 0,
                    "preferred_energy": None,
                    "max_session_hours": None,
                    "avoid_after_high_difficulty_task": False,
                    "reason": completion_check.get("reason", "No planning adjustment needed."),
                    "has_proposal": False
                }

            return

        latest_feedback_rows = [
            row for row in get_history_for_student(student_id)
            if len(row) > 1 and row[1] == proposal_task_id
        ]

        latest_feedback_rows.sort(key=lambda row: row[-1], reverse=True)

        latest_feedback = latest_feedback_rows[0] if latest_feedback_rows else None

        proposal_estimated_hours = None
        proposal_adjusted_hours = None
        proposal_actual_hours = None

        if latest_feedback:
            proposal_estimated_hours = float(latest_feedback[6])
            proposal_adjusted_hours = float(latest_feedback[7])
            proposal_actual_hours = float(latest_feedback[8])

        proposal = generate_learning_preference_proposal(
            task_name=proposal_task_name,
            subject=proposal_subject,
            task_type=proposal_task_type,
            student_context=proposal_context_text,
            chat_history=proposal_chat_history,
            estimated_hours=proposal_estimated_hours,
            adjusted_hours=proposal_adjusted_hours,
            actual_hours=proposal_actual_hours
        )

        if not isinstance(proposal, dict):
            proposal = {
                "has_proposal": False,
                "proposal_text": None,
                "reason": ""
            }

        if proposal.get("has_proposal") and proposal.get("proposal_text"):
            st.session_state.pending_ai_preference_proposal = {
                "task_id": proposal_task_id,
                "subject": proposal_subject,
                "task_type": proposal_task_type,
                "proposal_text": proposal["proposal_text"],
                "change_time_buffer": proposal.get("change_time_buffer", False),
                "add_time_buffer_percent": proposal.get("add_time_buffer_percent", 0),
                "preferred_energy": proposal.get("preferred_energy"),
                "max_session_hours": proposal.get("max_session_hours"),
                "avoid_after_high_difficulty_task": proposal.get("avoid_after_high_difficulty_task", False),
                "reason": proposal.get("reason", ""),
                "has_proposal": True
            }
        else:
            st.session_state.pending_ai_preference_proposal = {
                "task_id": proposal_task_id,
                "subject": proposal_subject,
                "task_type": proposal_task_type,
                "proposal_text": None,
                "change_time_buffer": False,
                "add_time_buffer_percent": 0,
                "preferred_energy": None,
                "max_session_hours": None,
                "avoid_after_high_difficulty_task": False,
                "reason": proposal.get("reason", ""),
                "has_proposal": False
            }

    def render_ai_reflection_section(active_reflection_task_id: int):
        reflection_task = get_task_by_id(active_reflection_task_id)

        if not reflection_task:
            st.warning("The reflection task could not be loaded.")
            st.session_state.feedback_reflection_task_id = None
            st.session_state.pending_ai_preference_proposal = None
            return

        (
            loaded_task_id,
            loaded_student_id,
            loaded_task_name,
            loaded_subject,
            loaded_task_type,
            loaded_importance_level,
            loaded_task_intensity,
            loaded_deadline,
            loaded_estimated_hours,
            loaded_adjusted_hours,
            loaded_status,
            loaded_is_spread_learning,
            loaded_preferred_study_days,
            loaded_min_session_hours,
            loaded_max_session_hours
        ) = reflection_task

        st.markdown("---")
        st.subheader("AI Reflection Coach")
        st.caption(
            "Reflect on your feedback and discuss how similar tasks could be planned differently in the future."
        )

        displayed_rows = get_ai_feedback_reflections(student_id, active_reflection_task_id)

        def save_current_reflection_summary(context_text):
            rows = get_ai_feedback_reflections(student_id, active_reflection_task_id)

            chat_history = [
                {"role": row[0], "content": row[1]}
                for row in rows
            ]

            summary_result = generate_reflection_summary(
                task_name=loaded_task_name,
                subject=loaded_subject,
                task_type=loaded_task_type,
                student_context=context_text,
                chat_history=chat_history
            )

            save_ai_reflection_summary(
                student_id=student_id,
                task_id=active_reflection_task_id,
                task_name=loaded_task_name,
                subject=loaded_subject,
                task_type=loaded_task_type,
                summary=summary_result.get("summary"),
                possible_pattern=summary_result.get("possible_pattern"),
                confidence_level=summary_result.get("confidence_level"),
                pattern_stability=summary_result.get("pattern_stability", "task_specific"),
                planning_relevance=summary_result.get("planning_relevance")
            )

        for message_role, message_content, message_created_at in displayed_rows:
            with st.chat_message(message_role):
                st.write(message_content)

        student_message = st.chat_input(
            "Reply to the AI reflection coach...",
            key=f"feedback_reflection_chat_{active_reflection_task_id}"
        )

        if student_message:
            save_ai_feedback_reflection(
                student_id=student_id,
                task_id=active_reflection_task_id,
                role="user",
                content=student_message
            )

            updated_rows = get_ai_feedback_reflections(student_id, active_reflection_task_id)

            updated_chat_history = [
                {"role": row[0], "content": row[1]}
                for row in updated_rows
            ]

            reply_context_text = build_current_reflection_context(
                subject=loaded_subject,
                task_type=loaded_task_type
            )

            latest_feedback_rows = [
                row for row in get_history_for_student(student_id)
                if row[1] == active_reflection_task_id
            ]

            latest_feedback_rows.sort(key=lambda row: row[-1], reverse=True)
            latest_feedback = latest_feedback_rows[0] if latest_feedback_rows else None

            ai_reply = generate_feedback_reflection(
                task_name=loaded_task_name,
                subject=loaded_subject,
                task_type=loaded_task_type,
                estimated_hours=float(latest_feedback[6]) if latest_feedback else float(loaded_estimated_hours),
                adjusted_hours=float(latest_feedback[7]) if latest_feedback else float(loaded_adjusted_hours),
                actual_hours=float(latest_feedback[8]) if latest_feedback else 0.0,
                remaining_hours=float(latest_feedback[10]) if latest_feedback else float(loaded_adjusted_hours),
                completed=bool(latest_feedback[9]) if latest_feedback else loaded_status == "completed",
                perceived_difficulty=latest_feedback[11] if latest_feedback and len(latest_feedback) > 11 else None,
                mental_effort=latest_feedback[12] if latest_feedback and len(latest_feedback) > 12 else None,
                confidence_level=latest_feedback[13] if latest_feedback and len(latest_feedback) > 13 else None,
                focus_level=latest_feedback[14] if latest_feedback and len(latest_feedback) > 14 else None,
                student_context=reply_context_text,
                chat_history=updated_chat_history
            )

            save_ai_feedback_reflection(
                student_id=student_id,
                task_id=active_reflection_task_id,
                role="assistant",
                content=ai_reply
            )

            create_pending_proposal(
                proposal_task_id=active_reflection_task_id,
                proposal_task_name=loaded_task_name,
                proposal_subject=loaded_subject,
                proposal_task_type=loaded_task_type,
                proposal_context_text=reply_context_text
            )

            st.rerun()

        current_proposal = st.session_state.get("pending_ai_preference_proposal")

        if current_proposal and current_proposal.get("task_id") == active_reflection_task_id:
            if not current_proposal.get("has_proposal", False):
                st.markdown("---")
                st.success(
                    "No planning adjustments seem necessary right now. "
                    "Your current study approach for similar tasks appears to work well. Keep it up!"
                )

                if st.button("Continue", key=f"continue_no_ai_preference_{active_reflection_task_id}"):
                    st.session_state.pending_ai_preference_proposal = None
                    st.session_state.feedback_reflection_task_id = None
                    st.rerun()

                return

            change_time_buffer = bool(current_proposal.get("change_time_buffer", False))

            proposal_has_changes = (
                    current_proposal.get("proposal_text") is not None
                    or change_time_buffer
                    or current_proposal.get("preferred_energy") is not None
                    or current_proposal.get("max_session_hours") is not None
                    or bool(current_proposal.get("avoid_after_high_difficulty_task", False))
            )

            if proposal_has_changes:
                st.markdown("---")
                st.subheader("Future planning suggestion")

                st.markdown(
                    f"""
                    <div class="soft-card">
                        <b>For future similar tasks:</b><br>
                        {current_proposal["proposal_text"]}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                accepted_preference_text = st.text_area(
                    "Adjust the suggestion if needed",
                    value=current_proposal["proposal_text"],
                    key=f"edit_ai_preference_{active_reflection_task_id}"
                )

                proposed_buffer = int(current_proposal.get("add_time_buffer_percent", 0) or 0)
                proposed_energy = current_proposal.get("preferred_energy")
                proposed_session = current_proposal.get("max_session_hours")
                proposed_avoid_after = bool(current_proposal.get("avoid_after_high_difficulty_task", False))

                accepted_buffer = None
                accepted_energy = None
                accepted_max_session = None
                accepted_avoid_after = None

                if change_time_buffer:
                    buffer_options = ["0%", "10%", "20%", "30%"]

                    accepted_buffer = st.selectbox(
                        "Extra time buffer for future similar tasks",
                        buffer_options,
                        index=buffer_options.index(f"{proposed_buffer}%")
                        if f"{proposed_buffer}%" in buffer_options
                        else 0,
                        key=f"edit_ai_buffer_{active_reflection_task_id}"
                    )

                    accepted_buffer = int(accepted_buffer.replace("%", ""))

                if proposed_energy is not None:
                    accepted_energy = st.selectbox(
                        "Preferred energy level for future similar tasks",
                        ["High", "Medium", "Low"],
                        index=["High", "Medium", "Low"].index(proposed_energy)
                        if proposed_energy in ["High", "Medium", "Low"]
                        else 0,
                        key=f"edit_ai_energy_{active_reflection_task_id}"
                    )

                if proposed_session is not None:
                    accepted_max_session = st.selectbox(
                        "Maximum session length for future similar tasks",
                        [0.5, 1.0, 1.5],
                        index=[0.5, 1.0, 1.5].index(float(proposed_session))
                        if float(proposed_session) in [0.5, 1.0, 1.5]
                        else 1,
                        key=f"edit_ai_session_{active_reflection_task_id}"
                    )

                if proposed_avoid_after:
                    accepted_avoid_after = st.checkbox(
                        "Avoid scheduling this directly after another demanding task",
                        value=True,
                        key=f"edit_ai_avoid_after_{active_reflection_task_id}"
                    )

                col_accept, col_reject = st.columns(2)

                with col_accept:
                    if st.button("Accept suggestion", key=f"accept_ai_preference_{active_reflection_task_id}"):
                        existing_preferences = get_ai_learning_preferences_for_task(
                            student_id=student_id,
                            task_type=current_proposal["task_type"],
                            subject=current_proposal["subject"]
                        )

                        latest_existing_preference = existing_preferences[0] if existing_preferences else None

                        existing_buffer = int(latest_existing_preference[5] or 0) if latest_existing_preference else 0
                        existing_energy = latest_existing_preference[6] if latest_existing_preference else None
                        existing_max_session = latest_existing_preference[7] if latest_existing_preference else None
                        existing_avoid_after = bool(
                            latest_existing_preference[8]) if latest_existing_preference else False

                        buffer_to_save = int(accepted_buffer) if accepted_buffer is not None else existing_buffer
                        energy_to_save = accepted_energy if accepted_energy is not None else existing_energy
                        max_session_to_save = accepted_max_session if accepted_max_session is not None else existing_max_session
                        avoid_after_to_save = (
                            bool(accepted_avoid_after)
                            if accepted_avoid_after is not None
                            else existing_avoid_after
                        )

                        save_ai_learning_preference(
                            student_id=student_id,
                            task_type=current_proposal["task_type"],
                            subject=current_proposal["subject"],
                            preference_text=accepted_preference_text,
                            add_time_buffer_percent=buffer_to_save,
                            preferred_energy=energy_to_save,
                            max_session_hours=max_session_to_save,
                            avoid_after_high_difficulty_task=avoid_after_to_save,
                            status="accepted"
                        )

                        finish_context_text = build_current_reflection_context(
                            subject=loaded_subject,
                            task_type=loaded_task_type
                        )

                        save_current_reflection_summary(finish_context_text)

                        st.session_state.pending_ai_preference_proposal = None
                        st.session_state.feedback_reflection_task_id = None
                        st.success("Suggestion saved for future similar tasks.")
                        st.rerun()

                with col_reject:
                    if st.button("Reject suggestion", key=f"reject_ai_preference_{active_reflection_task_id}"):
                        finish_context_text = build_current_reflection_context(
                            subject=loaded_subject,
                            task_type=loaded_task_type
                        )
                        save_current_reflection_summary(finish_context_text)

                        st.session_state.pending_ai_preference_proposal = None
                        st.session_state.feedback_reflection_task_id = None
                        st.info("Suggestion ignored.")
                        st.rerun()

            else:
                st.markdown("---")
                st.success(
                    "No planning adjustments seem necessary right now. "
                    "Your current study approach for similar tasks appears to work well. Keep it up!"
                )

                if st.button("Continue", key=f"continue_no_ai_preference_{active_reflection_task_id}"):
                    finish_context_text = build_current_reflection_context(
                        subject=loaded_subject,
                        task_type=loaded_task_type
                    )
                    save_current_reflection_summary(finish_context_text)

                    st.session_state.pending_ai_preference_proposal = None
                    st.session_state.feedback_reflection_task_id = None
                    st.rerun()

        else:
            user_messages = [
                row for row in displayed_rows
                if row[0] == "user"
            ]

            assistant_messages = [
                row for row in displayed_rows
                if row[0] == "assistant"
            ]

            latest_assistant_message = assistant_messages[-1][1] if assistant_messages else ""
            assistant_is_asking_question = "?" in latest_assistant_message

            if len(user_messages) > 0 and not assistant_is_asking_question:
                st.markdown("---")
                st.info("If the reflection feels complete, you can finish it and continue.")

                if st.button("Finish reflection", key=f"finish_reflection_{active_reflection_task_id}"):

                    finish_context_text = build_current_reflection_context(
                        subject=loaded_subject,
                        task_type=loaded_task_type
                    )

                    save_current_reflection_summary(finish_context_text)

                    create_pending_proposal(
                        proposal_task_id=active_reflection_task_id,
                        proposal_task_name=loaded_task_name,
                        proposal_subject=loaded_subject,
                        proposal_task_type=loaded_task_type,
                        proposal_context_text=finish_context_text
                    )

                    if st.session_state.get("pending_ai_preference_proposal") is None:
                        st.session_state.pending_ai_preference_proposal = {
                            "task_id": active_reflection_task_id,
                            "subject": loaded_subject,
                            "task_type": loaded_task_type,
                            "proposal_text": None,
                            "change_time_buffer": False,
                            "add_time_buffer_percent": 0,
                            "preferred_energy": None,
                            "max_session_hours": None,
                            "avoid_after_high_difficulty_task": False,
                            "reason": "No planning adjustment needed.",
                            "has_proposal": False
                        }

                    st.rerun()

    active_reflection_id = st.session_state.get("feedback_reflection_task_id")

    if active_reflection_id:
        render_ai_reflection_section(active_reflection_id)
        return

    tasks = get_tasks_for_student(student_id)
    active_tasks = [task for task in tasks if task[9] != "completed"]

    st.caption(
        "Give feedback after the planned study blocks for a task are finished. "
        "This feedback is about the whole task, not one separate study block.\n\n"
        "If the task is fully completed, the AI reflection coach will help the system learn from the experience. "
        "If the task is not completed after the planned work, enter the remaining hours so the planner can reschedule the extra work."
    )

    if not active_tasks:
        st.info("No active tasks available for feedback.")
        return

    task_options = {
        f"{task[0]} - {task[1]} ({task[9]})": task[0]
        for task in active_tasks
    }

    selected_task_label = st.selectbox("Select task", list(task_options.keys()))
    selected_task_id = task_options[selected_task_label]
    selected_feedback_task = get_task_by_id(selected_task_id)

    if not selected_feedback_task:
        st.warning("Selected task could not be loaded.")
        return

    (
        feedback_task_id,
        feedback_student_id,
        feedback_task_name,
        feedback_subject,
        feedback_task_type,
        feedback_importance_level,
        feedback_task_intensity,
        feedback_deadline,
        feedback_estimated_hours,
        feedback_adjusted_hours,
        feedback_status,
        feedback_is_spread_learning,
        feedback_preferred_study_days,
        feedback_min_session_hours,
        feedback_max_session_hours
    ) = selected_feedback_task

    spread_note = ""
    if bool(feedback_is_spread_learning) and feedback_task_type == "Study / Learning":
        spread_note = (
            f"<div style='margin-top:8px; color:#1d4ed8;'>"
            f"<b>Spread-learning task:</b> Yes"
            f"{f' | Preferred study days: {feedback_preferred_study_days}' if feedback_preferred_study_days is not None else ''}"
            f"{f' | Min session: {feedback_min_session_hours}h' if feedback_min_session_hours is not None else ''}"
            f"{f' | Max session: {feedback_max_session_hours}h' if feedback_max_session_hours is not None else ''}"
            f"</div>"
        )

    st.markdown(
        f"""
        <div class="block-card">
            <h4 style="margin-bottom:8px;">{feedback_task_name}</h4>
            <div style="margin-bottom:8px;">
                {importance_badge(feedback_importance_level)}
                {intensity_badge(feedback_task_intensity)}
                {status_badge(feedback_status)}
            </div>
            <div><b>Subject:</b> {feedback_subject}</div>
            <div><b>Task type:</b> {feedback_task_type}</div>
            <div><b>Deadline:</b> {feedback_deadline}</div>
            <div><b>Estimated hours:</b> {feedback_estimated_hours}</div>
            <div><b>Current remaining / plannable hours:</b> {feedback_adjusted_hours}</div>
            {spread_note}
        </div>
        """,
        unsafe_allow_html=True
    )

    feedback_mode = st.radio(
        "Feedback type",
        ["Worked on task", "Did not start task"],
        key=f"feedback_mode_{feedback_task_id}"
    )

    did_not_start = feedback_mode == "Did not start task"

    actual_hours = 0.0
    completed = False
    remaining_hours = float(feedback_adjusted_hours)

    mental_effort = None
    focus_level = None
    perceived_difficulty = None
    confidence_level = None

    if did_not_start:
        st.info(
            "Use this if you did not work on the task at all. "
            "The task stays open and can be replanned later."
        )
    else:
        col1, col2 = st.columns(2)

        with col1:
            actual_hours = st.number_input(
                "Actual hours worked in this session",
                min_value=0.0,
                max_value=200.0,
                value=1.0,
                step=0.25,
                key=f"actual_hours_{feedback_task_id}"
            )

        with col2:
            completed_choice = st.radio(
                "Is the entire task completed now?",
                ["No", "Yes"],
                horizontal=True,
                key=f"completed_choice_{feedback_task_id}"
            )

            st.caption(
                "Choose Yes only if the whole task is finished. "
                "Choose No if all planned study blocks are done, but the task still needs extra work."
            )
            completed = completed_choice == "Yes"

        if not completed:
            st.markdown("### Remaining work update")
            st.caption(
                "Use this only if the planned study blocks for this task are finished, "
                "but the task itself is still not completed. "
                "Enter how many extra hours are still needed so the planner can reschedule the remaining work."
            )

            remaining_hours = st.number_input(
                "Remaining hours after this session",
                min_value=0.0,
                max_value=200.0,
                value=max(float(feedback_adjusted_hours) - float(actual_hours), 0.0),
                step=0.5,
                key=f"remaining_hours_{feedback_task_id}"
            )

            mental_effort = st.slider(
                "How mentally demanding was this session? (1 = lowest, 5 = highest)",
                min_value=1,
                max_value=5,
                value=3,
                key=f"session_effort_{feedback_task_id}"
            )

            focus_level = st.slider(
                "How well could you focus during this session? (1 = lowest, 5 = highest)",
                min_value=1,
                max_value=5,
                value=3,
                key=f"session_focus_{feedback_task_id}"
            )

        else:
            remaining_hours = 0.0

            st.markdown("### Final learning reflection")
            st.caption(
                "These questions are only shown when the task is completed, "
                "so the reflection covers the whole task.\n\n"
                "Scale explanation:\n"
                "- 1 = lowest\n"
                "- 5 = highest"
            )

            perceived_difficulty = st.slider(
                "How difficult was this task overall? (1 = very easy, 5 = very difficult)",
                min_value=1,
                max_value=5,
                value=3,
                key=f"difficulty_{feedback_task_id}"
            )

            mental_effort = st.slider(
                "How much mental effort did this task require overall? (1 = very low, 5 = very high)",
                min_value=1,
                max_value=5,
                value=3,
                key=f"effort_{feedback_task_id}"
            )

            confidence_level = st.slider(
                "How confident did you feel about this task overall? (1 = very low, 5 = very high)",
                min_value=1,
                max_value=5,
                value=3,
                key=f"confidence_{feedback_task_id}"
            )

            focus_level = st.slider(
                "How well could you focus during this task overall? (1 = very low, 5 = very high)",
                min_value=1,
                max_value=5,
                value=3,
                key=f"focus_{feedback_task_id}"
            )


    pending_rebuild_id = st.session_state.get("pending_rebuild_task_id")
    show_rebuild_option = st.session_state.get("show_rebuild_option", False)

    if not (show_rebuild_option and pending_rebuild_id == feedback_task_id):

        if st.button("Submit Feedback", key=f"submit_feedback_{feedback_task_id}"):
            if not did_not_start:
                if float(actual_hours) <= 0:
                    st.warning("Please enter worked hours greater than 0, or choose 'Did not start task'.")
                    return

                if not completed and float(remaining_hours) <= 0:
                    st.warning("If the task is not completed, remaining hours must be greater than 0.")
                    return

            log_task_feedback(
                task_id=feedback_task_id,
                student_id=feedback_student_id,
                task_name=feedback_task_name,
                subject=feedback_subject,
                task_type=feedback_task_type,
                importance_level=feedback_importance_level,
                estimated_hours=float(feedback_estimated_hours),
                adjusted_hours=float(feedback_adjusted_hours),
                actual_hours=float(actual_hours),
                completed=completed,
                remaining_hours=float(remaining_hours),
                logged_at=datetime.now().isoformat(),
                did_not_start=did_not_start,
                perceived_difficulty=perceived_difficulty,
                mental_effort=mental_effort,
                confidence_level=confidence_level,
                focus_level=focus_level
            )

            st.session_state.pending_ai_preference_proposal = None

            if completed:
                current_context_text = build_current_reflection_context()

                existing_rows = get_ai_feedback_reflections(student_id, feedback_task_id)

                initial_chat_history = [
                    {"role": row[0], "content": row[1]}
                    for row in existing_rows
                ]

                ai_reflection = generate_feedback_reflection(
                    task_name=feedback_task_name,
                    subject=feedback_subject,
                    task_type=feedback_task_type,
                    estimated_hours=float(feedback_estimated_hours),
                    adjusted_hours=float(feedback_adjusted_hours),
                    actual_hours=float(actual_hours),
                    remaining_hours=0.0,
                    completed=True,
                    perceived_difficulty=perceived_difficulty,
                    mental_effort=mental_effort,
                    confidence_level=confidence_level,
                    focus_level=focus_level,
                    student_context=current_context_text,
                    chat_history=initial_chat_history
                )

                save_ai_feedback_reflection(
                    student_id=student_id,
                    task_id=feedback_task_id,
                    role="assistant",
                    content=ai_reflection
                )

                st.session_state.feedback_reflection_task_id = feedback_task_id

                create_pending_proposal(
                    proposal_task_id=feedback_task_id,
                    proposal_task_name=feedback_task_name,
                    proposal_subject=feedback_subject,
                    proposal_task_type=feedback_task_type,
                    proposal_context_text=current_context_text
                )

            else:
                st.session_state.feedback_reflection_task_id = None

            st.session_state.generated_plan = None
            st.session_state.ai_study_advice = None
            st.session_state.llm_chat_history = []

            if completed:
                st.session_state.show_rebuild_option = False
                st.session_state.pending_rebuild_task_id = None
                st.success(f"Final feedback for task '{feedback_task_name}' submitted successfully.")
            else:
                st.session_state.show_rebuild_option = True
                st.session_state.pending_rebuild_task_id = feedback_task_id

                if did_not_start:
                    st.success(
                        f"You indicated that you did not start '{feedback_task_name}'. "
                        f"The task remains open for replanning."
                    )
                else:
                    st.success(
                        f"Session feedback for task '{feedback_task_name}' submitted successfully."
                    )

            st.rerun()

    if show_rebuild_option and pending_rebuild_id == feedback_task_id:
        st.info("Feedback has already been submitted for this task.")
        st.info("You can rebuild your study plan to schedule the remaining work.")

        st.warning(
            "Your current saved study plan will be replaced. "
            "Future study blocks may be rescheduled based on your progress."
        )

        confirm_key = f"confirm_rebuild_{feedback_task_id}"

        if confirm_key not in st.session_state:
            st.session_state[confirm_key] = False

        if not st.session_state[confirm_key]:
            if st.button("Rebuild Study Plan now", key=f"rebuild_plan_btn_{feedback_task_id}"):
                st.session_state[confirm_key] = True
                st.rerun()

        if st.session_state[confirm_key]:
            st.warning(
                "⚠ Are you sure you want to rebuild your study plan?\n\n"
                "Your current saved plan will be replaced and upcoming study blocks may change."
            )

            col_rebuild_yes, col_rebuild_cancel = st.columns(2)

            with col_rebuild_yes:
                if st.button("Yes, rebuild plan", key=f"confirm_yes_{feedback_task_id}"):
                    plan_result = build_study_plan(student_id)
                    st.session_state.generated_plan = plan_result

                    if plan_result["daily_plan"]:
                        save_study_plan(student_id, plan_result["daily_plan"])

                    st.session_state[confirm_key] = False
                    st.session_state.show_rebuild_option = False
                    st.session_state.pending_rebuild_task_id = None

                    st.success("Study plan successfully rebuilt based on your updated progress.")
                    st.rerun()

            with col_rebuild_cancel:
                if st.button("Cancel", key=f"confirm_cancel_{feedback_task_id}"):
                    st.session_state[confirm_key] = False
                    st.session_state.show_rebuild_option = False
                    st.session_state.pending_rebuild_task_id = None
                    st.rerun()



def render_history_page(student_id: str):
    st.title("Task History")

    history = get_history_for_student(student_id)

    if not history:
        st.info("No task history available yet.")
        return

    grouped_history = group_history_by_task(history)

    tab1, tab2 = st.tabs(["Task Overview", "Feedback Log"])

    with tab1:
        st.markdown("### Task Overview")

        col1, col2, col3 = st.columns(3)

        with col1:
            subject_filter = st.selectbox(
                "Filter by subject",
                ["All"] + sorted(list(set(item["subject"] for item in grouped_history))),
                key="history_subject_filter"
            )

        with col2:
            task_type_filter = st.selectbox(
                "Filter by task type",
                ["All"] + sorted(list(set(item["task_type"] for item in grouped_history))),
                key="history_task_type_filter"
            )

        with col3:
            status_filter = st.selectbox(
                "Filter by status",
                ["All", "Completed only", "Open / Partial only"],
                key="history_status_filter"
            )

        filtered_history = grouped_history

        if task_type_filter != "All":
            filtered_history = [item for item in filtered_history if item["task_type"] == task_type_filter]

        if subject_filter != "All":
            filtered_history = [item for item in filtered_history if item["subject"] == subject_filter]

        if status_filter == "Completed only":
            filtered_history = [item for item in filtered_history if item["completed"] is True]
        elif status_filter == "Open / Partial only":
            filtered_history = [item for item in filtered_history if item["completed"] is False]

        st.markdown("---")

        if filtered_history:
            for item in filtered_history:
                status_html = (
                    '<span class="badge badge-completed">Completed</span>'
                    if item["completed"]
                    else '<span class="badge badge-incomplete">Open / Partial</span>'
                )

                st.markdown(
                    f"""
                    <div class="block-card">
                        <h4 style="margin-bottom:8px;">{item['task_name']}</h4>
                        <div style="margin-bottom:8px;">
                            {importance_badge(item['importance_level'])}
                            {status_html}
                        </div>
                        <div><b>Subject:</b> {item['subject']}</div>
                        <div><b>Task type:</b> {item['task_type']}</div>
                        <div><b>Estimated:</b> {item['estimated_hours']} h</div>
                        <div><b>Total actual worked:</b> {round(item['total_actual_hours'], 2)} h</div>
                        <div><b>Latest remaining:</b> {round(item['latest_remaining_hours'], 2)} h</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No task overview matches the selected filters.")

    with tab2:
        st.markdown("### Feedback Log")

        col1, col2 = st.columns(2)

        with col1:
            feedback_subject_options = ["All"] + sorted(list(set(row[2] for row in history)))
            feedback_subject_filter = st.selectbox(
                "Filter feedback by subject",
                feedback_subject_options,
                key="feedback_log_subject_filter"
            )

        with col2:
            feedback_type_options = ["All"] + sorted(list(set(row[3] for row in history)))
            feedback_type_filter = st.selectbox(
                "Filter feedback by task type",
                feedback_type_options,
                key="feedback_log_task_type_filter"
            )

        filtered_feedback = history

        if feedback_type_filter != "All":
            filtered_feedback = [row for row in filtered_feedback if row[3] == feedback_type_filter]

        if feedback_subject_filter != "All":
            filtered_feedback = [row for row in filtered_feedback if row[2] == feedback_subject_filter]

        st.markdown("---")

        if filtered_feedback:
            for row in filtered_feedback:
                (
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
                    logged_at
                ) = row

                render_history_card(
                    task_name=task_name,
                    subject=subject,
                    task_type=task_type,
                    importance=importance_level,
                    estimated=estimated_hours,
                    adjusted=adjusted_hours,
                    actual=actual_hours,
                    completed=completed,
                    remaining=remaining_hours
                )
        else:
            st.info("No feedback logs match the selected filters.")


def render_help_page():
    st.title("How to use this app")

    st.info("This page walks you through the app step by step, so you know exactly where to start and what to do next.")

    st.markdown("---")

    st.header("Step 1: Add your subjects")
    st.markdown("""
    Start by adding the subjects or courses you are currently working on.

    You do this in **Planning Setup** under **Task Setup**.  
    At the top of that section, you can add your subjects and manage them.

    This is helpful because:
    - you only need to add a subject once
    - you can select it later when creating tasks
    - it keeps your data clean and avoids spelling mistakes
    """)

    st.markdown("---")

    st.header("Step 2: Add your tasks")
    st.markdown("""
    After adding your subjects, you can start creating tasks.

    For each task, you fill in:
    - **Task name**: what you need to do
    - **Subject / Course**: choose one of your saved subjects
    - **Task type**: for example Reading, Practice, Writing, or Review
    - **Estimated hours**: your own estimate of how long the task will take
    - **Importance level**: how important the task is
    - **Deadline**: when the task needs to be finished

    Try to be as realistic as possible when entering your task.  
    You can always give feedback later if the task took more or less time than expected.
    """)

    st.markdown("---")

    st.header("Step 3: Set your daily context")
    st.markdown("""
    Before the app can build a study plan, it needs to know what your days look like.

    In **Planning Setup**, go to **Daily Context Setup** and enter:
    - when you wake up
    - when you go to sleep
    - which parts of your day are already filled with activities

    Activities can be things like:
    - work
    - social activities
    - physical activity
    - rest
    - other fixed plans

    The app uses the remaining free time as possible study time.

    This helps the planner make a schedule that fits around your real life, instead of creating an unrealistic plan.
    """)

    st.markdown("---")

    st.header("Step 4: Generate your study plan")
    st.markdown("""
    Once your tasks and daily context are ready, go to **Generate Study Plan**.

    Then click **Build Study Plan**.

    The app will create a study plan based on:
    - your tasks
    - your deadlines
    - your available time
    - your daily activities
    - your task types
    - your feedback history and cognitive data, when available

    After generating the plan, it is also saved automatically.
    """)

    st.markdown("---")

    st.header("Step 5: Review your saved plan")
    st.markdown("""
    In the saved plan, you can see how your work has been scheduled over time.

    You may notice that:
    - tasks are split across different moments
    - breaks are added automatically
    - some tasks are scheduled earlier or in stronger time slots

    This is normal.  
    The app tries to create a realistic and manageable plan instead of just filling every hour with work.
    """)

    st.markdown("---")

    st.header("Step 6: Log feedback after studying")
    st.markdown("""
    After working on a task, go to the **Feedback** page.

    There, you can tell the system:
    - how many hours you actually worked
    - whether you completed the task
    - how many hours are still remaining, if it is not finished

    You may also be asked short reflection questions, such as:
    - how difficult the task felt
    - how much mental effort it required
    - how confident you felt
    - how well you could focus

    This feedback helps the system understand your study behavior better over time.
    """)

    st.markdown("---")

    st.header("Step 7: Repeat the cycle")
    st.markdown("""
    The app works best when you use it as a cycle:

    1. add subjects  
    2. add tasks  
    3. set your daily context  
    4. generate a plan  
    5. study  
    6. log feedback  
    7. generate a new plan when needed  

    This means the app becomes more useful the more consistently you use it.
    """)

    st.markdown("---")

    st.header("AI Study Coach")
    st.markdown("""
    You can use the **AI Study Coach** to ask questions about your plan.

    For example, you can ask:
    - Is this plan realistic?
    - Why is this task scheduled here?
    - Why did this task get more time?
    - What should I focus on first?
    """)

    st.markdown("---")

    st.header("Helpful tip")
    st.markdown("""
    If you are using the app for the first time, the easiest order is:

    **Subjects → Tasks → Daily Context → Generate Plan → Feedback**

    Following that order makes the process much smoother.
    """)

    st.markdown("---")
    st.header("AI Help Assistant")
    st.markdown("You can also ask questions here about how to use the app.")

    if "help_chat_history" not in st.session_state:
        st.session_state.help_chat_history = []

    for msg in st.session_state.help_chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    help_user_message = st.chat_input(
        "Ask a question about how the app works",
        key="help_chat_input"
    )

    if help_user_message:
        st.session_state.help_chat_history.append({
            "role": "user",
            "content": help_user_message
        })

        with st.chat_message("user"):
            st.markdown(help_user_message)

        help_response = chat_with_system_guide(
            chat_history=st.session_state.help_chat_history,
            user_message=help_user_message
        )

        st.session_state.help_chat_history.append({
            "role": "assistant",
            "content": help_response
        })

        with st.chat_message("assistant"):
            st.markdown(help_response)


# -----------------------------
# Admin pages
# -----------------------------
def render_admin_dashboard():
    st.title("Admin Dashboard")

    global_summary = get_admin_global_summary()
    per_student_summary = get_admin_summary_per_student()
    students = get_all_students()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registered students", len(students))
    col2.metric("Students with feedback", global_summary["students_with_feedback"])
    col3.metric("Tasks analysed", global_summary["tasks_compared"])
    col4.metric("Average estimation error", f"{global_summary['avg_estimation_error']} h")

    st.markdown("---")

    top1, top2, top3 = st.columns(3)
    top1.metric("Underestimated tasks", global_summary["underestimated"])
    top2.metric("Overestimated tasks", global_summary["overestimated"])
    top3.metric("Accurately estimated tasks", global_summary["accurate"])

    st.markdown("### Global estimation pattern overview")
    chart_df = pd.DataFrame([
        {"metric": "Underestimated", "count": global_summary["underestimated"]},
        {"metric": "Overestimated", "count": global_summary["overestimated"]},
        {"metric": "Accurate", "count": global_summary["accurate"]}
    ])
    st.bar_chart(chart_df.set_index("metric"))

    st.markdown("---")
    st.markdown("## Per Student Estimation Summary")

    if per_student_summary:
        per_student_df = pd.DataFrame(per_student_summary)

        rename_map = {
            "student_id": "Student ID",
            "student_name": "Name",
            "tasks_compared": "Tasks analysed",
            "underestimated": "Underestimated",
            "overestimated": "Overestimated",
            "accurate": "Accurate",
            "avg_estimation_error": "Average error (h)",
            "avg_estimation_ratio": "Average ratio"
        }

        display_df = per_student_df.rename(columns=rename_map)
        st.dataframe(display_df, width="stretch", hide_index=True)

        render_csv_download(
            per_student_df,
            "admin_per_student_summary.csv",
            "Download per student summary as CSV"
        )

        st.markdown("### Average estimation error per student")

        error_chart_df = per_student_df[
            ["student_name", "avg_estimation_error"]
        ].set_index("student_name")

        st.bar_chart(error_chart_df)

        st.markdown("### Average estimation ratio per student")

        ratio_chart_df = per_student_df[
            ["student_name", "avg_estimation_ratio"]
        ].set_index("student_name")

        st.bar_chart(ratio_chart_df)
    else:
        st.info("No student feedback data available yet.")


# ------------------------
# Downloading CSV
# ------------------------

def render_csv_download(df: pd.DataFrame, filename: str, label: str):
    if df.empty:
        return

    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv_data,
        file_name=filename,
        mime="text/csv"
    )


def render_admin_detailed_page():
    st.title("Detailed Estimation Analysis")

    students = get_all_students()

    if not students:
        st.info("No students registered yet.")
        return

    student_options = [f"{student_id} - {name}" for student_id, name, is_active in students]
    selected_student = st.selectbox("Select student", student_options)
    selected_student_id = selected_student.split(" - ")[0]

    selected_summary = get_estimation_accuracy_summary(selected_student_id)
    selected_rows = get_estimation_accuracy_for_student(selected_student_id)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Tasks analysed", selected_summary["total_tasks_compared"])
    col2.metric("Underestimated", selected_summary["underestimated"])
    col3.metric("Overestimated", selected_summary["overestimated"])
    col4.metric("Accurate", selected_summary["accurate"])
    col5.metric("Average error", f"{selected_summary['avg_estimation_error']} h")

    st.markdown("---")

    if selected_rows:
        rows_df = pd.DataFrame(selected_rows)

        # Filters
        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            task_type_options = ["All"] + sorted(rows_df["task_type"].dropna().unique().tolist())
            selected_task_type = st.selectbox("Filter by task type", task_type_options, key="admin_detail_task_type")

        with filter_col2:
            pattern_options = ["All"] + sorted(rows_df["pattern"].dropna().unique().tolist())
            selected_pattern = st.selectbox("Filter by pattern", pattern_options, key="admin_detail_pattern")

        filtered_df = rows_df.copy()

        if selected_task_type != "All":
            filtered_df = filtered_df[filtered_df["task_type"] == selected_task_type]

        if selected_pattern != "All":
            filtered_df = filtered_df[filtered_df["pattern"] == selected_pattern]

        # Export
        render_csv_download(
            filtered_df,
            f"detailed_estimation_analysis_{selected_student_id}.csv",
            "Download filtered analysis as CSV"
        )

        chart_df = filtered_df[
            ["task_name", "estimated_hours", "adjusted_hours", "actual_total_hours"]
        ].copy()

        if not chart_df.empty:
            chart_df = chart_df.set_index("task_name")
            st.markdown("### Estimate vs actual workload")
            st.bar_chart(chart_df)

        st.markdown("---")
        st.markdown("### Task-level estimation details")

        for _, row in filtered_df.iterrows():
            st.markdown(
                f"""
                <div class="block-card">
                    <h4 style="margin-bottom:8px;">{row['task_name']}</h4>
                    <div style="margin-bottom:8px;">
                        {importance_badge(row['importance_level'])}
                        {status_badge(row['status'])}
                    </div>
                    <div><b>Task type:</b> {row['task_type']}</div>
                    <div><b>Original student estimate:</b> {row['estimated_hours']} h</div>
                    <div><b>Current remaining / plannable hours:</b> {row['adjusted_hours']} h</div>
                    <div><b>Total actual workload:</b> {row['actual_total_hours']} h</div>
                    <div><b>Absolute estimation error:</b> {row['estimation_error']} h</div>
                    <div><b>Estimation ratio:</b> {row['estimation_ratio']}</div>
                    <div style="margin-top:8px;"><b>Pattern:</b> {row['pattern']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("No task data available for this student.")


def render_admin_account_management():
    st.title("Student Account Management")

    students = get_all_students()

    if not students:
        st.info("No students registered yet.")
        return

    st.markdown("### All student accounts")

    for student_id, name, is_active in students:
        st.markdown(
            f"""
            <div class="soft-card">
                <b>{name}</b> ({student_id})<br>
                {student_active_badge(bool(is_active))}
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.subheader("Manage account")

    student_options = [f"{student_id} - {name}" for student_id, name, is_active in students]
    selected_student = st.selectbox("Select student account", student_options)
    selected_student_id = selected_student.split(" - ")[0]

    selected_row = next((row for row in students if row[0] == selected_student_id), None)

    if selected_row:
        _, selected_name, selected_is_active = selected_row

        st.markdown(
            f"""
            <div class="block-card">
                <h4 style="margin-bottom:8px;">{selected_name}</h4>
                <div><b>Student ID:</b> {selected_student_id}</div>
                <div style="margin-top:8px;">{student_active_badge(bool(selected_is_active))}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)

        with col1:
            if selected_is_active:
                if st.button("Set account to inactive"):
                    deactivate_student(selected_student_id)
                    st.success("Student account set to inactive.")
                    st.rerun()
            else:
                if st.button("Reactivate account"):
                    activate_student(selected_student_id)
                    st.success("Student account reactivated.")
                    st.rerun()

        with col2:
            confirm_delete_account = st.checkbox(
                "I understand this permanently deletes the student account and all related data",
                key="confirm_delete_student_account"
            )

            if st.button("Permanently delete account"):
                if not confirm_delete_account:
                    st.warning("Please confirm permanent deletion first.")
                else:
                    delete_student_account(selected_student_id)
                    st.success("Student account permanently deleted.")
                    st.rerun()


def render_admin_task_type_analysis():
    st.title("Task Type Analysis")

    rows = get_task_type_analysis()

    if not rows:
        st.info("No task type analysis data available yet.")
        return

    df = pd.DataFrame(rows)

    # Filter
    task_type_options = ["All"] + sorted(df["task_type"].dropna().unique().tolist())
    selected_task_type = st.selectbox("Filter by task type", task_type_options, key="task_type_analysis_filter")

    filtered_df = df.copy()
    if selected_task_type != "All":
        filtered_df = filtered_df[filtered_df["task_type"] == selected_task_type]

    # Export
    render_csv_download(
        filtered_df,
        "task_type_analysis.csv",
        "Download task type analysis as CSV"
    )

    st.markdown("### Overview per task type")
    st.dataframe(filtered_df, width="stretch", hide_index=True)

    if not filtered_df.empty:
        chart_df = filtered_df[
            ["task_type", "avg_estimated_hours", "avg_adjusted_hours", "avg_actual_hours"]
        ].set_index("task_type")

        st.markdown("### Average workload per task type")
        st.bar_chart(chart_df)


def render_admin_subject_analysis():
    st.title("Subject Analysis")

    rows = get_subject_analysis()

    if not rows:
        st.info("No subject analysis data available yet.")
        return

    df = pd.DataFrame(rows)

    # Filter
    subject_options = ["All"] + sorted(df["subject"].dropna().unique().tolist())
    selected_subject = st.selectbox("Filter by subject", subject_options, key="subject_analysis_filter")

    filtered_df = df.copy()
    if selected_subject != "All":
        filtered_df = filtered_df[filtered_df["subject"] == selected_subject]

    # Export
    render_csv_download(
        filtered_df,
        "subject_analysis.csv",
        "Download subject analysis as CSV"
    )

    st.markdown("### Overview per subject")
    st.dataframe(filtered_df, width="stretch", hide_index=True)

    if not filtered_df.empty:
        chart_df = filtered_df[[
            "subject",
            "avg_estimated_hours",
            "avg_adjusted_hours",
            "avg_actual_hours"
        ]].set_index("subject")

        st.markdown("### Average workload per subject")
        st.bar_chart(chart_df)

        cognitive_df = filtered_df[[
            "subject",
            "avg_difficulty",
            "avg_mental_effort",
            "avg_confidence",
            "avg_focus"
        ]].set_index("subject")

        st.markdown("### Average cognitive profile per subject")
        st.bar_chart(cognitive_df)


def render_admin_learning_profiles():
    st.title("Learning Profiles")

    rows = get_all_learning_profiles()

    if not rows:
        st.info("No learning profiles available yet.")
        return

    df = pd.DataFrame(rows, columns=[
        "student_id",
        "student_name",
        "task_type",
        "subject",
        "planning_factor",
        "feedback_count",
        "avg_difficulty",
        "avg_mental_effort",
        "avg_confidence",
        "avg_focus",

    ])

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        student_options = ["All"] + sorted(df["student_id"].dropna().unique().tolist())
        selected_student = st.selectbox("Filter by student", student_options, key="learning_profiles_student_filter")

    with col2:
        task_type_options = ["All"] + sorted(df["task_type"].dropna().unique().tolist())
        selected_task_type = st.selectbox("Filter by task type", task_type_options,
                                          key="learning_profiles_task_type_filter")

    with col3:
        subject_options = ["All"] + sorted(df["subject"].dropna().unique().tolist())
        selected_subject = st.selectbox("Filter by subject", subject_options, key="learning_profiles_subject_filter")

    filtered_df = df.copy()

    if selected_student != "All":
        filtered_df = filtered_df[filtered_df["student_id"] == selected_student]

    if selected_task_type != "All":
        filtered_df = filtered_df[filtered_df["task_type"] == selected_task_type]

    if selected_subject != "All":
        filtered_df = filtered_df[filtered_df["subject"] == selected_subject]

    # Export
    render_csv_download(
        filtered_df,
        "learning_profiles.csv",
        "Download learning profiles as CSV"
    )

    st.markdown("### Personal learning profiles per student, task type, and subject")
    st.dataframe(filtered_df, width="stretch", hide_index=True)

    if not filtered_df.empty:
        chart_df = filtered_df[[
            "task_type",
            "planning_factor",
            "avg_difficulty",
            "avg_mental_effort",
            "avg_confidence",
            "avg_focus"
        ]].copy()

        grouped_df = chart_df.groupby("task_type", as_index=True).mean(numeric_only=True)

        st.markdown("### Average profile signals by task type")
        st.bar_chart(grouped_df)


# -----------------------------
# Sidebar + routing
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
                    if len(student) >= 3 and student[2] is False:
                        st.error("This account is inactive. Please contact the admin.")
                    else:
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

        reflection_required = (
                st.session_state.get("feedback_reflection_task_id") is not None
        )

        if reflection_required:
            st.sidebar.warning(
                "Please respond to the AI reflection suggestion before navigating elsewhere."
            )

            student_page = "Feedback"

            st.sidebar.radio(
                "Student menu",
                ["Feedback"],
                index=0,
                disabled=True
            )
        else:
            student_page = st.sidebar.radio(
                "Student menu",
                ["Dashboard", "Planning Setup", "Saved Plan", "Feedback", "History", "Help"]
            )

        if student_page == "Dashboard":
            render_student_dashboard_home(
                st.session_state.student_id,
                st.session_state.student_name or "Student"
            )
        elif student_page == "Planning Setup":
            render_planning_setup_page(st.session_state.student_id)
        elif student_page == "Saved Plan":
            render_saved_plan_page(st.session_state.student_id)
        elif student_page == "Feedback":
            render_feedback_page(st.session_state.student_id)
        elif student_page == "History":
            render_history_page(st.session_state.student_id)
        elif student_page == "Help":
            render_help_page()

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

        st.title("Admin Menu")

        admin_tab_dashboard, admin_tab_detail, admin_tab_task_type, admin_tab_subject, admin_tab_learning, admin_tab_accounts = st.tabs(
            [
                "Dashboard",
                "Detailed Analysis",
                "Task Types",
                "Subjects",
                "Learning Profiles",
                "Student Accounts"
            ])

        with admin_tab_dashboard:
            render_admin_dashboard()

        with admin_tab_detail:
            render_admin_detailed_page()

        with admin_tab_task_type:
            render_admin_task_type_analysis()

        with admin_tab_subject:
            render_admin_subject_analysis()

        with admin_tab_learning:
            render_admin_learning_profiles()

        with admin_tab_accounts:
            render_admin_account_management()

