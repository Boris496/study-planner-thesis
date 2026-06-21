from datetime import date, datetime, timedelta
from typing import Dict, List
import math
from zoneinfo import ZoneInfo

import Database

DEFAULT_WAKE_TIME = "07:00"
DEFAULT_SLEEP_TIME = "23:00"

DAY_LIMIT_HOURS = 7.0
PREFERRED_COGNITIVE_LIMIT_HOURS = 5.0
MAX_STUDY_BLOCK_HOURS = 1.5
BREAK_DURATION_HOURS = 0.33
MIN_BLOCK_HOURS = 0.25
RECOVERY_AFTER_LOW_ENERGY_HOURS = 1.0

IMPORTANCE_RANK = {
    "High": 0,
    "Medium": 1,
    "Low": 2
}

ENERGY_BY_REASON = {
    "Work/School": "Low",
    "Physical activity": "Medium",
    "Social": "Medium",
    "Rest": "High",
    "Study-free day": "High",
    "Other": "Medium"
}

ALLOWED_INTENSITIES = {
    "Low": {"Low", "Medium"},
    "Medium": {"Low", "Medium", "High"},
    "High": {"Low", "Medium", "High"}
}

TASK_TYPE_TO_INTENSITY = {
    "Study / Learning": "High",
    "Reading": "Medium",
    "Practice": "High",
    "Writing": "High",
    "Review": "Low",
    "Administrative": "Low"
}

VALID_TASK_TYPES = set(TASK_TYPE_TO_INTENSITY.keys())

COGNITIVE_TASK_TYPES = {
    "Study / Learning",
    "Practice",
    "Writing"
    }

def daterange(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)

def _calculate_slot_hours(start_time_str: str, end_time_str: str) -> float:
    start_dt = datetime.strptime(start_time_str, "%H:%M")
    end_dt = datetime.strptime(end_time_str, "%H:%M")
    return round((end_dt - start_dt).seconds / 3600, 2)

def _add_hours_to_time(time_str: str, hours: float) -> str:
    start_dt = datetime.strptime(time_str, "%H:%M")
    end_dt = start_dt + timedelta(hours=hours)
    return end_dt.strftime("%H:%M")

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

def _merge_overlapping_blocks(blocks: List[dict]) -> List[dict]:
    if not blocks:
        return []

    sorted_blocks = sorted(blocks, key=lambda x: x["start_time"])
    merged = [sorted_blocks[0].copy()]

    for current in sorted_blocks[1:]:
        last = merged[-1]

        if current["start_time"] <= last["end_time"]:
            if current["end_time"] > last["end_time"]:
                last["end_time"] = current["end_time"]

            last["reason"] = current["reason"]
        else:
            merged.append(current.copy())

    return merged

def _append_free_slot_with_recovery(free_slots, day_str, start_time, end_time, energy_level):
    hours = _calculate_slot_hours(start_time, end_time)

    if hours <= 0:
        return

    if energy_level == "Low" and hours > RECOVERY_AFTER_LOW_ENERGY_HOURS:
        recovery_end = _add_hours_to_time(start_time, RECOVERY_AFTER_LOW_ENERGY_HOURS)

        free_slots.append({
            "study_date": day_str,
            "start_time": start_time,
            "end_time": recovery_end,
            "remaining_hours": RECOVERY_AFTER_LOW_ENERGY_HOURS,
            "energy_level": "Low"
        })

        remaining_hours = _calculate_slot_hours(recovery_end, end_time)

        if remaining_hours > 0:
            free_slots.append({
                "study_date": day_str,
                "start_time": recovery_end,
                "end_time": end_time,
                "remaining_hours": remaining_hours,
                "energy_level": "Medium"
            })

    else:
        free_slots.append({
            "study_date": day_str,
            "start_time": start_time,
            "end_time": end_time,
            "remaining_hours": hours,
            "energy_level": energy_level
        })

