from collections import defaultdict
from google import genai
import streamlit as st
import json


TASK_TYPE_TO_INTENSITY = {
    "Study / Learning": "High",
    "Reading": "Medium",
    "Practice": "High",
    "Writing": "High",
    "Review": "Low",
    "Administrative": "Low"
}

MIN_RATIO = 0.75
MAX_RATIO = 1.5


THEORY_PROMPT = """
Planning Fallacy Theory:
The planning fallacy describes the systematic tendency of people to underestimate how much time tasks will require, even when they know that similar tasks in the past took longer than expected.

People often make optimistic predictions about future performance while ignoring relevant historical evidence from previous experiences. This bias is especially common in academic work, long-term assignments, projects with multiple steps, and tasks that contain uncertainty or interruptions.

The planning fallacy is strongly connected to the “inside view.” When people estimate future workload, they mainly focus on their current intentions, ideal future schedules, motivation, best-case scenarios, and imagined successful progress. People naturally simulate how they hope the task will go instead of comparing it to previous real outcomes.

As a result, individuals often underestimate required time, delays, distractions, and overestimate future productivity. Even when previous tasks took significantly longer than expected, people may still remain optimistic because they explain past failures as exceptions, believe external factors caused previous delays, or assume they will behave differently this time.

Motivation can further strengthen unrealistic optimism. When people strongly want a task to go well or finish quickly, they often predict better outcomes without meaningfully changing their actual behavior.

The planning fallacy becomes stronger in complex tasks, open-ended assignments, unfamiliar topics, tasks requiring sustained focus, and long-duration projects. Short and simple tasks are generally easier to estimate accurately.

Repeated underestimation patterns may indicate unrealistic planning habits, insufficient reflection on previous experiences, overconfidence, ineffective workload estimation, or difficulty translating intentions into realistic schedules.

When interpreting student behavior, reason about whether the student consistently underestimates workload, whether previous experiences are being ignored, whether optimism may distort future planning, whether the student focuses mainly on ideal scenarios, and whether repeated deadline pressure reflects unrealistic expectations rather than lack of effort.


Cognitive Load Theory:
Cognitive Load Theory explains how learning and performance are influenced by the limited capacity of working memory.

Human working memory can only process a limited amount of information simultaneously. When too much information, complexity, or mental processing is required at the same time, cognitive overload can occur. Learning becomes less effective when mental demands exceed available cognitive resources.

Cognitive load can originate from task complexity, unfamiliar material, multitasking, distractions, poor instructional structure, insufficient prior knowledge, or sustained concentration demands.

Complex academic tasks often require students to process multiple concepts, maintain attention over time, integrate information, solve problems, and continuously update working memory. This can increase mental effort significantly.

High cognitive load may lead to mental exhaustion, slower progress, concentration problems, increased frustration, reduced comprehension, declining motivation, and reduced ability to maintain focus.

Students experiencing high mental effort are not necessarily incapable or unmotivated. Performance difficulties may instead reflect excessive cognitive demands placed on working memory.

Prior knowledge influences cognitive load strongly. Familiar or repetitive tasks usually require less mental effort because cognitive processes become more automated over time. Unfamiliar or conceptually difficult tasks generally require deeper processing, more working memory resources, and greater sustained concentration.

Cognitive overload may also accumulate gradually across long study sessions without sufficient recovery or breaks.

When interpreting student behavior, reason about whether workload complexity exceeds cognitive capacity, whether sustained concentration may contribute to fatigue, whether task structure or unfamiliarity increases mental strain, whether focus problems may reflect overload rather than lack of motivation, and whether balanced workload distribution could improve learning efficiency.


Self-Efficacy Theory:
Self-efficacy refers to a person’s belief in their own ability to successfully perform tasks and overcome challenges.

Students with high self-efficacy generally believe they are capable of handling difficult situations, learning new material, and recovering from setbacks. This belief strongly influences motivation, persistence, emotional responses, and academic behavior.

High self-efficacy is often associated with greater persistence, stronger resilience, willingness to attempt difficult tasks, higher motivation, and more adaptive coping strategies during setbacks.

Students with low self-efficacy may doubt their abilities, avoid challenging tasks, lose confidence quickly, experience anxiety more easily, disengage after failure, or underestimate their own competence.

Confidence does not always reflect actual performance accurately. A student may objectively perform well while still feeling insecure or uncertain. Similarly, some students may appear confident while underestimating task complexity.

Repeated experiences influence self-efficacy over time. Repeated failures, unfinished tasks, or overwhelming workload experiences may gradually lower confidence and willingness to engage with similar tasks in the future.

Positive mastery experiences, successful completion, and manageable progress can strengthen self-efficacy over time.

Self-efficacy also affects emotional interpretation of difficulty. Students with lower self-efficacy may interpret normal academic struggle as evidence of inability, while students with higher self-efficacy may interpret the same struggle as a normal learning challenge.

When interpreting student behavior, reason about confidence patterns across tasks, emotional responses to difficulty, avoidance or disengagement, persistence during challenging situations, whether repeated setbacks influence future expectations, and whether low confidence reflects actual inability or perceived lack of control.


Self-Regulated Learning Theory:
Self-regulated learning refers to the ability of learners to actively manage, monitor, and adapt their own learning process.

Effective learners do not simply complete tasks passively. They continuously plan their behavior, monitor progress, evaluate outcomes, reflect on mistakes, and adapt future strategies based on previous experiences.

Self-regulated learning includes goal setting, time management, workload planning, concentration management, self-monitoring, reflection, and behavioral adjustment.

Students differ significantly in their ability to regulate learning effectively. Some students monitor their workload realistically, recognize ineffective habits, and adapt strategies over time. Other students may repeat ineffective behaviors, underestimate workload repeatedly, struggle to reflect on mistakes, or fail to translate reflection into behavioral change.

Reflection is a critical component of learning improvement. Students who recognize recurring patterns in procrastination, workload estimation, concentration, stress, or study behavior are more likely to improve future performance.

Self-regulated learning also involves emotional regulation. Academic performance is influenced not only by cognitive ability, but also by motivation, stress management, persistence, and adaptation after setbacks.

Learning improvement is often gradual and iterative rather than immediate.

When interpreting student behavior, reason about whether the student reflects on previous experiences, whether behavioral adaptation occurs over time, whether recurring problems are recognized, whether planning behavior improves after feedback, and whether the student demonstrates awareness of their own learning process.


Metacognition Theory:
Metacognition refers to awareness and understanding of one’s own thinking, learning, and cognitive processes.

Metacognition includes monitoring understanding, evaluating progress, recognizing limitations, judging task difficulty, and adapting strategies when necessary.

Students with stronger metacognitive skills are generally better at realistic workload estimation, recognizing confusion early, adjusting ineffective strategies, evaluating learning quality, and reflecting accurately on performance.

Weak metacognitive awareness may lead students to overestimate understanding, underestimate workload, fail to recognize ineffective learning habits, or continue inefficient strategies despite poor outcomes.

Metacognitive monitoring is especially important during complex academic tasks that require planning, self-evaluation, sustained attention, and adaptive problem solving.

Poor metacognitive awareness can contribute to repeated planning errors because students may fail to accurately judge how difficult a task actually is, how much concentration it requires, or how effectively they are learning.

Metacognition is closely connected to reflection and self-awareness. Students who develop stronger reflective understanding of their learning behavior are often better able to identify recurring problems, make realistic predictions, and improve future study strategies.

When interpreting student behavior, reason about realism of self-evaluation, awareness of strengths and weaknesses, recognition of recurring mistakes, ability to monitor progress accurately, and whether the student demonstrates reflective insight into their own study behavior.


Distributed Practice Theory:
Distributed practice refers to spreading learning activities across multiple study sessions over time instead of concentrating learning into one long uninterrupted session.

Research consistently shows that distributed learning improves long-term retention, recall strength, understanding, consolidation of knowledge, and sustainable learning performance.

Massed practice, often called cramming, may produce temporary short-term progress but often results in quicker forgetting, reduced retention, cognitive overload, mental exhaustion, and declining concentration over time.

Spacing learning sessions allows the brain to consolidate information, recover from cognitive effort, and revisit material with refreshed attention.

Distributed practice is especially beneficial for complex learning, conceptual understanding, long-term memory formation, and tasks requiring sustained cognitive effort.

Long uninterrupted sessions may increase fatigue and reduce learning efficiency even when students remain motivated. Repeated exposure across multiple sessions can strengthen understanding while reducing excessive cognitive strain during individual study periods.

Different tasks may benefit differently from distribution. Difficult conceptual tasks generally benefit more from spacing than highly repetitive or procedural tasks.

When interpreting student behavior, reason about whether workload is concentrated too heavily, whether long sessions contribute to fatigue or declining focus, whether learning distribution may improve retention, whether repeated short sessions could support better sustainability, and whether spacing could reduce cognitive overload.


Mental Fatigue Theory:
Mental fatigue develops after prolonged periods of cognitive effort, sustained attention, and continuous mental processing. Mental fatigue is a gradual reduction in cognitive efficiency caused by extended mental workload.

High cognitive demands over time can reduce concentration, working memory performance, motivation, attention control, self-regulation, and decision-making quality.

Mental fatigue may accumulate across long study sessions, multiple difficult tasks, prolonged focus demands, insufficient breaks, stress, or sustained academic pressure.

Tasks that require deep concentration, complex reasoning, problem solving, information integration, or continuous attention are especially mentally demanding.

Symptoms of mental fatigue may include declining focus, slower progress, increased distraction, reduced motivation, frustration, emotional exhaustion, difficulty maintaining effort, and reduced study efficiency.

Performance problems are not always caused by low ability or low motivation. Students may experience temporary reductions in performance simply because cognitive resources have become depleted.

Mental fatigue can also influence emotional experiences, causing students to perceive tasks as more difficult, overwhelming, or frustrating after extended effort.

Recovery periods, balanced workload distribution, breaks, variation in task intensity, and sustainable pacing may reduce accumulated fatigue.

When interpreting student behavior, reason about whether cognitive exhaustion may explain reduced focus, whether workload intensity accumulates over time, whether prolonged concentration contributes to declining efficiency, whether recovery opportunities are sufficient, and whether fatigue rather than ability explains performance difficulties.
"""


