from datetime import datetime
from Database import get_due_feedback_tasks

student_id = "testfeedback"

print("AFTER FIRST BLOCK")
print(
    get_due_feedback_tasks(
        student_id,
        datetime(2026, 5, 19, 23, 0)
    )
)

print("\nAFTER SECOND BLOCK")
print(
    get_due_feedback_tasks(
        student_id,
        datetime(2026, 5, 21, 23, 0)
    )
)

print("\nAFTER FINAL BLOCK")
print(
    get_due_feedback_tasks(
        student_id,
        datetime(2026, 5, 23, 23, 0)
    )
)