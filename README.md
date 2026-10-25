# Facilities Ticketing System

[![Tests](https://github.com/amiyuk2000/ticketing-system/actions/workflows/tests.yml/badge.svg)](https://github.com/amiyuk2000/ticketing-system/actions/workflows/tests.yml)

A Django web app for reporting and tracking facilities issues (electrical, plumbing, HVAC, cleaning) across buildings. Staff report problems, managers triage and assign them, and technicians work through the tickets assigned to them.

**Live demo:** https://amiyuk2000.pythonanywhere.com

| Demo account | Password   | Role                                          |
|--------------|------------|-----------------------------------------------|
| `manager`    | `demo1234` | Full access: assign tickets, view reports     |
| `technician` | `demo1234` | Update the status of tickets assigned to them |
| `staff`      | `demo1234` | Report issues, edit their own open tickets    |

<!-- Add a screenshot: save it as docs/screenshot.png and uncomment the line below -->
<!-- ![Ticket list](docs/screenshot.png) -->

## Features

- Create, view and edit tickets with title, description, location, category, priority, status and assignee
- **Role-based permissions** (Managers, Technicians, Staff) enforced on the server, not just hidden in the UI
- Filter the ticket list by location (partial match), category, priority and status
- **Pagination** that keeps the active filters when changing page
- "My Assigned" view showing only the tickets assigned to the logged-in user
- Manager-only report of tickets per category
- Responsive Bootstrap 5 UI with colour-coded priority and status badges
- Login and logout using Django's built-in authentication
- Django admin for managing tickets, users and roles
- **CI** with GitHub Actions: tests, system checks and a missing-migrations check on every push

## Roles and permissions

Roles are Django groups, created by a data migration. The rules live in one place, [`tickets/permissions.py`](tickets/permissions.py):

| Action                   | Staff                   | Technician               | Manager |
|--------------------------|-------------------------|--------------------------|---------|
| See and filter tickets   | Ones they reported      | Assigned to them, or reported by them | All     |
| Report a ticket          | ✅                      | ✅                       | ✅      |
| Edit details of a ticket | Own tickets, while open | —                        | ✅      |
| Change status            | —                       | Tickets assigned to them | ✅      |
| Assign to a technician   | —                       | —                        | ✅      |
| View reports             | —                       | —                        | ✅      |

Every ticket query starts from `visible_tickets(user)`, so a ticket outside a user's scope returns **404 Not Found**, even when they type its URL directly, and the response doesn't reveal that it exists. Each role only sees the form fields it may change, and the server ignores any other fields in a submitted form. Actions a role can't take on a ticket it *can* see return **403 Forbidden**. To give someone a role, add them to the **Managers** or **Technicians** group in the Django admin.

## Performance notes

- The ticket list uses `select_related('assigned_to')`, so assignee names are loaded in the same SQL query as the tickets. Without it, a page of 10 tickets would run 10 extra queries (the "N+1 query" problem). A test checks that the query count stays fixed.
- Lists are paginated at 10 tickets per page with Django's `Paginator`, so pages stay fast as the number of tickets grows.

## Tech stack

- Python 3.12, Django 6.1
- SQLite
- Django templates (server-rendered HTML, no JavaScript framework)

## Project structure

```
ticketing_system/      Project settings and URL routing
tickets/
  models.py            Ticket model
  views.py             List, create, detail, edit, assigned and report views
  forms.py             Ticket ModelForm (shows only the fields a role may change)
  permissions.py       Role rules: who can create, edit and view what
  context_processors.py  Makes the user's role available to templates
  templates/           HTML templates (base layout, tickets/, registration/, 403)
  templatetags/        Badge colour filters
  management/commands/
    seed_demo.py       Creates one demo user per role and sample tickets
  tests.py             View, permission and pagination tests
.github/workflows/
  tests.yml            GitHub Actions CI
```

## Running locally

```bash
git clone https://github.com/amiyuk2000/ticketing-system.git
cd ticketing-system
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo     # optional: demo users + sample tickets
python manage.py runserver
```

Open http://127.0.0.1:8000/ and log in as `manager`, `technician` or `staff` (password `demo1234`).
To use the admin at `/admin/`, create an account with `python manage.py createsuperuser`.

## Running tests

```bash
python manage.py test
```

## Configuration

Settings are read from environment variables. The defaults work for local development.

| Variable               | Default            | Production value                     |
|------------------------|--------------------|--------------------------------------|
| `DJANGO_SECRET_KEY`    | insecure dev key   | a long random string                 |
| `DJANGO_DEBUG`         | `True`             | `False`                              |
| `DJANGO_ALLOWED_HOSTS` | empty (localhost)  | `amiyuk2000.pythonanywhere.com`   |

## Deploying to PythonAnywhere

1. In a PythonAnywhere Bash console:
   ```bash
   git clone https://github.com/amiyuk2000/ticketing-system.git
   cd ticketing-system
   mkvirtualenv venv --python=python3.12
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic
   python manage.py seed_demo
   ```
2. On the **Web** tab, add a new web app with **Manual configuration** and Python 3.12.
3. Set **Virtualenv** to `/home/amiyuk2000/.virtualenvs/venv`.
4. Replace the contents of the **WSGI configuration file** with:

   ```python
   import os, sys
   path = '/home/amiyuk2000/ticketing-system'
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ['DJANGO_SETTINGS_MODULE'] = 'ticketing_system.settings'
   os.environ['DJANGO_SECRET_KEY'] = 'paste-a-long-random-string-here'
   os.environ['DJANGO_DEBUG'] = 'False'
   os.environ['DJANGO_ALLOWED_HOSTS'] = 'amiyuk2000.pythonanywhere.com'

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

   To generate a secret key:
   `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
5. Under **Static files**, map URL `/static/` to `/home/amiyuk2000/ticketing-system/staticfiles`.
6. Under **Security**, turn on **Force HTTPS**.
7. Click **Reload**.

To deploy updates later, run `git pull` in the console (plus `migrate` / `collectstatic` if needed) and click **Reload**.