def get_client():
    return genai.Client(api_key=st.secrets["gemini_api_key"])


def _safe_text(value) -> str:
    if value is None:
        return "N/A"
    return str(value)


def _clamp_ratio(ratio: float) -> float:
    return max(MIN_RATIO, min(MAX_RATIO, ratio))


def _derive_intensity_from_task_type(task_type: str) -> str:
    return TASK_TYPE_TO_INTENSITY.get(task_type, "Medium")


def _format_daily_plan(daily_plan: dict) -> str:
    if not daily_plan:
        return "No daily plan was generated."

    lines = []
    for study_day, items in sorted(daily_plan.items()):
        lines.append(f"{study_day}:")
        for item in items:
            if item.get("is_break"):
                lines.append(
                    f"- Break (automatic) | "
                    f"hours: {item['hours']} | "
                    f"start: {item.get('start_time', 'N/A')} | "
                    f"end: {item.get('end_time', 'N/A')} | "
                    f"energy slot: {item.get('energy_level', 'N/A')} | "
                    f"purpose: recovery after continuous study"
                )
            else:
                lines.append(
                    f"- {item['task_name']} | "
                    f"subject: {item.get('subject', 'N/A')} | "
                    f"type: {item['task_type']} | "
                    f"importance: {item['importance_level']} | "
                    f"intensity: {item.get('task_intensity', _derive_intensity_from_task_type(item.get('task_type', '')))} | "
                    f"hours: {item['hours']} | "
                    f"start: {item.get('start_time', 'N/A')} | "
                    f"end: {item.get('end_time', 'N/A')} | "
                    f"energy slot: {item.get('energy_level', 'N/A')} | "
                    f"deadline: {item['deadline']}"
                )
    return "\n".join(lines)


def _format_unscheduled_tasks(unscheduled_tasks: list) -> str:
    if not unscheduled_tasks:
        return "No unscheduled tasks."

    lines = []
    for item in unscheduled_tasks:
        lines.append(
            f"- {item['task_name']} | "
            f"subject: {item.get('subject', 'N/A')} | "
            f"type: {item.get('task_type', 'N/A')} | "
            f"remaining_hours: {item['remaining_hours']} | "
            f"deadline: {item['deadline']} | "
            f"importance: {item['importance_level']} | "
            f"intensity: {item.get('task_intensity', _derive_intensity_from_task_type(item.get('task_type', '')))}"
        )
    return "\n".join(lines)


