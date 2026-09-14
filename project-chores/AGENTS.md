The Django project lives in `project-chores/`, not the repo root.

Commands

- `cd project-chores && python3 -m venv .venv` - create the virtualenv (first time only)
- `source project-chores/.venv/bin/activate` - activate the virtualenv
- `pip install -r project-chores/requirements.txt` - install dependencies
- `cd project-chores && python manage.py runserver` - start the dev server
- `cd project-chores && python manage.py test chores` - run the whole test suite
- `cd project-chores && python manage.py test chores.tests.SkipViewTests` - run one test class
- `cd project-chores && python manage.py makemigrations chores && python manage.py migrate` - after model changes
- `cd project-chores && python manage.py seed_demo_data` - populate demo members/chores/rotations (idempotent)

Rules

- Dependencies are added in `project-chores/requirements.txt`. Do not add one without
  asking.
- Stack is deliberately minimal: Django with server-rendered templates only, no JS
  framework, SQLite. Don't introduce a frontend build step or JS framework without asking.
- No bars/meters/progress visuals, no notifications, no analytics, no gamification -
  see `project-chores/_docs/plan.md` (Non-Goals) before adding UI or features.
- `project-chores/_docs/backlog.md` tracks build status; check it off as tasks are
  completed and add new tasks there rather than in ad-hoc notes.
