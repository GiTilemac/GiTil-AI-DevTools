# Backlog — Household Chore Tool (Django)

Derived from `plan.md`. Stack: Django, server-rendered templates only (no JS framework), SQLite.
Scaffolding already done: `config` project + `chores` app created, `chores` registered in `INSTALLED_APPS`, `templates/` dir wired up.

## 1. Data model
- [x] `Member` model (name)
- [x] `Chore` model (name, difficulty: light/medium/heavy)
- [x] `RotationSlot` model — ordered rotation position of each member per chore
- [x] `Assignment` model — chore + member + week_start + status (assigned/completed/skipped/reassigned) + note
- [x] `OneOffTask` model — title + status (pending/completed/skipped) + note
- [x] Register all models in `admin.py`
- [x] `makemigrations` / `migrate`

## 2. Rotation engine
- [x] Function to compute/create the current week's `Assignment` for each chore, advancing through `RotationSlot` order
- [x] Manual reassignment: change an assignment's member, require a note, mark status `reassigned`
- [x] Rotation countdown helper (days left in current week)

## 3. Chore Dashboard (main view)
- [x] View: list each chore's current assignment (member, difficulty)
- [x] Text-only streak indicator per member (consecutive completed weeks)
- [x] Mark chore complete / skipped (skip requires note)
- [x] Link to one-off backlog

## 4. Chore History
- [x] View: chronological log of completed / skipped / reassigned assignments, date only
- [x] No analytics, no aggregation — plain list

## 5. One-Off Backlog
- [ ] View: list one-off tasks
- [ ] Add a one-off task
- [ ] Mark complete / skip (with note)

## 6. Templates & polish
- [ ] `base.html` with minimal nav (Dashboard / History / Backlog)
- [ ] Plain, minimal CSS — no bars/meters/progress visuals
- [ ] Forms for reassign / skip / add-task with required-note validation

## 7. Housekeeping
- [ ] `requirements.txt` (pin Django version)
- [x] `.gitignore` (`.venv/`, `db.sqlite3`, `__pycache__/`)
- [x] Basic tests: rotation advancement logic, streak calculation, skip/reassign validation, dashboard/history views, model constraints
- [ ] Seed/fixture data or a management command for initial members + chores
