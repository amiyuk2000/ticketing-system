# Facilities Ticketing System

A Django web app for reporting and tracking facilities issues (electrical, plumbing, HVAC, cleaning) across buildings. Staff log in, raise tickets, filter them by location, category, priority and status, and see the tickets assigned to them.

**Live demo:** https://YOUR-USERNAME.pythonanywhere.com
**Demo login:** `demo` / `demo1234`

<!-- Add a screenshot: save it as docs/screenshot.png and uncomment the line below -->
<!-- ![Ticket list](docs/screenshot.png) -->

## Features

- Create and view tickets with title, description, location, category, priority, status and assignee
- Filter the ticket list by location (partial match), category, priority and status
- "My Assigned" view showing only the tickets assigned to the logged-in user
- Ticket counts per category
- Login and logout using Django's built-in authentication
- Django admin for managing tickets and users

## Tech stack

- Python 3.12, Django 6.1
- SQLite
- Django templates (server-rendered HTML, no JavaScript framework)

## Project structure

```
ticketing_system/      Project settings and URL routing
tickets/
  models.py            Ticket model
  views.py             List, create, detail, assigned and counts views
  forms.py             Ticket ModelForm
  templates/           HTML templates (base layout, tickets/, registration/)
  management/commands/
    seed_demo.py       Creates a demo user and sample tickets
  tests.py             View tests
```

## Running locally

```bash
git clone https://github.com/YOUR-USERNAME/ticketing-system.git
cd ticketing-system
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo     # optional: demo user + sample tickets
python manage.py runserver
```

Open http://127.0.0.1:8000/ and log in with `demo` / `demo1234`.
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
| `DJANGO_ALLOWED_HOSTS` | empty (localhost)  | `YOUR-USERNAME.pythonanywhere.com`   |

## Deploying to PythonAnywhere

1. In a PythonAnywhere Bash console:
   ```bash
   git clone https://github.com/YOUR-USERNAME/ticketing-system.git
   cd ticketing-system
   mkvirtualenv venv --python=python3.12
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic
   python manage.py seed_demo
   ```
2. On the **Web** tab, add a new web app with **Manual configuration** and Python 3.12.
3. Set **Virtualenv** to `/home/YOUR-USERNAME/.virtualenvs/venv`.
4. Replace the contents of the **WSGI configuration file** with:
   ```python
   import os, sys
   path = '/home/YOUR-USERNAME/ticketing-system'
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ['DJANGO_SETTINGS_MODULE'] = 'ticketing_system.settings'
   os.environ['DJANGO_SECRET_KEY'] = 'paste-a-long-random-string-here'
   os.environ['DJANGO_DEBUG'] = 'False'
   os.environ['DJANGO_ALLOWED_HOSTS'] = 'YOUR-USERNAME.pythonanywhere.com'

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
   To generate a secret key:
   `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
5. Under **Static files**, map URL `/static/` to `/home/YOUR-USERNAME/ticketing-system/staticfiles`.
6. Under **Security**, turn on **Force HTTPS**.
7. Click **Reload**.

To deploy updates later, run `git pull` in the console (plus `migrate` / `collectstatic` if needed) and click **Reload**.