def _build_day_free_slots(day_str: str, wake_time: str, sleep_time: str, day_activities: List[dict]) -> List[dict]:
    free_slots = []

    current_start = wake_time
    current_energy = "High"

    merged_activities = _merge_overlapping_blocks(day_activities)

    for activity in merged_activities:
        act_start = activity["start_time"]
        act_end = activity["end_time"]
        reason = activity["reason"]

        if act_end <= wake_time or act_start >= sleep_time:
            continue

        clipped_start = max(act_start, wake_time)
        clipped_end = min(act_end, sleep_time)

        if current_start < clipped_start:
            hours = _calculate_slot_hours(current_start, clipped_start)
            if hours > 0:
                _append_free_slot_with_recovery(
                    free_slots,
                    day_str,
                    current_start,
                    clipped_start,
                    current_energy
                )

        if clipped_end > current_start:
            current_start = clipped_end
            current_energy = ENERGY_BY_REASON.get(reason, "Medium")

    if current_start < sleep_time:
        hours = _calculate_slot_hours(current_start, sleep_time)
        if hours > 0:
            _append_free_slot_with_recovery(
                free_slots,
                day_str,
                current_start,
                sleep_time,
                current_energy
            )

    return free_slots

def _is_study_free_day(day_activities: List[dict]) -> bool:
    return any(
        activity.get("reason") == "Study-free day"
        for activity in day_activities
    )

def _build_free_slots(
    student_id: str,
    planning_start: str,
    planning_end: str,
    current_time: str | None = None
):
    activity_rows = Database.get_activity_slots_for_range(
        student_id=student_id,
        start_date=planning_start,
        end_date=planning_end
    )

    preference_rows = Database.get_day_preferences_for_range(
        student_id=student_id,
        start_date=planning_start,
        end_date=planning_end
    )

    activities_by_day = {}
    for slot_id, study_date, start_time, end_time, reason in activity_rows:
        activities_by_day.setdefault(study_date, []).append({
            "slot_id": slot_id,
            "start_time": start_time,
            "end_time": end_time,
            "reason": reason
        })

    preferences_by_day = {}
    for study_date, wake_time, sleep_time in preference_rows:
        preferences_by_day[study_date] = {
            "wake_time": wake_time,
            "sleep_time": sleep_time
        }

    all_free_slots = []
    total_available_hours = 0.0

    start_obj = datetime.strptime(planning_start, "%Y-%m-%d").date()
    end_obj = datetime.strptime(planning_end, "%Y-%m-%d").date()

    for d in daterange(start_obj, end_obj):
        day_str = d.isoformat()

        pref = preferences_by_day.get(day_str, {
            "wake_time": DEFAULT_WAKE_TIME,
            "sleep_time": DEFAULT_SLEEP_TIME
        })

        wake_time = pref["wake_time"]
        sleep_time = pref["sleep_time"]

        if wake_time >= sleep_time:
            continue

        day_activities = activities_by_day.get(day_str, [])

        if _is_study_free_day(day_activities):
            continue

        day_free_slots = _build_day_free_slots(
            day_str=day_str,
            wake_time=wake_time,
            sleep_time=sleep_time,
            day_activities=day_activities
        )

        # If this is the first planning day, remove time slots that are already in the past.
        if current_time is not None and day_str == planning_start:
            clipped_slots = []

            for slot in day_free_slots:
                # Entire slot is already in the past
                if slot["end_time"] <= current_time:
                    continue

                # Slot started in the past but still continues
                if slot["start_time"] < current_time:
                    slot = slot.copy()
                    slot["start_time"] = current_time
                    slot["remaining_hours"] = _calculate_slot_hours(
                        current_time,
                        slot["end_time"]
                    )

                if slot["remaining_hours"] > 0:
                    clipped_slots.append(slot)

            day_free_slots = clipped_slots

        for slot in day_free_slots:
            all_free_slots.append(slot)
            total_available_hours += slot["remaining_hours"]

    all_free_slots.sort(key=lambda s: (s["study_date"], s["start_time"]))
    return all_free_slots, round(total_available_hours, 2)

def _build_learning_profile_map(student_id: str) -> dict:
    rows = Database.get_learning_profile_for_student(student_id)
    profile_map = {}

    for row in rows:
        (
            task_type,
            subject,
            planning_factor,
            feedback_count,
            avg_difficulty,
            avg_mental_effort,
            avg_confidence,
            avg_focus,

        ) = row

        normalized_task_type = _normalize_task_type(task_type)
        normalized_subject = subject.strip() if subject and subject.strip() else "General"

        profile_map[(normalized_task_type, normalized_subject)] = {
            "planning_factor": float(planning_factor or 1.0),
            "feedback_count": int(feedback_count or 0),
            "avg_difficulty": float(avg_difficulty or 0.0),
            "avg_mental_effort": float(avg_mental_effort or 0.0),
            "avg_confidence": float(avg_confidence or 0.0),
            "avg_focus": float(avg_focus or 0.0),
        }

    return profile_map

