# Fencing Club

A web app for running a fencing club's training sessions and attendance: group classes, private lessons, and physical conditioning. Managers plan sessions on a calendar, take attendance, and manage members, coaches, and logins. Coaches mark attendance for their own sessions. Members book group sessions, ask their coaches for private lessons, and edit their own profile. Everyone can subscribe to their sessions in Google Calendar.

It's a Django app with server-rendered pages. htmx swaps parts of a page without reloading it, Alpine.js holds small bits of browser state, and FullCalendar draws the calendars. It works on a computer or a phone.

For what the app does and why, see [Fencing Club App PRD.md](Fencing%20Club%20App%20PRD.md).

## Contents

- [Features](#features)
- [Getting started](#getting-started)
- [Trying each role](#trying-each-role)
- [Project layout](#project-layout)
- [How a request works](#how-a-request-works)
- [Data model](#data-model)
- [Roles and permissions](#roles-and-permissions)
- [Tests](#tests)
- [Configuration](#configuration)
- [Deploying](#deploying)
- [Common tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

## Features

**Managers**
- A week or day calendar of every session, showing headcounts (for example 3/12) and filters for coach, member, location, category, and weapon
- Create a session by dragging across empty time. Move or resize a session by dragging it, and the change saves straight away
- Each session has a category (fencing or physical conditioning) and a type (group or individual)
- A list view of the same sessions, split into upcoming and past
- A side panel for each session: edit it, add or remove members, mark attendance, write notes, repeat it weekly, and delete it (or it and the rest of its series)
- Members and Coaches pages, each with a side panel showing details, attendance rate, session history, and login
- Invite coaches and members by email, resend invites, and switch logins off and on
- Accept or decline private lesson requests

**Coaches**
- A calendar and list of the sessions they coach
- Mark attendance and write notes for their own sessions
- Accept or decline lesson requests sent to them

**Members**
- A calendar and list of the sessions they're on
- Book an upcoming group session with space, or cancel a booking before it starts
- Request a private lesson from their primary coach or the coach of a session they're on, choosing from the coach's free times
- Edit their name, phone, and weapon, and see their attendance record

**Everyone**
- Calendar sync: a secret `.ics` link to add to Google Calendar or any calendar app
- Invite and password-reset emails, with links that work once and expire after 7 days
- Rate-limited login and password resets

## Getting started

You need Python 3.10 or newer.

```bash
git clone <this repo's URL> fencing_club_app
cd fencing_club_app

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser   # this login is a manager
python manage.py runserver
```

Open http://localhost:8000 and log in with the superuser you created.

Locally, nothing needs configuring. Debug is on, the database is `db.sqlite3` in the project folder, and emails print in the `runserver` terminal rather than being sent.

**After pulling new code**, run `python manage.py migrate` again. If you see `no such table` or `no such column`, a migration hasn't been run yet. `python manage.py showmigrations` lists any that are missing with `[ ]`.

## Trying each role

The superuser is a manager. To try being a coach or a member:

1. As the manager, add a coach or member on the Coaches or Members page, and give them an email address
2. Open them and click **Invite** in their Login row
3. The invite email prints in the `runserver` terminal. Open its link in a private browser window
4. Choose a password, and you're logged in as them

The username is their email address. You can also give someone a login from the Django admin at http://localhost:8000/admin/ by adding a user and a profile.

## Project layout

```
fencing_club_app/
├── config/                  The Django project
│   ├── settings.py          Settings, mostly from environment variables online
│   └── urls.py              /admin/ goes to Django's admin; everything else to web/urls.py
├── club/                    The club: data and rules. Nothing here knows about HTTP
│   ├── models.py            Member, Coach, TrainingSession, Attendance, Profile, CalendarFeed
│   ├── roles.py             role_of(user): 'manager', 'coach', 'member', or None
│   ├── queries.py           What each person may see. Every page asks here
│   ├── services.py          The rules for actions: enrol, repeat a session, request a lesson, invite...
│   ├── emails.py            Invite and password-reset emails and their links
│   ├── ical.py              Writes the .ics calendar feed
│   ├── admin.py             The Django admin screens
│   ├── migrations/
│   └── tests.py             Tests for the rules and queries
├── web/                     The website
│   ├── urls.py              Every page's URL
│   ├── views/               One file per area: auth, sessions, book, lessons, members, coaches, feeds
│   │   └── common.py        role_required, and helpers for htmx response headers
│   ├── forms.py             Forms for sessions, members, coaches, lessons, and logging in
│   ├── templatetags/club.py Template tags for status and weapon badges
│   ├── templates/web/       Django templates, one folder per area, plus partials/
│   ├── static/web/          app.css, app.js, and vendored htmx, Alpine.js and FullCalendar
│   └── tests/               Tests that load pages through Django's test client
├── manage.py
└── requirements.txt
```

**The main idea:** `club` decides what's allowed and what's visible, and `web` turns that into pages. A view checks the person's role, gets data through `club/queries.py`, changes it through `club/services.py`, and renders a template. Keeping the rules in `club` means every page follows the same ones.

## How a request works

Take a member clicking **Enrol** in a session's side panel:

1. htmx sends `POST /sessions/42/enrol/`. The CSRF token comes from `hx-headers` on `<body>` in `base.html`
2. `web/urls.py` sends it to `sessions.enrol` in `web/views/sessions.py`
3. `@role_required(MEMBER)` checks the person is logged in as a member and sets `request.role`
4. The view finds the session through `queries.visible_sessions()`, so a member can't reach a session they aren't allowed to see
5. `services.enrol()` checks the rules. If the session has started, is full, or the member is already on it, it raises a `ValidationError` with a message to show
6. The view renders `sessions/panel.html` again, with any message, and adds an `HX-Trigger: sessionsChanged` header
7. htmx swaps the new panel into the page. The calendar hears `sessionsChanged` and reloads its sessions, so the headcount updates

Most features work the same way. A few things worth knowing:

- **Views return HTML, not JSON.** The exceptions are `calendar_events` and `lesson_events`, which give FullCalendar its events as JSON, and `calendar_feed`, which returns the `.ics` file
- **htmx response headers** coordinate the page. `HX-Trigger` fires events such as `sessionsChanged`, `HX-Trigger-After-Swap: closeModal` closes a dialog once it saves, and `HX-Retarget` puts a response somewhere other than where it was asked for. The `htmx()` helper in `web/views/common.py` sets them
- **Dialogs** load into `<div id="modal">` and close by emptying it. **Side panels** load into `<div id="panel">`
- **Alpine.js** components live in `web/static/web/app.js`: `peek` (which side panel is open), `filters` (the session filters, kept in the URL), `sessionCalendar`, and `lessonCalendar`

## Data model

| Model | What it is |
| --- | --- |
| `Member` | A fencer: name, contact details, weapon, active, and an optional primary coach |
| `Coach` | A coach: name, contact details, weapon, and active |
| `TrainingSession` | One session on one date: times, coach, location, category (fencing or conditioning), type (group or individual), status (confirmed or unconfirmed), weapon, capacity, and notes. Weekly copies share a `series` ID |
| `Attendance` | A member on a session, with a status of enrolled, present, absent, or excused. One per member per session |
| `Profile` | Gives a Django `User` a role (coach or member) and links the login to their `Coach` or `Member` |
| `CalendarFeed` | The secret token in a person's calendar feed URL |

Members and coaches are separate from logins. A member can be in the club without being able to log in, and gets a login only when a manager invites them. **Managers are staff users** (`is_staff`) and have no profile.

**A private lesson is an individual session.** When a member asks for one, it's saved as an unconfirmed individual `TrainingSession` with them on it. The coach confirming it changes its status. Declining or cancelling deletes it. Because requests share the table with real sessions, `queries.sessions()` returns only confirmed ones, and only `queries.requests()` and `queries.lessons()` include unconfirmed ones. Start from those, not `TrainingSession.objects`, so a request never shows up as if it were booked.

The PRD has every field.

## Roles and permissions

`club/roles.py` works out each person's role, and every view is protected with `@role_required(...)` from `web/views/common.py`.

| | Manager | Coach | Member |
| --- | --- | --- | --- |
| Sessions on calendar and list | All, with filters | Own | Own |
| Create, move, edit, repeat, delete sessions | Yes | No | No |
| Mark attendance and edit notes | Yes | Own sessions | No |
| Book or cancel a group session | No | No | Self |
| Private lessons | Answer any | Answer own | Request and cancel |
| Members and Coaches pages | Yes | No | Own profile only |
| Manage logins | Yes | No | No |
| Calendar sync | All sessions | Own sessions | Own sessions |

**The calendar feed needs no login.** Calendar apps fetch `/calendar/<token>.ics` on their own, so the secret token in the URL is the only check. Resetting the link on the Calendar sync page replaces the token.

## Tests

```bash
python manage.py test
```

- `club/tests.py` tests the rules in `services.py` and `queries.py` directly
- `web/tests/` tests pages through Django's test client, one file per area. `web/tests/base.py` sets up a manager, a coach, two members, and a session that most tests share

Run one file or one test with:

```bash
python manage.py test web.tests.test_sessions
python manage.py test web.tests.test_sessions.CalendarTests.test_dragging_moves_a_session
```

## Configuration

Settings come from environment variables. Locally you don't need any of them.

| Variable | Default | What it does |
| --- | --- | --- |
| `DJANGO_DEBUG` | `true` | Set to `false` online |
| `DJANGO_SECRET_KEY` | A development key | Required when debug is off |
| `SITE_HOST` | None | The site's address, for example `jorellesee.pythonanywhere.com`. Allows the host, and is used in email links and calendar feed IDs. Render sets `RENDER_EXTERNAL_HOSTNAME`, which works the same way |
| `SQLITE_PATH` | `db.sqlite3` in the project | Where the database lives |
| `EMAIL_HOST` | None | An SMTP server, for example `smtp.gmail.com`. Without it, emails print in the terminal |
| `EMAIL_PORT` | `587` | |
| `EMAIL_HOST_USER` | | |
| `EMAIL_HOST_PASSWORD` | | For Gmail, an app password |
| `DEFAULT_FROM_EMAIL` | `Fencing Club <noreply@localhost>` | The From address on emails |

Other settings worth knowing, in `config/settings.py`:

- `TIME_ZONE = 'Asia/Singapore'`. Times are stored in UTC and shown in this zone
- `PASSWORD_RESET_TIMEOUT` is 7 days, how long invite and reset links work

## Deploying

The app runs anywhere that can run a Django WSGI app with a permanent place for the SQLite file. It has run on **PythonAnywhere** (free, with permanent files) and **Render** (which needs a paid persistent disk for the database).

On any host:

1. Set `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY` to a long random value, and `SITE_HOST`. Set the `EMAIL_*` variables so invites are actually sent
2. Install the requirements, then run:
   ```bash
   python manage.py collectstatic --noinput   # with the same environment variables as the site
   python manage.py migrate
   ```
3. Serve `config.wsgi:application`. On Render that's `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`. On PythonAnywhere, point the WSGI file at it and click **Reload**
4. Create the first manager with `python manage.py createsuperuser`

Static files are served by WhiteNoise, so no separate static file server is needed. With debug off, `collectstatic` gives files hashed names so browsers fetch new versions after a deploy.

**To update a deployed site:** pull the new code, run `collectstatic` and `migrate`, then restart or reload.

**Back up `db.sqlite3` now and then.** It holds all the club's data, and no host here backs it up for you.

## Common tasks

**Change a model**
1. Edit `club/models.py`
2. `python manage.py makemigrations`, and read the migration it writes
3. `python manage.py migrate`
4. Commit the model change and the migration together

**Add a page**
1. Write a view in the right file under `web/views/`, with `@role_required(...)` for who may see it
2. Get data through a function in `club/queries.py`, and put any rules in `club/services.py`
3. Add its URL to `web/urls.py`, and a template under `web/templates/web/`
4. Add it to the sidebar in `web/templates/web/layout.html` if it needs a link
5. Write a test in `web/tests/`

**Update a vendored library** (htmx, Alpine.js, FullCalendar): replace the file in `web/static/web/vendor/`. There's no npm or build step.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `OperationalError: no such table` or `no such column` | Run `python manage.py migrate` |
| "Wrong username or password" when the password is right | The login has no role. Make it staff, or give it a profile in the admin |
| No invite email arrived | Locally, look in the `runserver` terminal. Online, check the `EMAIL_*` variables |
| An invite link says it's expired or used | Resend the invite from the person's Login row |
| Online, the page has no styles, or a 500 mentioning the manifest | Run `collectstatic` with `DJANGO_DEBUG=false` set |
| Online, a 400 Bad Request | `SITE_HOST` doesn't match the address you're using |
| Google Calendar doesn't show a change | Google refreshes subscribed calendars every few hours. Wait, or check the feed link in a browser |