def _format_recent_feedback_examples(history_rows: list, max_items: int = 8) -> str:
    if not history_rows:
        return "No recent feedback examples available."

    lines = []

    for row in history_rows[:max_items]:
        (
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
            logged_at
        ) = row

        estimated_hours = float(estimated_hours) if estimated_hours else 0.0
        actual_hours = float(actual_hours) if actual_hours else 0.0
        remaining_hours = float(remaining_hours) if remaining_hours else 0.0

        total_needed = round(actual_hours + remaining_hours, 2)
        completed_text = "completed" if completed else "not completed"

        ratio_text = "N/A"
        if estimated_hours > 0:
            raw_ratio = total_needed / estimated_hours
            clamped_ratio = _clamp_ratio(raw_ratio)
            ratio_text = f"raw ratio: {round(raw_ratio, 2)} | clamped ratio: {round(clamped_ratio, 2)}"

        lines.append(
            f"- {task_name} | subject: {subject} | type: {task_type} | importance: {importance_level} | "
            f"estimated: {estimated_hours}h | total needed: {total_needed}h | "
            f"{ratio_text} | difficulty: {perceived_difficulty} | "
            f"effort: {mental_effort} | confidence: {confidence_level} | focus: {focus_level} | "
            f"status: {completed_text} | logged at: {logged_at}"
        )

    return "\n".join(lines)


def _format_learning_profile(learning_profile_rows: list) -> str:
    if not learning_profile_rows:
        return "No personal learning profile available yet."

    lines = []

    for row in learning_profile_rows:
        (
            task_type,
            subject,
            planning_factor,
            feedback_count,
            avg_difficulty,
            avg_mental_effort,
            avg_confidence,
            avg_focus,
            updated_at
        ) = row

        lines.append(
            f"- {task_type} | subject: {subject} | historical time ratio: {round(float(planning_factor), 2)} | "
            f"feedback count: {feedback_count} | "
            f"avg difficulty: {round(float(avg_difficulty), 2)} | "
            f"avg effort: {round(float(avg_mental_effort), 2)} | "
            f"avg confidence: {round(float(avg_confidence), 2)} | "
            f"avg focus: {round(float(avg_focus), 2)} | "
            f"updated at: {updated_at}"
        )

    return "\n".join(lines)


def _format_task_feasibility(tasks: list, daily_plan: dict) -> str:
    if not tasks:
        return "No active tasks available."

    planned_hours_by_task = {}

    for study_day, items in daily_plan.items():
        for item in items:
            task_id = item["task_id"]
            planned_hours_by_task[task_id] = planned_hours_by_task.get(task_id, 0.0) + float(item["hours"])

    lines = []

    for task in tasks:
        if len(task) == 13:
            (
                task_id,
                task_name,
                subject,
                task_type,
                importance_level,
                task_intensity,
                deadline,
                estimated_hours,
                status,
                is_spread_learning,
                preferred_study_days,
                min_session_hours,
                max_session_hours
            ) = task
            adjusted_hours = estimated_hours
        else:
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

        estimated_hours = float(estimated_hours)
        adjusted_hours = float(adjusted_hours)
        planned_hours = round(planned_hours_by_task.get(task_id, 0.0), 2)
        unplanned_hours = round(max(adjusted_hours - planned_hours, 0.0), 2)

        feasibility_note = "fully planned before deadline"
        if unplanned_hours > 0:
            feasibility_note = f"NOT fully planned ({unplanned_hours}h still unplanned before deadline)"

        lines.append(
            f"- {task_name} | task_id: {task_id} | subject: {subject} | type: {task_type} | "
            f"importance: {importance_level} | intensity: {task_intensity} | "
            f"deadline: {deadline} | estimated: {estimated_hours}h | "
            f"current adjusted/plannable: {adjusted_hours}h | "
            f"planned in current plan: {planned_hours}h | "
            f"unplanned: {unplanned_hours}h | status: {status} | "
            f"feasibility: {feasibility_note} | "
            f"spread learning: {'yes' if is_spread_learning else 'no'} | "
            f"preferred study days: {preferred_study_days if preferred_study_days is not None else 'N/A'}"
        )

    return "\n".join(lines)


def summarize_learning_patterns(history_rows: list) -> str:
    if not history_rows:
        return "No historical feedback available yet."

    grouped = defaultdict(list)

    for row in history_rows:
        (
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
            logged_at
        ) = row

        if estimated_hours is None:
            continue

        estimated_hours = float(estimated_hours)
        actual_hours = float(actual_hours) if actual_hours is not None else 0.0
        remaining_hours = float(remaining_hours) if remaining_hours is not None else 0.0

        if estimated_hours <= 0:
            continue

        total_needed = actual_hours + remaining_hours
        raw_ratio = total_needed / estimated_hours
        clamped_ratio = _clamp_ratio(raw_ratio)

        grouped[(task_type, subject)].append({
            "importance_level": importance_level,
            "estimated_hours": estimated_hours,
            "total_needed": total_needed,
            "raw_ratio": raw_ratio,
            "clamped_ratio": clamped_ratio,
            "difficulty": float(perceived_difficulty) if perceived_difficulty is not None else None,
            "effort": float(mental_effort) if mental_effort is not None else None,
            "confidence": float(confidence_level) if confidence_level is not None else None,
            "focus": float(focus_level) if focus_level is not None else None,
        })

    if not grouped:
        return "No usable learning patterns found."

    lines = []

    for (task_type, subject), items in sorted(grouped.items()):
        avg_raw_ratio = sum(x["raw_ratio"] for x in items) / len(items)
        avg_clamped_ratio = sum(x["clamped_ratio"] for x in items) / len(items)
        avg_estimated = sum(x["estimated_hours"] for x in items) / len(items)
        avg_total_needed = sum(x["total_needed"] for x in items) / len(items)

        difficulty_vals = [x["difficulty"] for x in items if x["difficulty"] is not None]
        effort_vals = [x["effort"] for x in items if x["effort"] is not None]
        confidence_vals = [x["confidence"] for x in items if x["confidence"] is not None]
        focus_vals = [x["focus"] for x in items if x["focus"] is not None]

        avg_difficulty = round(sum(difficulty_vals) / len(difficulty_vals), 2) if difficulty_vals else None
        avg_effort = round(sum(effort_vals) / len(effort_vals), 2) if effort_vals else None
        avg_confidence = round(sum(confidence_vals) / len(confidence_vals), 2) if confidence_vals else None
        avg_focus = round(sum(focus_vals) / len(focus_vals), 2) if focus_vals else None

        if avg_clamped_ratio > 1.15:
            pattern = "usually underestimated"
        elif avg_clamped_ratio < 0.85:
            pattern = "usually overestimated"
        else:
            pattern = "usually estimated fairly accurately"

        line = (
            f"Task type: {task_type} | "
            f"subject: {subject} | "
            f"samples: {len(items)} | "
            f"avg estimated: {round(avg_estimated, 2)}h | "
            f"avg total needed: {round(avg_total_needed, 2)}h | "
            f"avg raw ratio: {round(avg_raw_ratio, 2)} | "
            f"avg clamped ratio: {round(avg_clamped_ratio, 2)} | "
            f"time estimation pattern: {pattern}"
        )

        if avg_difficulty is not None:
            line += f" | avg difficulty: {avg_difficulty}"
        if avg_effort is not None:
            line += f" | avg mental effort: {avg_effort}"
        if avg_confidence is not None:
            line += f" | avg confidence: {avg_confidence}"
        if avg_focus is not None:
            line += f" | avg focus: {avg_focus}"

        lines.append(line)

    return "\n".join(lines)