def _estimate_spread_day_target(
    total_hours: float,
    preferred_study_days: int | None,
    min_session_hours: float | None
) -> tuple[float, int]:
    if preferred_study_days is None or preferred_study_days <= 0:
        return round(total_hours, 2), 1

    if min_session_hours is None or min_session_hours <= 0:
        min_session_hours = 1.0

    effective_spread_days = min(
        int(preferred_study_days),
        max(1, math.floor(float(total_hours) / float(min_session_hours)))
    )

    if effective_spread_days < 1:
        effective_spread_days = 1

    per_day_target = round(float(total_hours) / effective_spread_days, 2)
    return per_day_target, effective_spread_days


def build_study_plan(student_id: str):
    tasks = Database.get_plannable_tasks_for_student(student_id)
    learning_profile_map = _build_learning_profile_map(student_id)

    if not tasks:
        return {
            "daily_plan": {},
            "unscheduled_tasks": [],
            "planning_start": None,
            "planning_end": None,
            "total_required_hours": 0.0,
            "total_available_hours": 0.0,
            "day_limit_hours": DAY_LIMIT_HOURS
        }

    local_tz = ZoneInfo("Europe/Amsterdam")

    now_local = datetime.now(local_tz)
    today = now_local.date()
    now_time = now_local.strftime("%H:%M")

    parsed_deadlines = []
    for task in tasks:
        deadline_obj = datetime.strptime(task[6], "%Y-%m-%d").date()
        effective_deadline = max(deadline_obj, today)
        parsed_deadlines.append(effective_deadline)

    planning_start = today
    planning_end = max(parsed_deadlines)

    free_slots, total_available_hours = _build_free_slots(
        student_id=student_id,
        planning_start=planning_start.isoformat(),
        planning_end=planning_end.isoformat(),
        current_time=now_time
    )

    daily_plan: Dict[str, List[dict]] = {}
    sortable_tasks = []
    total_required_hours = 0.0

    for task in tasks:
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

        normalized_task_type = _normalize_task_type(task_type)
        normalized_subject = subject.strip() if subject and subject.strip() else "General"
        normalized_task_intensity = _derive_task_intensity(normalized_task_type)

        deadline_obj = datetime.strptime(deadline, "%Y-%m-%d").date()
        effective_deadline = max(deadline_obj, today)

        estimated_hours = float(estimated_hours)
        profile = learning_profile_map.get((normalized_task_type, normalized_subject))

        base_hours = adjusted_hours
        theory_adjusted_hours = round(float(base_hours), 2)

        preferred_energy = None
        resolved_max_session_hours = MAX_STUDY_BLOCK_HOURS
        buffer_percent = 0
        avoid_after_high_difficulty_task = False
        llm_reason = ""

        user_min_session_hours = float(min_session_hours) if min_session_hours is not None else None
        user_max_session_hours = float(max_session_hours) if max_session_hours is not None else None

        accepted_preferences = Database.get_ai_learning_preferences_for_task(
            student_id=student_id,
            task_type=normalized_task_type,
            subject=normalized_subject
        )

        latest_preference = accepted_preferences[0] if accepted_preferences else None

        if latest_preference:
            (
                preference_id,
                preference_text,
                pref_status,
                created_at,
                updated_at,
                pref_buffer,
                pref_energy,
                pref_max_session,
                pref_avoid_after
            ) = latest_preference

            if pref_buffer:
                buffer_percent = int(pref_buffer)

            if pref_energy:
                preferred_energy = pref_energy

            if pref_max_session is not None:
                resolved_max_session_hours = min(
                    resolved_max_session_hours,
                    float(pref_max_session)
                )

            if pref_avoid_after:
                avoid_after_high_difficulty_task = True

            llm_reason = preference_text or ""

        if buffer_percent:
            theory_adjusted_hours *= (1 + buffer_percent / 100)

        if user_max_session_hours is not None:
            resolved_max_session_hours = min(
                resolved_max_session_hours,
                user_max_session_hours
            )

        theory_adjusted_hours = round(theory_adjusted_hours, 2)
        total_required_hours += float(theory_adjusted_hours)

        spread_learning_enabled = (
            bool(is_spread_learning)
            and normalized_task_type == "Study / Learning"
        )

        if spread_learning_enabled:
            per_day_target, effective_spread_days = _estimate_spread_day_target(
                total_hours=theory_adjusted_hours,
                preferred_study_days=int(preferred_study_days) if preferred_study_days is not None else None,
                min_session_hours=user_min_session_hours if user_min_session_hours is not None else 1.0
            )
        else:
            per_day_target = theory_adjusted_hours
            effective_spread_days = 1

        sortable_tasks.append({
            "task_id": task_id,
            "task_name": task_name,
            "subject": normalized_subject,
            "task_type": normalized_task_type,
            "importance_level": importance_level,
            "task_intensity": task_intensity or normalized_task_intensity,
            "deadline": effective_deadline,
            "estimated_hours": estimated_hours,
            "adjusted_hours": float(theory_adjusted_hours),
            "status": status,
            "preferred_energy": preferred_energy,
            "max_session_hours": resolved_max_session_hours,
            "llm_buffer_percent": buffer_percent,
            "llm_reason": llm_reason,
            "avoid_after_high_difficulty_task": avoid_after_high_difficulty_task,
            "avg_difficulty": profile.get("avg_difficulty", 2.5) if profile else 2.5,
            "avg_mental_effort": profile.get("avg_mental_effort", 2.5) if profile else 2.5,
            "avg_confidence": profile.get("avg_confidence", 2.5) if profile else 2.5,
            "avg_focus": profile.get("avg_focus", 2.5) if profile else 2.5,
            "is_spread_learning": spread_learning_enabled,
            "preferred_study_days": int(preferred_study_days) if preferred_study_days is not None else None,
            "effective_spread_days": effective_spread_days,
            "min_session_hours": user_min_session_hours if user_min_session_hours is not None else 1.0,
            "user_max_session_hours": user_max_session_hours,
            "per_day_target": round(per_day_target, 2),
            "planned_hours_per_day": {}
        })

    sortable_tasks.sort(
        key=lambda t: (
            t["deadline"],
            IMPORTANCE_RANK.get(t["importance_level"], 99),
            -t["adjusted_hours"]
        )
    )

    unscheduled_tasks = []
    planned_hours_per_day: Dict[str, float] = {}
    cognitive_hours_per_day: Dict[str, float] = {}
    current_end_time_per_day: Dict[str, str] = {}

    for slot in free_slots:
        slot_date_obj = datetime.strptime(slot["study_date"], "%Y-%m-%d").date()
        day_str = slot["study_date"]
        slot_energy = slot["energy_level"]
        slot_start = slot["start_time"]

        if day_str not in current_end_time_per_day:
            current_end_time_per_day[day_str] = slot_start
        elif current_end_time_per_day[day_str] < slot_start:
            current_end_time_per_day[day_str] = slot_start

        slot_remaining = float(slot["remaining_hours"])
        continuous_study_time = 0.0
        skipped_task_ids_this_slot = set()

        while slot_remaining > 0:
            selected_task = None

            last_task_was_llm_flagged = False
            last_items_today = daily_plan.get(day_str, [])

            for previous_item in reversed(last_items_today):
                if not previous_item.get("is_break"):
                    previous_task_id = previous_item.get("task_id")

                    previous_task = next(
                        (t for t in sortable_tasks if t["task_id"] == previous_task_id),
                        None
                    )

                    if previous_task:
                        last_task_was_llm_flagged = bool(
                            previous_task.get("avoid_after_high_difficulty_task", False)
                        )

                    break

            candidate_tasks = sortable_tasks

            if last_task_was_llm_flagged:
                preferred_candidates = [
                    task for task in sortable_tasks
                    if not task.get("avoid_after_high_difficulty_task", False)
                       and task["adjusted_hours"] > 0
                ]

                if preferred_candidates:
                    candidate_tasks = preferred_candidates

            # Soft energy preference
            candidate_tasks = sorted(
                candidate_tasks,
                key=lambda candidate: (
                    0 if candidate.get("preferred_energy") == slot_energy else 1,
                    candidate["deadline"],
                    IMPORTANCE_RANK.get(candidate["importance_level"], 99),
                    -candidate["adjusted_hours"]
                )
            )

            for task in candidate_tasks:
                if task["task_id"] in skipped_task_ids_this_slot:
                    continue

                if task["adjusted_hours"] <= 0:
                    continue

                latest_study_date = max(
                    planning_start,
                    task["deadline"] - timedelta(days=1)
                )

                if slot_date_obj < planning_start or slot_date_obj > latest_study_date:
                    continue

                task["_reserve_later_preferred_energy"] = 0.0

                preferred_energy = task.get("preferred_energy")

                if preferred_energy and slot_energy != preferred_energy:
                    later_preferred_energy_hours = sum(
                        float(other_slot["remaining_hours"])
                        for other_slot in free_slots
                        if slot_date_obj < datetime.strptime(other_slot["study_date"],
                                                             "%Y-%m-%d").date() <= latest_study_date
                        and other_slot["energy_level"] == preferred_energy
                    )

                    if later_preferred_energy_hours >= float(task["adjusted_hours"]):
                        continue

                    task["_reserve_later_preferred_energy"] = later_preferred_energy_hours

                allowed = ALLOWED_INTENSITIES.get(slot_energy, {"Low"})
                if task["task_intensity"] not in allowed:
                    continue

                already_planned_today = planned_hours_per_day.get(day_str, 0.0)
                remaining_day_capacity = round(DAY_LIMIT_HOURS - already_planned_today, 2)

                if remaining_day_capacity <= 0:
                    continue

                already_planned_for_task_today = task["planned_hours_per_day"].get(day_str, 0.0)

                if task["is_spread_learning"]:
                    if round(task["per_day_target"] - already_planned_for_task_today, 2) <= 0:
                        continue

                if task["task_type"] in COGNITIVE_TASK_TYPES:
                    used_cognitive = cognitive_hours_per_day.get(day_str, 0.0)

                    if used_cognitive >= PREFERRED_COGNITIVE_LIMIT_HOURS:
                        later_available_hours = sum(
                            float(other_slot["remaining_hours"])
                            for other_slot in free_slots
                            if slot_date_obj < datetime.strptime(other_slot["study_date"],
                                                                 "%Y-%m-%d").date() <= latest_study_date
                        )

                        if later_available_hours >= float(task["adjusted_hours"]):
                            continue

                selected_task = task
                break

            if not selected_task:
                break

            already_planned_today = planned_hours_per_day.get(day_str, 0.0)
            remaining_day_capacity = round(DAY_LIMIT_HOURS - already_planned_today, 2)

            max_session_hours = float(
                selected_task.get("max_session_hours", MAX_STUDY_BLOCK_HOURS)
            )

            remaining_until_break = round(
                MAX_STUDY_BLOCK_HOURS - continuous_study_time,
                2
            )

            task_day_quota = selected_task["planned_hours_per_day"].get(day_str, 0.0)

            if selected_task["is_spread_learning"]:
                remaining_task_day_quota = round(
                    selected_task["per_day_target"] - task_day_quota,
                    2
                )
            else:
                remaining_task_day_quota = float(selected_task["adjusted_hours"])

            preferred_energy_current_limit = float(selected_task["adjusted_hours"])

            if (
                    selected_task.get("preferred_energy")
                    and slot_energy != selected_task.get("preferred_energy")
                    and selected_task.get("_reserve_later_preferred_energy", 0.0) > 0
            ):
                preferred_energy_current_limit = max(
                    float(selected_task["adjusted_hours"])
                    - float(selected_task["_reserve_later_preferred_energy"]),
                    0.0
                )

            allocated = min(
                slot_remaining,
                preferred_energy_current_limit,
                remaining_day_capacity,
                max_session_hours,
                remaining_until_break,
                remaining_task_day_quota
            )

            allocated = round(allocated, 2)

            if allocated <= 0:
                break

            if selected_task["is_spread_learning"]:
                min_block = 0.5

            elif selected_task["task_type"] in ["Practice", "Writing"]:
                min_block = 0.5

            elif selected_task["task_type"] in ["Review", "Reading"]:
                min_block = 0.15

            else:
                min_block = MIN_BLOCK_HOURS

            if allocated < min_block:
                skipped_task_ids_this_slot.add(selected_task["task_id"])
                continue

            start_dt = datetime.strptime(current_end_time_per_day[day_str], "%H:%M")
            end_dt = start_dt + timedelta(hours=allocated)

            start_time = start_dt.strftime("%H:%M")
            end_time = end_dt.strftime("%H:%M")

            daily_plan.setdefault(day_str, []).append({
                "task_id": selected_task["task_id"],
                "task_name": selected_task["task_name"],
                "subject": selected_task["subject"],
                "task_type": selected_task["task_type"],
                "importance_level": selected_task["importance_level"],
                "task_intensity": selected_task["task_intensity"],
                "hours": allocated,
                "deadline": selected_task["deadline"].isoformat(),
                "start_time": start_time,
                "end_time": end_time,
                "energy_level": slot_energy,
                "is_break": False
            })

            selected_task["adjusted_hours"] = round(
                float(selected_task["adjusted_hours"]) - allocated,
                2
            )

            selected_task["planned_hours_per_day"][day_str] = round(
                selected_task["planned_hours_per_day"].get(day_str, 0.0) + allocated,
                2
            )

            slot_remaining = round(slot_remaining - allocated, 2)

            planned_hours_per_day[day_str] = round(
                planned_hours_per_day.get(day_str, 0.0) + allocated,
                2
            )

            continuous_study_time = round(continuous_study_time + allocated, 2)
            current_end_time_per_day[day_str] = end_time

            if selected_task["task_type"] in COGNITIVE_TASK_TYPES:
                cognitive_hours_per_day[day_str] = round(
                    cognitive_hours_per_day.get(day_str, 0.0) + allocated,
                    2
                )

            effective_session_limit = float(
                selected_task.get("max_session_hours") or MAX_STUDY_BLOCK_HOURS
            )

            if (
                    continuous_study_time >= effective_session_limit
                    and slot_remaining >= BREAK_DURATION_HOURS
            ):
                break_start_dt = datetime.strptime(
                    current_end_time_per_day[day_str],
                    "%H:%M"
                )

                break_end_dt = break_start_dt + timedelta(hours=BREAK_DURATION_HOURS)

                break_start = break_start_dt.strftime("%H:%M")
                break_end = break_end_dt.strftime("%H:%M")

                daily_plan.setdefault(day_str, []).append({
                    "task_id": None,
                    "task_name": "Break",
                    "subject": "-",
                    "task_type": "Break",
                    "importance_level": "Low",
                    "task_intensity": "Low",
                    "hours": round(BREAK_DURATION_HOURS, 2),
                    "deadline": day_str,
                    "start_time": break_start,
                    "end_time": break_end,
                    "energy_level": "Recovery",
                    "is_break": True
                })

                current_end_time_per_day[day_str] = break_end
                slot_remaining = round(slot_remaining - BREAK_DURATION_HOURS, 2)
                continuous_study_time = 0.0

    for task in sortable_tasks:
        if 0 < task["adjusted_hours"] <= MIN_BLOCK_HOURS:
            task["adjusted_hours"] = 0

        if task["adjusted_hours"] > 0:
            unscheduled_tasks.append({
                "task_id": task["task_id"],
                "task_name": task["task_name"],
                "subject": task["subject"],
                "task_type": task["task_type"],
                "remaining_hours": round(task["adjusted_hours"], 2),
                "deadline": task["deadline"].isoformat(),
                "importance_level": task["importance_level"],
                "task_intensity": task["task_intensity"]
            })

    daily_plan = {
        day: items
        for day, items in daily_plan.items()
        if items
    }

    return {
        "daily_plan": daily_plan,
        "unscheduled_tasks": unscheduled_tasks,
        "planning_start": planning_start.isoformat(),
        "planning_end": planning_end.isoformat(),
        "total_required_hours": round(total_required_hours, 2),
        "total_available_hours": round(total_available_hours, 2),
        "day_limit_hours": DAY_LIMIT_HOURS
    }