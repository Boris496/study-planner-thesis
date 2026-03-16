from google import genai
import streamlit as st


def get_client():
    return genai.Client(api_key=st.secrets["AIzaSyC31HNgztpRYUQ3JxZyP1qUxIrYthUgGPw"])


def _format_daily_plan(daily_plan: dict) -> str:
    if not daily_plan:
        return "No daily plan was generated."

    lines = []
    for study_day, items in daily_plan.items():
        lines.append(f"{study_day}:")
        for item in items:
            lines.append(
                f"- {item['task_name']} | type: {item['task_type']} | "
                f"importance: {item['importance_level']} | "
                f"hours: {item['hours']} | deadline: {item['deadline']}"
            )
    return "\n".join(lines)


def _format_unscheduled_tasks(unscheduled_tasks: list) -> str:
    if not unscheduled_tasks:
        return "No unscheduled tasks."

    lines = []
    for item in unscheduled_tasks:
        lines.append(
            f"- {item['task_name']} | remaining_hours: {item['remaining_hours']} | "
            f"deadline: {item['deadline']} | importance: {item['importance_level']}"
        )
    return "\n".join(lines)


def generate_plan_feedback(student_name: str, plan_result: dict) -> str:
    client = get_client()

    daily_plan_text = _format_daily_plan(plan_result.get("daily_plan", {}))
    unscheduled_tasks_text = _format_unscheduled_tasks(plan_result.get("unscheduled_tasks", []))
    total_required_hours = plan_result.get("total_required_hours", 0.0)
    total_available_hours = plan_result.get("total_available_hours", 0.0)
    planning_start = plan_result.get("planning_start", "N/A")
    planning_end = plan_result.get("planning_end", "N/A")

    prompt = f"""
You are an academic study planning assistant helping a university student.

Student name: {student_name}

Planning period:
- Start: {planning_start}
- End: {planning_end}

Workload summary:
- Total required hours: {total_required_hours}
- Total available hours: {total_available_hours}

Generated daily plan:
{daily_plan_text}

Unscheduled tasks:
{unscheduled_tasks_text}

Please provide:
1. A short summary of the study plan
2. Whether the workload seems realistic
3. Three practical study recommendations
4. A warning if the workload is too high
5. If there are unscheduled tasks, explain clearly what the student should do

Keep the answer:
- supportive
- practical
- concise
- easy for a student to understand
"""

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt
    )

    return response.text