def _format_ai_learning_preferences(preference_rows: list) -> str:
    if not preference_rows:
        return "No accepted AI learning preferences available yet."

    lines = []

    for row in preference_rows:
        (
            preference_id,
            task_type,
            subject,
            preference_text,
            status,
            created_at,
            updated_at
        ) = row

        lines.append(
            f"- subject: {subject} | task type: {task_type} | "
            f"preference: {preference_text} | updated at: {updated_at}"
        )

    return "\n".join(lines)


def build_student_context(student_name: str, plan_result: dict, history_rows: list, tasks: list, learning_profile_rows: list,  ai_learning_preferences: list | None = None) -> str:
    daily_plan_text = _format_daily_plan(plan_result.get("daily_plan", {}))
    unscheduled_tasks_text = _format_unscheduled_tasks(plan_result.get("unscheduled_tasks", []))
    learning_patterns_text = summarize_learning_patterns(history_rows)
    learning_profile_text = _format_learning_profile(learning_profile_rows)
    recent_feedback_text = _format_recent_feedback_examples(history_rows)
    task_feasibility_text = _format_task_feasibility(tasks, plan_result.get("daily_plan", {}))
    ai_preferences_text = _format_ai_learning_preferences(ai_learning_preferences or [])

    total_required_hours = plan_result.get("total_required_hours", 0.0)
    total_available_hours = plan_result.get("total_available_hours", 0.0)
    planning_start = _safe_text(plan_result.get("planning_start", "N/A"))
    planning_end = _safe_text(plan_result.get("planning_end", "N/A"))
    day_limit_hours = _safe_text(plan_result.get("day_limit_hours", "N/A"))

    overload_note = "Workload seems within available hours."
    try:
        if float(total_required_hours) > float(total_available_hours):
            overload_note = (
                f"Workload exceeds availability by "
                f"{round(float(total_required_hours) - float(total_available_hours), 2)} hours."
            )
    except (TypeError, ValueError):
        pass

    context = f"""
Student name: {student_name}

Planning period:
- Start: {planning_start}
- End: {planning_end}

Workload summary:
- Total required hours: {total_required_hours}
- Total available hours: {total_available_hours}
- Day limit hours: {day_limit_hours}
- Workload note: {overload_note}

Current study plan:
{daily_plan_text}

Unscheduled tasks:
{unscheduled_tasks_text}

Task feasibility overview:
{task_feasibility_text}

Historical learning patterns:
{learning_patterns_text}

Personal learning factors currently available:
{learning_profile_text}

Accepted AI learning preferences:
{ai_preferences_text}

Recent feedback examples:
{recent_feedback_text}

Planner/system context:
- The planner derives study time from the remaining gaps between daily activities.
- The planning window for a day is based on the student's wake time and sleep time.
- The planner also uses a daily study-hour limit so one day does not become overloaded.
- Study blocks are influenced by energy level after the most recent activity.
- 'Rest' refers to awake rest moments, such as breaks, recovery, or moments where the student does not want to study.
- Energy level is interpreted as:
  - Work/School -> Low
  - Physical activity -> Medium
  - Social -> Medium
  - Rest -> High
  - Other -> Medium
- Task intensity is not chosen manually by the student.
- Task intensity is derived automatically from task type:
  - Study / Learning -> High
  - Reading -> Medium
  - Practice -> High
  - Writing -> High
  - Review -> Low
  - Administrative -> Low
- The scheduler enforces deadlines, time windows, valid study slots, and capacity constraints.
- The LLM should not override hard scheduling constraints.
- The LLM should interpret feedback, study behavior, and learning patterns using the provided theories.
- The LLM should avoid rigid threshold-based conclusions.
- The LLM should reason cautiously and contextually.
- The LLM may identify possible recurring behavioral, motivational, cognitive, or estimation-related patterns across subjects and task types.
- The student can confirm, reject, or refine the LLM interpretation.
- Short study breaks are automatically inserted by the planner after periods of continuous study.
- Breaks are not user-defined tasks and should not be interpreted as productive study time.
"""
    return context.strip()


def _build_conversation_text(chat_history: list, empty_text: str) -> str:
    if not chat_history:
        return empty_text

    conversation_lines = []
    for msg in chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        conversation_lines.append(f"{role.upper()}: {content}")

    return "\n".join(conversation_lines)


