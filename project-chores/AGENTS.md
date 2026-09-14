## Project Chores

The Django app lives in `project-chores/` (this project's app subfolder), not
here at this file's level. Full backlog and plan: `_docs/backlog.md` and
`_docs/plan.md`.

Commands (run from inside `project-chores/`):

- `python3 -m venv .venv` - create the virtualenv (first time only)
- `source .venv/bin/activate` - activate the virtualenv
- `pip install -r requirements.txt` - install dependencies
- `python manage.py runserver` - start the dev server
- `python manage.py test chores` - run the whole test suite
- `python manage.py test chores.tests.SkipViewTests` - run one test class
- `python manage.py makemigrations chores && python manage.py migrate` - after model changes
- `python manage.py seed_demo_data` - populate demo members/chores/rotations (idempotent)

Rules

- Dependencies are added in `project-chores/requirements.txt`. Do not add one without
  asking.
- Stack is deliberately minimal: Django with server-rendered templates only, no JS
  framework, SQLite. Don't introduce a frontend build step or JS framework without asking.
- No bars/meters/progress visuals, no notifications, no analytics, no gamification -
  see `_docs/plan.md` (Non-Goals) before adding UI or features.
- `_docs/backlog.md` tracks build status; check it off as tasks are
  completed and add new tasks there rather than in ad-hoc notes.
