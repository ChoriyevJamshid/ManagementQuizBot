# Report 1: Scheduled Quiz Auto-Start Logic

**Date:** 2026-05-01

---

## General Flow (works correctly)

```
Creation → CeleryBeat fires 1 hour before quiz
    ↓ run_scheduled_quiz
Sends "1 hour left" notification to group
    ↓ (countdown 50 min) notify_before_quiz(10m)
    ↓ (countdown 55 min) notify_before_quiz(5m)
    ↓ (countdown 60 min) start_scheduled_group_quiz
Creates GroupQuiz, sends "Ready" button to group
```

---

## Bugs Found

### Bug 1 (Moderate): Missing `poll_id` when creating `GroupQuiz`

`quiz/tasks.py:157` — `GroupQuiz.objects.create(...)` does not pass `poll_id`:

```python
GroupQuiz.objects.create(
    part=quiz_part,
    user=scheduled.created_by,
    group_id=scheduled.group_id,
    message_id=message_id,
    title=scheduled.group_title or '',
    invite_link='',
    # poll_id is missing!
)
```

The field `poll_id = models.CharField(max_length=255)` has no `default` and no `blank=True`. Django will insert `''` (empty string) into the DB — no crash, but semantically incorrect. `poll_id` should be updated later when Telegram returns the poll ID.

**Fix:** explicitly pass `poll_id=''` in the create call.

---

### Bug 2 (Minor): One-time `PeriodicTask` is only disabled, not deleted

`quiz/tasks.py:169-171`:

```python
PeriodicTask.objects.filter(pk=scheduled.periodic_task_id).update(enabled=False)
```

For a one-time quiz the task is created with `one_off=True`. After execution it is only disabled but never removed from `django_celery_beat`, causing stale records to accumulate over time.

**Fix:** use `.delete()` instead of `.update(enabled=False)`.

---

### Potential Issue: `get_distinct_groups` — limited scan

`bot/utils/orm.py:172` — when selecting a group from the list, only the last `limit * 5 = 50` `GroupQuiz` records are scanned. If a group has not held a quiz recently and falls outside those 50 records, it will not appear in the dropdown. The admin must then enter the group ID manually.

---

## What Works Correctly

| Aspect | Status |
|---|---|
| Notifications at 1h / 10m / 5m | ✅ |
| `is_active` check in all tasks | ✅ |
| Guard against starting if quiz already active | ✅ |
| Midnight hour shift (`hour=0 → task_hour=23`) | ✅ |
| Day-of-week shift for periodic quizzes at `hour=0` | ✅ |
| Deactivation after one-time quiz completes | ✅ |
| `updated_at` via `auto_now` handled correctly | ✅ |

---

## Recommended Fixes

### 1. `quiz/tasks.py:157` — add `poll_id=''`

```python
GroupQuiz.objects.create(
    part=quiz_part,
    user=scheduled.created_by,
    group_id=scheduled.group_id,
    message_id=message_id,
    title=scheduled.group_title or '',
    invite_link='',
    poll_id='',  # will be set later when poll is created
)
```

### 2. `quiz/tasks.py:169-171` — delete task instead of disabling

```python
if scheduled.periodic_task_id:
    from django_celery_beat.models import PeriodicTask
    PeriodicTask.objects.filter(pk=scheduled.periodic_task_id).delete()
```