def chat_with_study_coach(
    student_name: str,
    student_context: str,
    chat_history: list,
    user_message: str
) -> str:

    client = get_client()

    conversation_text = _build_conversation_text(
        chat_history,
        "No previous conversation yet."
    )

    prompt = f"""
You are a supportive AI study coach for a university student.

Your role:
- help the student understand their study plan,
- explain important workload or planning risks,
- reflect on study behavior patterns,
- and support realistic future planning.

- Use the following theories internally only for reasoning quality.
- Never structure the response like an academic analysis.

{THEORY_PROMPT}

Important behavior rules:
IMPORTANT LANGUAGE RULE:
- Always respond in English.
- Never switch languages, even if task names, subject names, or student messages contain Dutch or other non-English words.
- All reflections, explanations, questions, and recommendations must be written in English.
- Keep your answers short, practical, and supportive.
- Do NOT write long essays.
- Use a maximum of 3-5 short bullet points when giving analysis.
- Focus only on the most important observations.
- Do not explain theory names unless the student explicitly asks for them.
- Briefly explain WHY tasks were scheduled in certain places.
- Mention concrete planning factors such as:
  - deadlines,
  - available time,
  - task intensity,
  - breaks,
  - workload balance,
  - and previous feedback patterns.
- Only mention real risks that are clearly relevant.
- Avoid dramatic language.
- Do not overanalyse small issues.
- Small remaining times below 15 minutes are not important.
- If the plan looks realistic overall, clearly say that.
- End with at most ONE short reflective question.
- Do not repeat information unnecessarily.

Reasoning behavior:
- Do not use rigid threshold-based rules.
- Do not treat one feedback moment as proof of a stable pattern.
- Reason dynamically from the student's context.
- Make uncertainty clear.
- Use phrases such as:
  - "this may suggest"
  - "one possible explanation is"
  - "based on the available feedback"
- Allow the student to correct or refine your interpretation.
- Do not invent data that is not in the context.
- Distinguish between:
  - time-estimation issues
  - cognitive load
  - focus problems
  - motivational issues
- If discussing realism, check whether tasks are planned before their deadline.
- Recognize that breaks are recovery periods, not productive study time.
- When discussing the study plan, first explain WHY the planner scheduled tasks in certain places.
- Speak collaboratively using phrases like:
  - "the planner scheduled"
  - "we scheduled"
  - "this was placed here because"
- Avoid sounding overly critical or dramatic.
- Do not frame every concentrated workload as a problem.
- Only mention fatigue or overload if the workload is clearly unrealistic.
- Prefer explaining planning decisions over warning about them.
- Do not discuss every task individually if the overall plan already looks balanced.
- Prioritize the single most important planning observations.
- Prefer explaining the planner's reasoning over criticizing the schedule.
- Assume the generated schedule is reasonable unless there are clear planning problems.
- High-intensity tasks are not automatically problematic if enough time, breaks, and recovery are available.
- Small remaining task fragments below the minimum scheduling block are considered effectively completed and should not be framed as missing workload.
- Ignore very small scheduling differences below 15 minutes.
- Treat tiny remaining fragments as effectively planned.
- Do not describe negligible rounding leftovers as real missing workload.

- Avoid academic sounding section titles such as:
  - "Distributed Practice"
  - "Cognitive Load"
  - "Mental Fatigue"
  - "Self-Regulation"
- Prefer natural planning explanations instead.

- Do not overstate workload risks.
- A concentrated study day is not automatically a problem.
- Only warn about overload if the workload is clearly unrealistic relative to the student's available time and context.

- When discussing intensive days:
  - explain WHY the planner scheduled tasks there,
  - mention deadlines, free time, and workload balancing,
  - and frame it as a planning tradeoff rather than a mistake.

- Prefer phrases such as:
  - "the planner spread the workload"
  - "this was scheduled here because"
  - "this day is relatively intensive"
  - "it may help to monitor your focus"
- Avoid dramatic phrases such as:
  - "serious overload"
  - "high risk of burnout"
  - "extreme cognitive fatigue"

- Do not criticize the schedule if:
  - tasks fit before deadlines,
  - breaks are included,
  - and workload remains feasible overall.

- Never mention weekdays unless they are explicitly provided in the study plan context.
- Do not calculate or infer weekdays yourself.
- Refer to dates only as dates, for example "May 28" instead of "Thursday, May 28".
- If the student asks about a specific day, use the exact date shown in the study plan.
- If the plan is realistic overall, clearly say so and keep the tone reassuring.

Student:
{student_name}

Student context:
{student_context}

Conversation so far:
{conversation_text}

Latest student message:
{user_message}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text


def generate_feedback_reflection(
    student_name: str,
    task_name: str,
    subject: str,
    task_type: str,
    estimated_hours: float,
    adjusted_hours: float,
    actual_hours: float,
    remaining_hours: float,
    completed: bool,
    perceived_difficulty,
    mental_effort,
    confidence_level,
    focus_level,
    student_context: str,
    chat_history: list
) -> str:

    client = get_client()

    conversation_text = _build_conversation_text(
        chat_history,
        "No previous reflection conversation yet."
    )

    prompt = f"""
    You are an adaptive AI reflection coach for a university student.

    Your role is to:
    - understand the student's study behaviour,
    - identify possible learning patterns,
    - gather contextual explanations,
    - and help improve future planning personalization.

    The educational psychology theories below should remain INVISIBLE to the student.
    Use them internally as reasoning foundations only.

    Never explicitly mention theory names such as:
    - Planning Fallacy
    - Cognitive Load Theory
    - Self-Efficacy
    - Self-Regulated Learning
    - Metacognition
    - Distributed Practice
    - Mental Fatigue

    The student should experience the conversation as:
    - natural,
    - reflective,
    - supportive,
    - and conversational.

    NOT as an academic theory explanation.

    Use the following theories internally for reasoning:

    {THEORY_PROMPT}

    Important behavioral rules:
    IMPORTANT LANGUAGE RULE:
    - Always respond in English.
    - Never switch languages, even if task names, subject names, or student messages contain Dutch or other non-English words.
    - All reflections, explanations, questions, and recommendations must be written in English.
    - Do not lecture the student.
    - Do not explain psychological theories.
    - Avoid long explanations.
    - Keep responses concise and conversational.
    - Focus primarily on understanding WHY the study experience happened.
    - Generate hypotheses, not absolute conclusions.
    - One feedback moment does NOT prove a stable pattern.
    - Use the current feedback together with historical feedback patterns.
    - If similar issues appeared in previous tasks with the same subject and task type, mention this carefully.
    - If the pattern appears recurring, explain that future planning may adapt.
    - If there is only one example, describe the interpretation as tentative.
    - If the explanation is already sufficiently clear, stop asking questions.
    - Only ask follow-up questions when important context is still missing.
    - You may ask multiple follow-up questions across the conversation if they are genuinely needed.
    - Ask at most ONE focused question per response.
    - Never ask questions just to continue the conversation.
    - Stop asking once the cause is clear enough to support a future planning decision.
    - The goal is not only reflection, but collecting useful information for future planning preferences.
    - The goal is to gradually build understanding of the student's learning behaviour over time.
    - The student is allowed to disagree with your interpretation.
    - If the student corrects your interpretation, adapt naturally.
    - Prefer short reflections over long analyses.
    - When judging whether the time estimate was accurate, compare actual hours mainly with the planned / adjusted hours used by the planner.
    - Use the original estimated hours only to understand how much the planner had already adjusted the task.
    - If actual hours are close to planned / adjusted hours, do not say the task was underestimated, even if it is higher than the original estimate.

    Conversation strategy:
