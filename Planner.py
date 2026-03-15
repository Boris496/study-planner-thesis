from datetime import date, datetime, timedelta
from typing import Dict, List

from Database import get_plannable_tasks_for_student, get_availability_for_range


IMPORTANCE_RANK = {
    "High": 0,
    "Medium": 1,
    "Low": 2
}


def daterange(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def build_study_plan(student_id: str):
    tasks = get_plannable_tasks_for_student(student_id)

    if not tasks:
        return {
            "daily_plan": {},
            "unscheduled_tasks": [],
            "planning_start": None,
            "planning_end": None,
            "total_required_hours": 0.0,
            "total_available_hours": 0.0
        }

    today = date.today()

    parsed_deadlines = []
    for task in tasks:
        deadline_obj = datetime.strptime(task[4], "%Y-%m-%d").date()
        effective_deadline = max(deadline_obj, today)
        parsed_deadlines.append(effective_deadline)

    planning_start = today
    planning_end = max(parsed_deadlines)

    availability_rows = get_availability_for_range(
        student_id=student_id,
        start_date=planning_start.isoformat(),
        end_date=planning_end.isoformat()
    )

    availability_map = {row[0]: row[1] for row in availability_rows}

    remaining_day_hours: Dict[str, float] = {}
    daily_plan: Dict[str, List[dict]] = {}

    for day in daterange(planning_start, planning_end):
        day_str = day.isoformat()
        remaining_day_hours[day_str] = float(availability_map.get(day_str, 0.0))
        daily_plan[day_str] = []

    sortable_tasks = []
    total_required_hours = 0.0

    for task in tasks:
        (
            task_id,
            task_name,
            task_type,
            importance_level,
            deadline,
            estimated_hours,
            adjusted_hours,
            status
        ) = task

        deadline_obj = datetime.strptime(deadline, "%Y-%m-%d").date()
        effective_deadline = max(deadline_obj, today)

        total_required_hours += float(adjusted_hours)

        sortable_tasks.append({
            "task_id": task_id,
            "task_name": task_name,
            "task_type": task_type,
            "importance_level": importance_level,
            "deadline": effective_deadline,
            "estimated_hours": float(estimated_hours),
            "adjusted_hours": float(adjusted_hours),
            "status": status
        })

    sortable_tasks.sort(
        key=lambda t: (
            t["deadline"],
            IMPORTANCE_RANK.get(t["importance_level"], 99),
            -t["adjusted_hours"]
        )
    )

    total_available_hours = round(sum(remaining_day_hours.values()), 2)
    unscheduled_tasks = []

    for task in sortable_tasks:
        remaining_task_hours = float(task["adjusted_hours"])

        for day in daterange(planning_start, task["deadline"]):
            if remaining_task_hours <= 0:
                break

            day_str = day.isoformat()
            available_today = remaining_day_hours.get(day_str, 0.0)

            if available_today <= 0:
                continue

            allocated = min(available_today, remaining_task_hours)

            daily_plan[day_str].append({
                "task_id": task["task_id"],
                "task_name": task["task_name"],
                "task_type": task["task_type"],
                "importance_level": task["importance_level"],
                "hours": round(allocated, 2),
                "deadline": task["deadline"].isoformat()
            })

            remaining_day_hours[day_str] = round(available_today - allocated, 2)
            remaining_task_hours = round(remaining_task_hours - allocated, 2)

        if remaining_task_hours > 0:
            unscheduled_tasks.append({
                "task_id": task["task_id"],
                "task_name": task["task_name"],
                "remaining_hours": round(remaining_task_hours, 2),
                "deadline": task["deadline"].isoformat(),
                "importance_level": task["importance_level"]
            })

    daily_plan = {
        day: items for day, items in daily_plan.items() if items
    }

    return {
        "daily_plan": daily_plan,
        "unscheduled_tasks": unscheduled_tasks,
        "planning_start": planning_start.isoformat(),
        "planning_end": planning_end.isoformat(),
        "total_required_hours": round(total_required_hours, 2),
        "total_available_hours": total_available_hours
    }