1. Briefly reflect on the feedback.
2. Compare it with available historical patterns if relevant.
3. Form a tentative interpretation.
4. Decide which of the following outcomes is most appropriate:

A. Ask a follow-up question
- Use this only when important planning context is still missing.
- Ask a follow-up question only if the answer is likely to improve future planning personalization.
- A reflection conversation may contain multiple follow-up questions across multiple turns, but only when each question adds meaningful planning information.
- In a single response, ask at most ONE focused question.
- Do not ask questions just to continue the conversation.
- If the student's explanation already gives a plausible planning-relevant cause, do not ask another question.
- Stop asking once the likely cause is clear enough to support either a planning proposal or a no-change conclusion.
Information sufficiency rule:
- The goal is to collect enough information for future planning decisions, not to maximize conversation length.
- When enough information has been collected, move to outcome B or C.
- Do not keep the conversation open with a question when the likely cause is already clear.
- If the evidence suggests a task-specific or temporary explanation rather than a stable pattern, prefer outcome C.
- Only continue asking questions if the answer could realistically change the future planning recommendation.
- Do not ask a new follow-up question after you have already concluded that no planning adjustment is needed.
- Do not combine outcome A (follow-up question) and outcome C (no adaptation) in the same response.
- If no adaptation is needed, end the reflection with a conclusion rather than another question.
B. Generate an adaptive planning proposal
- Use this when clear and useful future planning adaptations can already be suggested.
- Suggestions may relate to additional workload buffers, shorter study sessions, preferred energy moments, workload spreading, or estimation adjustments.
- Clearly explain WHY the proposal may help.
- If a concrete preference is proposed, ask whether the student would like to apply this preference to future similar tasks.

C. Continue without adaptive changes
- Use this when the current planning approach appears effective and no meaningful adaptation is needed.
- Briefly explain why no change is recommended.
- Mention which aspect of the current planning approach seems to work well.
- Do not ask another question.

5. Always choose exactly ONE of these outcomes per response.
6. Avoid vague endings such as only saying "continue".
7. Keep the response concise, supportive, and practical.

    When asking a follow-up question, try to uncover one of these planning-relevant causes:
    - Was the task easier or harder because of prior knowledge?
    - Was the estimate wrong because the task had hidden steps?
    - Did focus, fatigue, stress, motivation, or distractions affect progress?
    - Was the task too long or too concentrated in one session?
    - Did the student prefer a different time of day or energy level?
    - Would future similar tasks benefit from more time, shorter sessions, higher-energy slots, or more spacing?

    Current feedback:
    - Student: {student_name}
    - Task: {task_name}
    - Subject: {subject}
    - Task type: {task_type}
    - Original estimated hours: {estimated_hours}
    - Planned / adjusted hours used by the planner: {adjusted_hours}
    - Actual hours spent: {actual_hours}
    - Remaining hours: {remaining_hours}
    - Completed: {completed}
    - Perceived difficulty: {perceived_difficulty}
    - Mental effort: {mental_effort}
    - Confidence level: {confidence_level}
    - Focus level: {focus_level}

    Student context:
    {student_context}

    Previous reflection conversation:
    {conversation_text}

    Write the next response for the reflection conversation.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text

def check_reflection_completion(
    student_name: str,
    task_name: str,
    subject: str,
    task_type: str,
    student_context: str,
    chat_history: list
) -> dict:
    client = get_client()

    conversation_text = _build_conversation_text(
        chat_history,
        "No reflection conversation available."
    )

    prompt = f"""
You are checking whether an AI reflection conversation has enough information to move on.

The goal of the reflection conversation is to understand WHY the study experience happened,
so future similar tasks can be planned better.

Similar tasks means:
- same student
- same subject
- same task type

Return ONLY valid raw JSON.
Do not use markdown.
Do not wrap the JSON in triple backticks.

Schema:
{{
  "enough_information": <true | false>,
  "reason": <short string>
}}

Set enough_information to true if:
- the student gave a specific explanation for why the task went as it did,
- or the AI already has enough context to make/no make a future planning suggestion.

Set enough_information to false if:
- the student answer is vague,
- important context is missing,
- or the AI should ask one more focused follow-up question.

Student:
{student_name}

Task:
- {task_name}
- Subject: {subject}
- Task type: {task_type}

Student context:
{student_context}

Reflection conversation:
{conversation_text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    raw_text = response.text.strip()
    cleaned_text = raw_text

    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text.removeprefix("```json").strip()
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.removeprefix("```").strip()

    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text.removesuffix("```").strip()

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        return {
            "enough_information": False,
            "reason": "Could not parse completion check."
        }

def generate_learning_preference_proposal(
    student_name: str,
    task_name: str,
    subject: str,
    task_type: str,
    student_context: str,
    chat_history: list,
    estimated_hours: float | None = None,
    adjusted_hours: float | None = None,
    actual_hours: float | None = None
) -> dict:
    client = get_client()
    conversation_text = _build_conversation_text(
        chat_history,
        "No reflection conversation available."
    )

    prompt = f"""
You are an adaptive AI study coach.

Your task is to decide whether the reflection conversation contains enough information to propose a future planning preference for similar tasks.

Similar tasks means:
- same student
- same subject
- same task type

Do NOT propose a preference if the explanation is too vague or based on only unclear information.

Do NOT propose a preference if the explanation is too vague or based on only unclear information.

Adaptive recommendations must be conservative.

Do not propose planning adjustments based on a single task unless the evidence is very strong.

When interpreting a completed task:
1. First determine whether the observed outcome is likely caused by:
   - a stable personal pattern
   - task-specific circumstances
   - external circumstances

2. Prior knowledge, unusually easy material, high motivation, or favorable conditions should be treated as task-specific explanations rather than evidence of a stable learning pattern.

3. Only suggest persistent planning adjustments when:
   - similar patterns have occurred repeatedly
   - historical feedback supports the same conclusion
   - sufficient evidence exists that the behavior reflects a stable tendency.

4. If evidence is insufficient, explain the observation but avoid recommending planner changes.

5. When uncertainty exists, explicitly state that additional observations are needed before adapting future planning behaviour.

The preference should be practical and useful for future planning.
Do not mention theory names.
Do not include long explanations.
Do not ask the student more questions in this response.

Return ONLY valid raw JSON.
Do not use markdown.
Do not wrap the JSON in triple backticks.

Schema:
{{
  "has_proposal": <true | false>,
  "proposal_text": <short string or null>,
  "add_time_buffer_percent": <0 | 10 | 20 | 30>,
  "preferred_energy": <"High" | "Medium" | "Low" | null>,
  "max_session_hours": <0.5 | 1.0 | 1.5 | null>,
  "avoid_after_high_difficulty_task": <true | false>,
  "reason": <short string>
}}

Only include planner adjustments if they logically follow from the reflection conversation.
If the student completed the task faster because it was familiar, do not add extra buffer.
Only recommend shorter sessions when the reflection conversation contains evidence that session length contributed to reduced focus, fatigue, or performance.
Do not recommend shorter sessions solely because a task was difficult or mentally demanding.
Only set max_session_hours when the student explicitly indicates that:
- concentration dropped during longer sessions,
- the session felt too long,
- fatigue increased during the session,
- or shorter blocks would likely improve focus or performance.

If the task was difficult but focus remained good, prefer a time buffer or high-energy preference instead of shorter sessions.
Time buffer decision rule:
- Original estimated hours: {estimated_hours}
- Planned / adjusted hours used by the planner: {adjusted_hours}
- Actual hours spent: {actual_hours}
- When deciding whether to suggest a larger time buffer, compare actual hours mainly with the planned / adjusted hours.
- Do not suggest increasing the buffer further if actual hours are already close to the adjusted planned hours.
- Small differences between adjusted planned hours and actual hours should be treated as normal estimation variation.
- Only suggest a larger buffer if the student still clearly exceeds the adjusted planned hours.
If the student needed more time because similar tasks are unpredictable, cognitively demanding, or difficult to sustain, a buffer may be appropriate.
If the conversation only supports shorter sessions, set max_session_hours but keep add_time_buffer_percent at 0.
If the conversation only supports more time, set add_time_buffer_percent but do not force shorter sessions.

The proposal_text should describe what the system should remember for future similar tasks.

Good examples:
- "For Philosophy / Study / Learning tasks, prior familiarity can make the task faster and less demanding. Avoid adding extra time buffer unless future feedback shows underestimation again."
- "For Programming / Practice tasks, debugging and unclear steps often make the task take longer. Future similar tasks may need more time buffer and shorter sessions."

Bad examples:
- "The student did well."
- "Use Cognitive Load Theory."
- "Always plan 1 hour."
- "Ask whether the topic is familiar."

Student:
{student_name}

Current task:
- Task: {task_name}
- Subject: {subject}
- Task type: {task_type}

Student context:
{student_context}

Reflection conversation:
{conversation_text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    raw_text = response.text.strip()
    cleaned_text = raw_text

    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text.removeprefix("```json").strip()
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.removeprefix("```").strip()

    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text.removesuffix("```").strip()

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        return {
            "has_proposal": False,
            "proposal_text": None,
            "reason": "Could not parse proposal."
        }


def chat_with_system_guide(student_name: str, chat_history: list, user_message: str) -> str:
    client = get_client()

    system_context = """
You are an AI help assistant for a Streamlit study planning app.

App structure:
- Dashboard:
  - shows today's study plan
  - shows feedback reminders
  - shows current open tasks
  - shows a this-week workload overview
  - shows recent feedback
  - includes an AI Help Assistant
- Planning Setup:
  - Task Setup:
    - students can add tasks
    - task fields include task name, subject / course, task type, importance level, deadline, and estimated hours
    - task type options are:
      - Study / Learning
      - Reading
      - Practice
      - Writing
      - Review
      - Administrative
    - the student enters the estimated hours themselves
    - task intensity is assigned automatically based on task type
    - estimated_hours reflects the original workload estimate
  - Daily Context Setup:
    - students can set wake time and sleep time per day
    - students can add daily activity blocks within the active part of the day
    - activity categories include Work/School, Physical activity, Social, Rest, and Other
    - sleep is entered through the wake/sleep window, not as a normal activity
    - Rest means awake rest, recovery, breaks, or moments where the student does not want to study
    - the remaining time between activities becomes possible study time
  - Generate Study Plan:
    - students can build a study plan based on tasks, deadlines, importance, automatically derived task intensity, daily activities, wake/sleep times, energy matching, and a daily hour limit
    - the plan is also saved in the database
- Saved Plan:
  - shows the saved study plan
  - includes the AI Study Coach
- Feedback:
  - students log actual hours worked
  - students say whether the task is completed
  - if not completed, they can enter remaining hours
  - feedback helps the system learn per student, per task type, and per subject
  - after feedback, an AI reflection coach can help the student interpret the feedback
- History:
  - Task Overview shows grouped task summaries
  - Feedback Log shows individual feedback moments
- Admin pages:
  - used for analytics and estimation accuracy
  - student accounts can be set inactive, reactivated, or deleted

Important concepts:
- estimated_hours = the student's original estimate
- task_intensity is not entered manually by the student
- task_intensity is derived automatically from task type
- when a task is completed, the system compares the total actual time spent on that task to the original estimated time
- if the task was completed over multiple feedback moments, the actual hours are summed across those moments
- when feedback is logged and a task is not completed, remaining_hours is used to keep the task open
- Build Study Plan also saves the plan in the study_plan table
- a task with status 'planned' is still open for planning
- a task with status 'completed' is finished
- a task with status 'incomplete' means it is not completed and currently has no remaining hours entered
- the planner derives study time from the wake/sleep window minus activity blocks
- the planner uses simple energy rules based on the most recent activity before a free study slot
- the planner also uses a daily study-hour limit to prevent overload on one day
- sleep and rest are not the same thing in the system

Your job:
- explain clearly how to use the system
- Always communicate in English.
- Never switch languages because of user-entered task names or course names.
- answer navigation questions
- explain buttons, pages, and concepts in simple language
- help the user understand where to do something
- do not invent features that are not described
- be concise, helpful, and student-friendly
"""

    conversation_text = _build_conversation_text(chat_history, "No previous conversation yet.")

    prompt = f"""
{system_context}

Student name: {student_name}

Conversation so far:
{conversation_text}

Latest student question:
{user_message}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text


def _build_learning_profile_lookup(learning_profile_rows: list) -> dict:
    lookup = {}

    for row in learning_profile_rows:
        (
            task_type,
            subject,
            planning_factor,
            feedback_count,
            avg_difficulty,
            avg_mental_effort,
            avg_confidence,
            avg_focus,
            updated_at
        ) = row

        lookup[(task_type, subject)] = {
            "planning_factor": float(planning_factor or 1.0),
            "feedback_count": int(feedback_count or 0),
            "avg_difficulty": float(avg_difficulty or 0.0),
            "avg_mental_effort": float(avg_mental_effort or 0.0),
            "avg_confidence": float(avg_confidence or 0.0),
            "avg_focus": float(avg_focus or 0.0),
        }

    return lookup


def get_planner_advice(student_name: str, student_context: str, tasks: list, learning_profile_rows: list) -> dict:
    client = get_client()
    learning_profile_lookup = _build_learning_profile_lookup(learning_profile_rows)

    task_lines = []

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

        profile = learning_profile_lookup.get((task_type, subject), {})
        feedback_count = int(profile.get("feedback_count", 0))

        task_lines.append(
            f"- task_id: {task_id} | "
            f"name: {task_name} | "
            f"subject: {subject} | "
            f"type: {task_type} | "
            f"importance: {importance_level} | "
            f"intensity: {task_intensity} | "
            f"deadline: {deadline} | "
            f"estimated_hours: {estimated_hours} | "
            f"adjusted_hours: {adjusted_hours} | "
            f"learning_feedback_count_for_same_type_and_subject: {feedback_count} | "
            f"historical_time_ratio: {round(float(profile.get('planning_factor', 1.0)), 2) if profile else 'N/A'} | "
            f"avg_difficulty: {round(float(profile.get('avg_difficulty', 0.0)), 2) if profile else 'N/A'} | "
            f"avg_mental_effort: {round(float(profile.get('avg_mental_effort', 0.0)), 2) if profile else 'N/A'} | "
            f"avg_confidence: {round(float(profile.get('avg_confidence', 0.0)), 2) if profile else 'N/A'} | "
            f"avg_focus: {round(float(profile.get('avg_focus', 0.0)), 2) if profile else 'N/A'} | "
            f"status: {status} | "
            f"spread_learning: {is_spread_learning} | "
            f"preferred_study_days: {preferred_study_days} | "
            f"min_session_hours: {min_session_hours} | "
            f"max_session_hours: {max_session_hours}"
        )

    tasks_text = "\n".join(task_lines) if task_lines else "No tasks available."

    prompt = f"""
You are NOT the scheduler.

You are the theory-grounded personalization layer of the study planning system.

Your role is to:
- interpret the student's historical learning behaviour,
- reason about cognitive and motivational patterns,
- detect possible workload risks,
- and return task-level personalization recommendations.

The deterministic planner is responsible for:
- deadlines,
- available time windows,
- daily capacity,
- slot allocation,
- no-overlap logic,
- and hard scheduling constraints.

You do NOT directly schedule tasks.
You only provide personalized planning recommendations based on educational psychology theory and historical student behaviour.

Your recommendations should be treated as adaptive hypotheses, not absolute truths.

Use the following educational psychology theories as reasoning foundations:

{THEORY_PROMPT}

Your task:
Translate the student's historical feedback, learning profile, and current task context into personalized planning recommendations for the scheduler.

Do not use rigid threshold-based reasoning.
Do not assume one feedback moment proves a stable behavioral pattern.
Reason dynamically from the theories and the available student context.
If little or no historical data is available for the same task type and subject, avoid strong personalization.

Return ONLY valid raw JSON.
Do not use markdown.
Do not wrap the JSON in triple backticks.
Do not add explanations outside the JSON.

Schema:
{{
  "task_recommendations": [
    {{
      "task_id": <int>,
      "add_time_buffer_percent": <int from 0 to 30>,
      "preferred_energy": <"High" | "Medium" | "Low" | null>,
      "max_session_hours": <0.5 | 1.0 | 1.5 | null>,
      "avoid_after_high_difficulty_task": <true | false>,
      "reason": <short string>
    }}
  ]
}}

Guidance:
- Make recommendations per task.
- Use the theories to reason about possible patterns in planning accuracy, cognitive load, self-efficacy, self-regulation, metacognition, distributed practice, and mental fatigue.
- The reason should briefly explain the interpretation, not quote rules.
- If no meaningful personalization is justified, return neutral values:
  add_time_buffer_percent = 0,
  preferred_energy = null,
  max_session_hours = null,
  avoid_after_high_difficulty_task = false.
- Keep the reason short and grounded in the provided data.
- Do not invent data.

Student name:
{student_name}

Student context:
{student_context}

Tasks:
{tasks_text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    raw_text = response.text.strip()
    cleaned_text = raw_text

    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text.removeprefix("```json").strip()
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.removeprefix("```").strip()

    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text.removesuffix("```").strip()

    try:
        parsed = json.loads(cleaned_text)
        return parsed
    except json.JSONDecodeError:
        return {"task_recommendations": []}


def validate_planner_advice(advice: dict) -> dict:
    cleaned = {"task_recommendations": []}

    if not isinstance(advice, dict):
        return cleaned

    items = advice.get("task_recommendations", [])
    if not isinstance(items, list):
        return cleaned

    valid_energy = {"High", "Medium", "Low", None}
    valid_sessions = {0.5, 1.0, 1.5, None}

    for item in items:
        if not isinstance(item, dict):
            continue

        task_id = item.get("task_id")
        if not isinstance(task_id, int):
            continue

        add_time_buffer_percent = item.get("add_time_buffer_percent", 0)
        if not isinstance(add_time_buffer_percent, int):
            add_time_buffer_percent = 0
        add_time_buffer_percent = max(0, min(30, add_time_buffer_percent))

        preferred_energy = item.get("preferred_energy")
        if preferred_energy not in valid_energy:
            preferred_energy = None

        max_session_hours = item.get("max_session_hours")
        if max_session_hours not in valid_sessions:
            max_session_hours = None

        avoid_after_high_difficulty_task = item.get("avoid_after_high_difficulty_task", False)
        if not isinstance(avoid_after_high_difficulty_task, bool):
            avoid_after_high_difficulty_task = False

        reason = item.get("reason", "")
        if not isinstance(reason, str):
            reason = ""

        cleaned["task_recommendations"].append({
            "task_id": task_id,
            "add_time_buffer_percent": add_time_buffer_percent,
            "preferred_energy": preferred_energy,
            "max_session_hours": max_session_hours,
            "avoid_after_high_difficulty_task": avoid_after_high_difficulty_task,
            "reason": reason.strip()
        })

    return cleaned