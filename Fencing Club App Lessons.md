# Fencing Club App: Build Lessons

How to build the manager-only fencing club app: a Django backend with a REST API, and a React FullCalendar frontend. Each lesson builds on the one before.

| Lesson | What you build | What you learn |
| --- | --- | --- |
| [1. Setup](#lesson-1-setup) | A Django project and an app | Virtual environments, projects vs apps |
| [2. Models](#lesson-2-models) | The Members, Classes, and Attendance tables | Models, fields, migrations |
| [3. Admin](#lesson-3-the-django-admin) | A ready-made screen for editing the data | The Django admin |
| [4. API](#lesson-4-the-api) | URLs that React can call | Django REST Framework |
| [5. React](#lesson-5-the-react-calendar) | The FullCalendar screen talking to Django | Vite, fetch, CSRF, PATCH on drag |
| [6. Tests](#lesson-6-automated-tests) | Checks that the API works | Django's test runner |
| [7. Recurring classes](#lesson-7-recurring-classes) | Weekly repeats with copied rosters | `@action`, transactions, `bulk_create` |
| [10. Logins and roles](#lesson-10-logins-for-managers-coaches-and-members) | Coach and member logins with their own views | `OneToOneField`, DRF permissions, sessions, React context |
| [11. Calendar and table views](#lesson-11-a-calendar-and-a-table-for-every-role) | Two views per role, and class locations | Shared query helpers, lifting state up |
| [12. Creating in the app](#lesson-12-creating-classes-and-members-in-the-app) | New class and New member forms | Controlled forms, dates and time zones, server-side validation |
| [13. Going online](#lesson-13-putting-it-online-with-render) | The app on Render with a persistent disk | Environment variables, gunicorn, WhiteNoise, serving React from Django |
| [14. Editing and naming classes](#lesson-14-editing-classes-and-names-that-write-themselves) | Edit form, Generate name, class weapon, series edits | Create/edit in one form, `.update()`, lazy `useState` |

Versions used: Python 3.10, Django 5.2, Django REST Framework 3.18, Node 24+, React 19, FullCalendar 7.

**Final project layout:**

```
fencing_club_app/
├── .gitignore
├── Fencing Club App PRD.md
├── backend/                   Django
│   ├── .venv/                 (not in git)
│   ├── manage.py
│   ├── requirements.txt
│   ├── db.sqlite3             (not in git)
│   ├── config/                Project: settings.py, urls.py
│   └── club/                  App: models, admin, serializers, views, urls, tests
└── frontend/                  React (Vite)
    ├── node_modules/          (not in git)
    ├── package.json
    ├── vite.config.js
    └── src/                   main.jsx, App.jsx, AttendancePanel.jsx, api.js, App.css
```

---

## Daily habits

Before running any `python manage.py ...` command:

```bash
cd /Users/jorellesee/Projects/fencing_club_app/backend
source .venv/bin/activate
```

- `pwd` should end in `/backend`.
- Your prompt should start with `(.venv)`.
- Re-activate in every new terminal.
- `type python` should print `.../backend/.venv/bin/python`.

---

# Lesson 1: Setup

## Steps

**1. Make a backend folder**, so the React app can sit next to it later.

```bash
cd /Users/jorellesee/Projects/fencing_club_app
mkdir backend && cd backend
```

**2. Create a virtual environment.**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install Django** and record the version.

```bash
pip install "django>=5.2,<5.3"
pip freeze > requirements.txt
```

`requirements.txt` should have only a few lines (`asgiref`, `Django`, `sqlparse`). If it lists dozens of unrelated packages, the venv wasn't active when you ran `pip freeze`.

**4. Create the project.**

```bash
django-admin startproject config .
```

The `.` means "put it here", without an extra nested folder.

**5. Create an app.**

```bash
python manage.py startapp club
```

Then open `config/settings.py` and add `'club',` to the end of `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'club',
]
```

Indent with 4 spaces, keep the trailing comma, and save with Cmd+S. Django ignores any app that isn't in this list, so without it Django won't see your models.

**6. Run it.**

```bash
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000 to see the Django rocket page. Press Ctrl+C to stop the server.

**7. Set up `.gitignore`** in the project root:

```
.DS_Store
node_modules/
.env
.venv/
__pycache__/
db.sqlite3
```

## `.venv` vs `.env`

| | `.venv` | `.env` |
| --- | --- | --- |
| What it is | A folder | A text file |
| Holds | This project's Python and installed packages | Secrets and settings (`NAME=value` lines) |
| Created by | `python3 -m venv .venv` | You, by hand, when you need one |
| Commit to git? | No. Rebuild it from `requirements.txt` | No. Commit a `.env.example` with names but no values |

- **Why `.venv` exists:** each project gets its own package versions, so one project's Django 5.2 can't clash with another's Django 4.2.
- **Why `.env` exists:** secrets (like `SECRET_KEY`) and settings that differ between your laptop and the server don't belong in code. Settings read them from the environment instead.

To rebuild a venv from scratch:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Project vs app

- **`config/` is the project.** It holds site-wide settings and URLs, and there's only ever one.
- **`club/` is an app**: one feature area with its own models and views. A bigger site might have `club`, `payments`, `competitions` and so on.

| File | What it does |
| --- | --- |
| `manage.py` | The command you run: `runserver`, `migrate`, `shell`, `test`… |
| `config/settings.py` | All configuration: installed apps, database, timezone, secret key |
| `config/urls.py` | The site's main list of URLs |
| `config/wsgi.py`, `asgi.py` | How a production web server starts Django |
| `club/models.py` | The data: your tables |
| `club/migrations/` | The instructions that build those tables |
| `club/admin.py` | The admin screens for those tables |
| `club/views.py` | The logic that handles a request and returns a response |
| `club/tests.py` | Automated checks |
| `club/apps.py` | The app's config, used when you write `'club'` in `INSTALLED_APPS` |
| `__init__.py` | An empty file that marks a folder as a Python package |

## Troubleshooting Lesson 1

**`ModuleNotFoundError: No module named 'django'`.** Python can't see the venv. Check each of these:

1. **Is the venv active?** Run `source .venv/bin/activate`.
2. **Are you in `backend/`?** `manage.py` lives there.
3. **Was the project folder moved or renamed?** A venv can't be moved, because `.venv/bin/activate` hard-codes its original path. Delete it and rebuild:
   ```bash
   rm -rf .venv
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Is `python` an alias?** Run `type python`. If it says `python is an alias for /usr/bin/python3`, a line in `~/.zshrc` is overriding the venv. zsh checks aliases **before** `PATH`, and activating a venv only changes `PATH`. Put `#` in front of the `alias python=...` line in `~/.zshrc`, save, and open a new terminal.

**`can't open file '.../manage.py'`.** You're in the wrong folder. Run `cd backend`.

---

# Lesson 2: Models

**Goal:** create the three tables from the PRD, and practise using them from Python.

A **model** is a Python class that describes one database table. Each attribute is a column, and each object is a row. Django adds an auto-numbered `id` column to every model.

## Step 1: Set the club's timezone

In `config/settings.py`:

```python
TIME_ZONE = 'Asia/Singapore'
```

Leave `USE_TZ = True`. Django **stores** times in UTC and **shows** them in Singapore time.

## Step 2: The models

`club/models.py`:

```python
from django.db import models


class Member(models.Model):
    class Weapon(models.TextChoices):
        FOIL = 'foil', 'Foil'
        EPEE = 'epee', 'Épée'
        SABRE = 'sabre', 'Sabre'

    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    weapon = models.CharField(max_length=10, choices=Weapon.choices, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class FencingClass(models.Model):
    name = models.CharField(max_length=100)
    start = models.DateTimeField()
    end = models.DateTimeField()
    coach = models.CharField(max_length=100, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['start']
        verbose_name_plural = 'fencing classes'

    def __str__(self):
        return f'{self.name} ({self.start:%a %d %b %H:%M})'


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'present', 'Present'
        ABSENT = 'absent', 'Absent'
        ENROLLED = 'enrolled', 'Enrolled'
        EXCUSED = 'excused', 'Excused'

    fencing_class = models.ForeignKey(
        FencingClass, on_delete=models.CASCADE, related_name='attendance'
    )
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name='attendance'
    )
    status = models.CharField(max_length=10, choices=Status.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['fencing_class', 'member'],
                name='one_attendance_per_member_per_class',
            )
        ]

    def __str__(self):
        return f'{self.member} – {self.fencing_class}: {self.status}'
```

Leave **two** blank lines between top-level classes. That's the Python style convention (PEP 8).

| Code | Meaning |
| --- | --- |
| `models.Model` | Makes the class a database table (`club_member`) |
| `CharField(max_length=100)` | Short text |
| `EmailField` | Text that must look like an email address when entered through a form |
| `blank=True` | The field is optional in forms |
| `null=True` | The database may store "no value" (NULL) |
| `TextChoices` | Limits a field to fixed values. The first value is stored, the second is shown |
| `default=True` | The value used when none is given |
| `ForeignKey` | A link to a row in another table, stored as a `<name>_id` column |
| `on_delete=models.CASCADE` | Deleting the linked row deletes these rows too |
| `related_name='attendance'` | The name of the link going backwards, e.g. `junior.attendance.all()` |
| `UniqueConstraint` | The database refuses a second row with the same values |
| `class Meta` | Settings for the whole model: ordering, names, constraints |
| `__str__` | How a row is shown in the admin and the shell |

**Why `FencingClass` and not `Class`?** `class Class` is legal Python but confusing to read, and `class` is a reserved word in JavaScript.

**Why Enrolled and Excused statuses?** A member is first added to a class (Enrolled), then marked Present, Absent or Excused.

## Step 3: Create the tables

Run these after **every** model change:

```bash
python manage.py makemigrations
python manage.py migrate
```

Building one model at a time produces `0001_initial.py`, `0002_fencingclass.py` and `0003_attendance.py`.

## Step 4: Use the models in the shell

```bash
python manage.py shell
```

```python
from datetime import timedelta
from django.utils import timezone
from club.models import Member, FencingClass, Attendance

alex = Member.objects.create(name='Alex Tan', weapon='foil')
sam = Member.objects.create(name='Sam Lee', weapon='sabre')

start = timezone.now().replace(minute=0, second=0, microsecond=0)
junior = FencingClass.objects.create(
    name='Junior Foil', start=start, end=start + timedelta(hours=1), capacity=12
)

Member.objects.all()
Member.objects.filter(weapon='foil')
alex.get_weapon_display()

Attendance.objects.create(fencing_class=junior, member=alex, status='present')
Attendance.objects.create(fencing_class=junior, member=sam, status='absent')
junior.attendance.all()
junior.attendance.filter(status='present').count()

sam_row = junior.attendance.get(member=sam)
sam_row.status = 'present'
sam_row.save()

# Should raise IntegrityError, because of the unique constraint
Attendance.objects.create(fencing_class=junior, member=alex, status='absent')

# Cascade: deleting the class deletes its attendance
junior.delete()
Attendance.objects.count()   # 0
```

Type `exit()` to leave the shell.

## Concepts

### `makemigrations` vs `migrate`

| Thing | What it is | Who changes it |
| --- | --- | --- |
| **Models** | Your Python code in `club/models.py` | **You**, by editing |
| **Migration files** | Step-by-step instructions in `club/migrations/` | **`makemigrations`** |
| **Database** | The real tables in `db.sqlite3` | **`migrate`** |

```
You edit models.py  →  makemigrations  →  migration file  →  migrate  →  database tables
```

- `makemigrations` **writes the instructions**. It doesn't touch the database.
- `migrate` **carries them out**. It doesn't touch `models.py`.
- Neither command adds, edits or deletes **rows** (records). They change the **shape** of the tables.
- `python manage.py showmigrations club` shows which migrations are applied (`[X]`) and which aren't (`[ ]`).

### Keep every migration file

- Commit them to git with the model change that created them.
- They're how any other database (a server, a teammate's laptop, the test database) gets built: `migrate` replays them in order.
- Each one names the one before it (`dependencies`), so deleting one breaks the chain.
- The database's `django_migrations` table records which ones have run.
- **Only before the app is deployed**, you can reset by deleting `club/migrations/0*.py` (keep `__init__.py`) and `db.sqlite3`, then running `makemigrations` and `migrate`. This wipes all data.
- Once real data exists, never delete migrations. Use `squashmigrations` to tidy up, and never hand-edit one that has already been applied.

### `null=True` vs `blank=True`

- `blank=True` means a **form** can leave the field empty.
- `null=True` means the **database** can store NULL.
- **Text fields** use only `blank=True`, and "empty" is stored as `''`. Django avoids NULL for text so there's only one empty value to check for.
- **Number fields** can't hold `''`, and `0` would mean something different. So an optional number like `capacity` needs **both**, and "no capacity" is stored as NULL (`None` in Python).

### `on_delete` options

Using the example of deleting a class that has 8 attendance rows:

| Option | What happens |
| --- | --- |
| `CASCADE` | The class **and** its 8 attendance rows are deleted |
| `PROTECT` | Nothing is deleted. Django raises `ProtectedError` |
| `SET_NULL` | The class is deleted. The rows stay, with an empty link (needs `null=True`) |

We use `CASCADE` because attendance means nothing without its class. Use `PROTECT` when deleting would lose something important, such as a member who has payment records. Deactivate them instead, which is why `Member` has an `active` field.

### `related_name`

The `ForeignKey` lives on `Attendance`, so going **forwards** is automatic: `row.fencing_class`, `row.member`. `related_name` names the link going **backwards**:

```python
junior.attendance.all()                              # every row for a class
alex.attendance.all()                                # every row for a member
junior.attendance.filter(status='present').count()   # headcount for the calendar
```

Without `related_name`, Django would call it `attendance_set`.

---

# Lesson 3: The Django admin

**Goal:** a working back office in the browser, with no screens to build yourself.

## Step 1: Create an admin login

```bash
python manage.py createsuperuser
python manage.py runserver
```

Log in at http://localhost:8000/admin/.

## Step 2: Register and customise the models

`club/admin.py`:

```python
from django.contrib import admin

from .models import Attendance, FencingClass, Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'weapon', 'email', 'phone', 'active']
    list_filter = ['weapon', 'active']
    search_fields = ['name', 'email']


class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0
    autocomplete_fields = ['member']


@admin.register(FencingClass)
class FencingClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'start', 'end', 'coach', 'capacity', 'present_count']
    list_filter = ['coach']
    search_fields = ['name', 'coach']
    date_hierarchy = 'start'
    inlines = [AttendanceInline]

    @admin.display(description='Present')
    def present_count(self, obj):
        return obj.attendance.filter(status='present').count()


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['member', 'fencing_class', 'status']
    list_filter = ['status']
    list_editable = ['status']
    autocomplete_fields = ['member', 'fencing_class']
```

| Option | What it adds |
| --- | --- |
| `@admin.register(Model)` | Shows the model in the admin, with these settings |
| `list_display` | Columns in the list. Can include methods, like `present_count` |
| `list_filter` | A filter sidebar |
| `search_fields` | A search box |
| `date_hierarchy` | Year, month and day links above the list |
| `list_editable` | Edit these fields directly in the list |
| `inlines` | Edit related rows on the parent's page |
| `autocomplete_fields` | A search box instead of a long dropdown. The linked model's admin must have `search_fields` |

`runserver` reloads when you save a file, so just refresh the browser.

## What `admin.py` does

`admin.py` is the **only** place that connects your models to the built-in admin site. When Django starts, it runs every app's `admin.py`, and your registrations say **which** models to show and **how**. It doesn't store data or change tables. Delete it and your data is untouched; only the admin pages disappear.

How a request reaches the admin:

```
Browser  GET /admin/club/member/
   → config/urls.py      "/admin/ → the admin site"
   → Django admin        "Member is registered, so use MemberAdmin"
   → club/models.py      Member.objects.all() reads from db.sqlite3
   → Django admin        Builds an HTML page using list_display, list_filter…
   → Browser
```

## What an inline does

An **inline** lets you edit related rows **on the same page** as the thing they belong to.

- **Without one:** add each attendance row separately, choosing the class every time.
- **With `AttendanceInline`:** open a class and see a table of all its members and statuses. Django fills in the class from the page, and one **Save** saves everything.

```
Change fencing class
──────────────────────────────────
Name:      Junior Foil
Start:     Tue 21 Oct, 17:00
...
Attendances
┌──────────────┬───────────┬────────┐
│ Member       │ Status    │ Delete │
├──────────────┼───────────┼────────┤
│ Alex Tan     │ Present ▾ │   ☐    │
│ Sam Lee      │ Absent  ▾ │   ☐    │
└──────────────┴───────────┴────────┘
+ Add another Attendance
```

Django knows which rows belong to the class because of the `ForeignKey`. `TabularInline` shows compact rows, while `StackedInline` shows a full form per row. The calendar's side panel in Lesson 5 is the same idea.

## Practice

1. Add 6+ members across all weapons, with one inactive.
2. Create 4 classes this week, one with no capacity.
3. Enrol members, and mark some Present, Absent or Excused.
4. Delete a class, and check its attendance rows are gone.

**Challenges:**

1. Add a per-member "classes attended" column.
2. Make `active` editable in the member list.
3. Make the inline offer only active members. **Hint:** `formfield_for_foreignkey`.

---

# Lesson 4: The API

**Goal:** URLs that return and accept JSON, for React to call.

## Key ideas

An **API** is a set of URLs for programs. It returns **JSON** instead of HTML.

| Method | Meaning | Calendar action |
| --- | --- | --- |
| `GET` | Read | Load this week's classes |
| `POST` | Create | Add a class |
| `PATCH` | Update **only the fields sent** | Drag a class (send `start` and `end`) |
| `PUT` | Replace the **whole** row | Not used |
| `DELETE` | Delete | Delete a class |

**Django REST Framework (DRF):**

| Tool | File | Job |
| --- | --- | --- |
| **Serializer** | `serializers.py` | Converts model objects to JSON, and incoming JSON to validated data that can be saved |
| **ViewSet** | `views.py` | Handles list, get one, create, update and delete |
| **Router** | `urls.py` | Generates the URLs |

**The API:**

| URL | Methods | Used for |
| --- | --- | --- |
| `/api/classes/?start=…&end=…` | GET, POST | Load a week, create a class |
| `/api/classes/<id>/` | GET, PATCH, DELETE | Drag, edit, delete |
| `/api/attendance/?fencing_class=<id>` | GET, POST | The side panel list, add a member |
| `/api/attendance/<id>/` | PATCH, DELETE | Change status, remove |
| `/api/members/` | GET, POST | The member list |

## Step 1: Install DRF

```bash
pip install djangorestframework
pip freeze > requirements.txt
```

In `config/settings.py`, add `'rest_framework',` to `INSTALLED_APPS` above `'club'`, and add this at the bottom:

```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAdminUser',
    ],
}
```

This makes every API URL manager-only: only users who can log in to the admin can use it.

## Step 2: Serializers

`club/serializers.py`:

```python
from rest_framework import serializers

from .models import Attendance, FencingClass, Member


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['id', 'name', 'email', 'phone', 'weapon', 'active']


class FencingClassSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    present_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = FencingClass
        fields = [
            'id', 'name', 'start', 'end', 'coach', 'capacity', 'notes',
            'member_count', 'present_count',
        ]

    def validate(self, data):
        start = data.get('start', getattr(self.instance, 'start', None))
        end = data.get('end', getattr(self.instance, 'end', None))
        if end <= start:
            raise serializers.ValidationError({'end': 'End must be after start.'})
        return data


class AttendanceSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)

    class Meta:
        model = Attendance
        fields = ['id', 'fencing_class', 'member', 'member_name', 'status']
```

- **`ModelSerializer`** builds the fields from the model. `fields` picks which ones are included.
- **`read_only=True`** fields are sent out, but never accepted in.
- **`validate`** is where rules involving several fields go. The `getattr(self.instance, ...)` handles a PATCH that sends only `end` (resizing a class), by falling back to the existing `start`.
- **`source='member.name'`** follows the link, so React gets the name without a second request.
- **Duplicates:** DRF reads the `UniqueConstraint` and returns a clean 400 error instead of crashing.

## Step 3: ViewSets

`club/views.py`:

```python
from django.db.models import Count, Q
from rest_framework import viewsets

from .models import Attendance, FencingClass, Member
from .serializers import AttendanceSerializer, FencingClassSerializer, MemberSerializer


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.order_by('name')
    serializer_class = MemberSerializer


class FencingClassViewSet(viewsets.ModelViewSet):
    serializer_class = FencingClassSerializer

    def get_queryset(self):
        queryset = FencingClass.objects.annotate(
            member_count=Count('attendance'),
            present_count=Count('attendance', filter=Q(attendance__status='present')),
        )
        start = self.request.query_params.get('start')
        end = self.request.query_params.get('end')
        if start and end:
            queryset = queryset.filter(start__lt=end, end__gt=start)
        return queryset


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        queryset = Attendance.objects.select_related('member').order_by('member__name')
        fencing_class = self.request.query_params.get('fencing_class')
        if fencing_class:
            queryset = queryset.filter(fencing_class=fencing_class)
        return queryset
```

- **`ModelViewSet`** gives you list, get one, create, update and delete. You supply the rows and the serializer.
- **`get_queryset`** is used when the rows depend on the request, such as the `?start=` and `?end=` parameters.
- **`__`** in a lookup means "follow the link, then use this field". `__lt` and `__gt` mean less than and greater than.

## Step 4: URLs

`club/urls.py`:

```python
from rest_framework.routers import DefaultRouter

from .views import AttendanceViewSet, FencingClassViewSet, MemberViewSet

router = DefaultRouter()
router.register('members', MemberViewSet, basename='member')
router.register('classes', FencingClassViewSet, basename='class')
router.register('attendance', AttendanceViewSet, basename='attendance')

urlpatterns = router.urls
```

`config/urls.py`:

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('club.urls')),
]
```

The router creates a **list** URL (`/api/classes/`) and a **single-row** URL (`/api/classes/<id>/`) for each ViewSet. The request flow is now: `config/urls.py → club/urls.py → club/views.py → club/models.py → JSON`.

## Step 5: Try it in the browsable API

1. Log in at http://localhost:8000/admin/ first.
2. Open http://localhost:8000/api/ and click **classes**.
3. Filter by week: `/api/classes/?start=2026-10-19T00:00:00%2B08:00&end=2026-10-26T00:00:00%2B08:00`. `%2B` is `+` in a URL.
4. **Drag a class by hand:** open `/api/classes/2/`. In the form at the bottom, click **Raw data**, clear the box, enter the following and click **PATCH**:
   ```json
   {"start": "2026-10-22T18:00:00+08:00", "end": "2026-10-22T19:30:00+08:00"}
   ```
5. **Break a rule:** PATCH `{"end": "2026-10-22T17:00:00+08:00"}`. You should get a 400 error, *End must be after start*.
6. **Take attendance:** open `/api/attendance/?fencing_class=2`, note a row's `id`, go to `/api/attendance/<id>/`, and PATCH `{"status": "present"}`.
7. **Security:** in a private window, `/api/classes/` returns 403.

**Troubleshooting:**

- **There's no link to click on a row.** The serializers return `id` numbers, not URLs. Type `/api/attendance/<id>/` yourself.
- **There's only a POST button.** You're on a **list** page (title "… List"), which allows only GET and POST. PATCH, PUT and DELETE are on a **single-row** page (title "… Instance"). The `Allow:` line near the top of each page lists the allowed methods.
- **`JSON parse error`.** The Raw data box isn't valid JSON. Text values need **double** quotes (`"present"`), and curly quotes won't work. Clear the box and type only the fields you're changing.

## Concepts

### The overlap filter: `start__lt=end, end__gt=start`

```
                   Week shown on calendar
                 |◄────────────────────────►|
A  ███                                         ✗ ends before the week starts
B           ██████████                         ✓ starts before, ends inside
C                      ████                    ✓ fully inside
D                                     ██████████  ✓ starts inside, ends after
E                                                 ███ ✗ starts after the week ends
```

"Starts within the week" would miss **B**, such as a Sunday-night camp running past midnight. Two ranges **overlap** when each starts before the other ends:

- `start__lt=end` (the class starts before the week ends) rules out E.
- `end__gt=start` (the class ends after the week starts) rules out A.

### The N+1 query problem

Loading 20 classes and then counting each one's attendance separately is **1 + 20 = 21 queries**. Both of these fix it by getting everything in **one** query:

- **`annotate(Count(...))`** counts in the database, in the same query.
- **`select_related('member')`** joins each attendance row's member in the same query.

The admin's `present_count` method has the N+1 problem (one query per row). That's fine there, but not for a calendar.

---

# Lesson 5: The React calendar

**Goal:** a calendar where the manager sees the week, drags classes to reschedule them, and clicks a class to take attendance.

## The big picture

```
Browser: http://localhost:5173
   │
Vite dev server (5173): serves React code, and proxies /api/... to Django
   │
Django (8000): /api/classes/ → views → database
```

- **Vite** serves the React code and reloads the page on save.
- **The proxy** passes `/api/...` requests to Django, so the browser sees one address.
- **Login:** log in through the Django admin at `localhost:8000`. Browsers share cookies between ports on the same host, so `localhost:5173` is logged in too.

## Step 1: Node

Vite needs **Node 20.19+ or 22.12+**.

```bash
which node
node -v
```

**Troubleshooting Node:**

- **`styleText` error or `v18`:** an old Node is being used. Check `which -a node` for more than one install. An old nodejs.org install lives in `/usr/local/bin`, and Homebrew's in `/opt/homebrew/bin`.
- **Homebrew:** `brew upgrade node`, then `brew link --overwrite node`, then `hash -r`.
- **`Command Line Tools does not support macOS`:** update them in System Settings → Software Update. Or run `sudo rm -rf /Library/Developer/CommandLineTools` then `sudo xcode-select --install`, and retry `brew upgrade node`.
- **No Homebrew needed:** install the LTS `.pkg` from https://nodejs.org/en/download.
- **`Uncaught SyntaxError` after typing a shell command:** you're inside Node's own prompt (`>`). Press Ctrl+D to leave it. Plain `node` opens the prompt; `node -v` prints the version.

## Step 2: Create the React app

From the **project root**:

```bash
cd /Users/jorellesee/Projects/fencing_club_app
npm create vite@latest frontend -- --template react
cd frontend
npm install
```

Delete `src/assets/` and `src/index.css`, and remove `import './index.css'` from `src/main.jsx`.

| File | What it is |
| --- | --- |
| `package.json` | Like `requirements.txt`: packages, plus commands like `npm run dev` |
| `node_modules/` | Installed packages, like `.venv` (not in git) |
| `index.html` | The one HTML page. React fills `<div id="root">` |
| `src/main.jsx` | The starting point. It renders `<App />` |
| `vite.config.js` | Vite settings, including the proxy |

## Step 3: Install FullCalendar

From **`frontend/`**:

```bash
npm install @fullcalendar/react temporal-polyfill
```

FullCalendar **7** puts everything in `@fullcalendar/react`, with extras on sub-paths like `@fullcalendar/react/timegrid`. Most tutorials show **v6** packages (`@fullcalendar/core`, `@fullcalendar/timegrid`). Don't install those.

## Step 4: Connect Vite to Django

`frontend/vite.config.js`:

```js
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

Add this at the bottom of `backend/config/settings.py`:

```python
CSRF_TRUSTED_ORIGINS = ['http://localhost:5173']
```

**CSRF (Cross-Site Request Forgery)** is an attack where another website makes your browser send requests to your app using your login cookie. Django blocks it in two ways:

1. **A token:** requests that change data must send the `csrftoken` cookie's value in an `X-CSRFToken` header. Other sites can't read your cookies.
2. **An origin check:** Django only accepts requests from pages it trusts. `CSRF_TRUSTED_ORIGINS` adds the React page. Without it, every drag fails with *"Origin checking failed"*.

## Step 5: The API helper

`frontend/src/api.js`:

```js
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[2]) : ''
}

export async function api(path, { method = 'GET', body } = {}) {
  const response = await fetch(`/api/${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) {
    throw new Error(`${method} /api/${path} failed (${response.status}): ${await response.text()}`)
  }
  return response.status === 204 ? null : response.json()
}
```

- **`fetch`** is the browser's built-in way to send HTTP requests.
- **`JSON.stringify`** turns an object into JSON text.
- **`response.ok`** is false for 400 and 403 errors, which become JavaScript errors carrying Django's message.
- **`204`** is DRF's "deleted, nothing to return".

## Step 6: The calendar

`frontend/src/App.jsx`:

```jsx
import { useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import classicThemePlugin from '@fullcalendar/react/themes/classic'
import timeGridPlugin from '@fullcalendar/react/timegrid'
import interactionPlugin from '@fullcalendar/react/interaction'
import '@fullcalendar/react/skeleton.css'
import '@fullcalendar/react/themes/classic/theme.css'
import '@fullcalendar/react/themes/classic/palette.css'
import { api } from './api'
import AttendancePanel from './AttendancePanel'
import './App.css'

function toEvent(fencingClass) {
  const limit = fencingClass.capacity ?? fencingClass.member_count
  return {
    id: String(fencingClass.id),
    title: `${fencingClass.name} (${fencingClass.present_count}/${limit})`,
    start: fencingClass.start,
    end: fencingClass.end,
  }
}

export default function App() {
  const calendarRef = useRef(null)
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState('')

  function refresh() {
    calendarRef.current.getApi().refetchEvents()
  }

  async function loadClasses(info) {
    const params = new URLSearchParams({
      start: info.start.toISOString(),
      end: info.end.toISOString(),
    })
    try {
      const classes = await api(`classes/?${params}`)
      setError('')
      return classes.map(toEvent)
    } catch (err) {
      setError(err.message)
      return []
    }
  }

  async function saveTimes(info) {
    try {
      await api(`classes/${info.event.id}/`, {
        method: 'PATCH',
        body: {
          start: info.event.start.toISOString(),
          end: info.event.end.toISOString(),
        },
      })
    } catch (err) {
      setError(err.message)
      info.revert()
    }
  }

  async function createClass(info) {
    calendarRef.current.getApi().unselect()
    const name = window.prompt('Class name')
    if (!name) return
    try {
      await api('classes/', {
        method: 'POST',
        body: { name, start: info.start.toISOString(), end: info.end.toISOString() },
      })
      refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="layout">
      <main className="calendar">
        {error && <p className="error">{error}</p>}
        <FullCalendar
          ref={calendarRef}
          plugins={[classicThemePlugin, timeGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          headerToolbar={{
            start: 'prev,next today',
            center: 'title',
            end: 'timeGridWeek,timeGridDay',
          }}
          height="100%"
          events={loadClasses}
          editable
          selectable
          eventDrop={saveTimes}
          eventResize={saveTimes}
          select={createClass}
          eventClick={(info) => setSelectedId(info.event.id)}
        />
      </main>
      {selectedId && (
        <AttendancePanel
          key={selectedId}
          classId={selectedId}
          onChange={refresh}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  )
}
```

| Option | When it runs | What it does |
| --- | --- | --- |
| `events={loadClasses}` | The visible week changes | GET `/api/classes/?start=…&end=…` |
| `editable` | | Allows dragging and resizing |
| `eventDrop` and `eventResize` | After a drag or resize | PATCH `start` and `end` |
| `selectable` + `select` | After dragging across empty time | POST a new class |
| `eventClick` | Clicking a class | Opens the side panel |

- **`useState`** holds values that cause a redraw when they change.
- **`useRef`** keeps a handle on the calendar, so it can call `refetchEvents()`.
- **`toEvent`** converts the API's shape to FullCalendar's: a serializer on the frontend side. `??` means "if capacity is empty, use the member count instead".
- **`info.revert()`** moves the class back if Django rejects the change.
- **`toISOString()`** sends UTC times. Django stores UTC and shows Singapore time.

## Step 7: The attendance panel

`frontend/src/AttendancePanel.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { api } from './api'

const STATUSES = ['enrolled', 'present', 'absent', 'excused']

function formatTime(iso) {
  return new Date(iso).toLocaleString([], {
    weekday: 'short', hour: '2-digit', minute: '2-digit',
  })
}

export default function AttendancePanel({ classId, onChange, onClose }) {
  const [fencingClass, setFencingClass] = useState(null)
  const [rows, setRows] = useState([])
  const [members, setMembers] = useState([])

  async function load() {
    const [classData, attendance, allMembers] = await Promise.all([
      api(`classes/${classId}/`),
      api(`attendance/?fencing_class=${classId}`),
      api('members/'),
    ])
    setFencingClass(classData)
    setRows(attendance)
    setMembers(allMembers)
  }

  useEffect(() => {
    load()
  }, [classId])

  async function setStatus(row, status) {
    await api(`attendance/${row.id}/`, { method: 'PATCH', body: { status } })
    await load()
    onChange()
  }

  async function addMember(memberId) {
    await api('attendance/', {
      method: 'POST',
      body: { fencing_class: classId, member: memberId, status: 'enrolled' },
    })
    await load()
    onChange()
  }

  async function removeRow(row) {
    await api(`attendance/${row.id}/`, { method: 'DELETE' })
    await load()
    onChange()
  }

  async function deleteClass() {
    if (!window.confirm(`Delete ${fencingClass.name}?`)) return
    await api(`classes/${classId}/`, { method: 'DELETE' })
    onChange()
    onClose()
  }

  if (!fencingClass) return <aside className="panel">Loading…</aside>

  const available = members.filter(
    (member) => member.active && !rows.some((row) => row.member === member.id),
  )

  return (
    <aside className="panel">
      <button className="close" onClick={onClose}>×</button>
      <h2>{fencingClass.name}</h2>
      <p className="meta">
        {formatTime(fencingClass.start)} – {formatTime(fencingClass.end)}
        {fencingClass.coach && ` · ${fencingClass.coach}`}
      </p>

      <h3>Attendance ({fencingClass.present_count} present)</h3>
      <ul className="attendance">
        {rows.map((row) => (
          <li key={row.id}>
            <span>{row.member_name}</span>
            <select value={row.status} onChange={(e) => setStatus(row, e.target.value)}>
              {STATUSES.map((status) => (
                <option key={status} value={status}>{status}</option>
              ))}
            </select>
            <button onClick={() => removeRow(row)}>Remove</button>
          </li>
        ))}
      </ul>

      <select value="" onChange={(e) => addMember(e.target.value)}>
        <option value="">Add a member…</option>
        {available.map((member) => (
          <option key={member.id} value={member.id}>{member.name}</option>
        ))}
      </select>

      <button className="danger" onClick={deleteClass}>Delete class</button>
    </aside>
  )
}
```

- **Props** (`classId`, `onChange`, `onClose`) pass data and callbacks down from `App`.
- **`useEffect(..., [classId])`** loads the data when the panel appears.
- **`Promise.all`** sends the three requests at the same time.
- **Every action** follows the same pattern: call the API, then `load()`, then `onChange()`. The screen always matches the database.
- **`available`** lists active members who aren't in the class yet.
- **`key={selectedId}`**, in `App.jsx`, gives a fresh panel for each class.

## Step 8: Layout styles

`frontend/src/App.css`:

```css
body {
  margin: 0;
  font-family: system-ui, sans-serif;
}

.layout {
  display: flex;
  height: 100vh;
}

.calendar {
  flex: 1;
  min-width: 0;
  padding: 16px;
}

.error {
  color: #b00020;
}

.panel {
  width: 320px;
  padding: 16px;
  border-left: 1px solid #ddd;
  overflow-y: auto;
}

.panel .close {
  float: right;
}

.panel .meta {
  color: #666;
}

.attendance {
  padding: 0;
  list-style: none;
}

.attendance li {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.attendance li span {
  flex: 1;
}

.danger {
  display: block;
  margin-top: 24px;
  color: #b00020;
}
```

## Step 9: Run it

**Terminal 1:**

```bash
cd /Users/jorellesee/Projects/fencing_club_app/backend
source .venv/bin/activate
python manage.py runserver
```

**Terminal 2:**

```bash
cd /Users/jorellesee/Projects/fencing_club_app/frontend
npm run dev
```

1. Log in at **http://localhost:8000/admin/**. Use `localhost`, **not** `127.0.0.1`, because cookies belong to a host name.
2. Open **http://localhost:5173**.

**Try it:** drag a class, resize one, click one, change statuses, add and remove members, drag across empty time to create a class, and stop Django then drag (the class should jump back).

**Troubleshooting:**

- **Red "failed (403)" message:** you're not logged in on `localhost:8000`.
- **Blank page:** a JavaScript error. Open the browser console (Cmd+Option+J) and check the `npm run dev` terminal. A common cause is FullCalendar not being installed in `frontend/`. Run `npm install @fullcalendar/react temporal-polyfill` from `frontend/`, then `npm run dev -- --force` to clear Vite's cache.
- **`package.json` or `node_modules` in the project root:** `npm install` was run from the wrong folder. Delete them and install from `frontend/`.

---

# Lesson 6: Automated tests

**Goal:** one command that proves the app still works.

```bash
python manage.py test        # add -v 2 to list each test
```

## How Django tests work

- Every method in `club/tests.py` named `test_…` is one test.
- Django creates a **separate, empty test database**, so your real data is never touched.
- Each test starts fresh, and `setUp` runs before **every** test.
- Each test follows three steps: **arrange** the data, **act**, then **assert** the result.
- `APITestCase` gives `self.client`, which sends requests without a running server. `force_login(user)` logs it in.
- `refresh_from_db()` re-reads a row, to check what was actually saved.

## The tests

`backend/club/tests.py`:

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APITestCase

from .models import Attendance, FencingClass, Member

SGT = ZoneInfo('Asia/Singapore')


def at(day, hour):
    """A Singapore time in the week of Mon 19 Oct 2026."""
    return datetime(2026, 10, day, hour, tzinfo=SGT)


class ModelTests(TestCase):
    def setUp(self):
        self.alex = Member.objects.create(name='Alex Tan')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18)
        )

    def test_member_can_only_appear_once_per_class(self):
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='present')
        with self.assertRaises(IntegrityError):
            Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='absent')

    def test_deleting_class_deletes_its_attendance(self):
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='present')
        self.junior.delete()
        self.assertEqual(Attendance.objects.count(), 0)


class ClassApiTests(APITestCase):
    def setUp(self):
        manager = User.objects.create_user('manager', is_staff=True)
        self.client.force_login(manager)
        self.alex = Member.objects.create(name='Alex Tan')
        self.sam = Member.objects.create(name='Sam Lee')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18), capacity=12
        )

    def test_logged_out_users_are_refused(self):
        self.client.logout()
        response = self.client.get('/api/classes/')
        self.assertEqual(response.status_code, 403)

    def test_non_managers_are_refused(self):
        coach = User.objects.create_user('coach')
        self.client.force_login(coach)
        response = self.client.get('/api/classes/')
        self.assertEqual(response.status_code, 403)

    def test_week_filter_returns_overlapping_classes(self):
        FencingClass.objects.create(name='Last week', start=at(12, 17), end=at(12, 18))
        FencingClass.objects.create(name='Overnight camp', start=at(18, 22), end=at(19, 2))
        week = {'start': at(19, 0).isoformat(), 'end': at(26, 0).isoformat()}

        response = self.client.get('/api/classes/', week)

        names = sorted(c['name'] for c in response.json())
        self.assertEqual(names, ['Junior Foil', 'Overnight camp'])

    def test_class_includes_headcounts(self):
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='present')
        Attendance.objects.create(fencing_class=self.junior, member=self.sam, status='absent')

        response = self.client.get(f'/api/classes/{self.junior.id}/')

        self.assertEqual(response.json()['member_count'], 2)
        self.assertEqual(response.json()['present_count'], 1)

    def test_dragging_a_class_saves_new_times(self):
        new_times = {'start': at(22, 18).isoformat(), 'end': at(22, 19).isoformat()}

        response = self.client.patch(f'/api/classes/{self.junior.id}/', new_times)

        self.assertEqual(response.status_code, 200)
        self.junior.refresh_from_db()
        self.assertEqual(self.junior.start, at(22, 18))
        self.assertEqual(self.junior.end, at(22, 19))

    def test_class_cannot_end_before_it_starts(self):
        response = self.client.patch(
            f'/api/classes/{self.junior.id}/', {'end': at(20, 16).isoformat()}
        )

        self.assertEqual(response.status_code, 400)
        self.junior.refresh_from_db()
        self.assertEqual(self.junior.end, at(20, 18))


class AttendanceApiTests(APITestCase):
    def setUp(self):
        manager = User.objects.create_user('manager', is_staff=True)
        self.client.force_login(manager)
        self.alex = Member.objects.create(name='Alex Tan')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18)
        )

    def test_adding_a_member_to_a_class(self):
        response = self.client.post('/api/attendance/', {
            'fencing_class': self.junior.id, 'member': self.alex.id, 'status': 'enrolled',
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['member_name'], 'Alex Tan')

    def test_adding_the_same_member_twice_is_refused(self):
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='enrolled')

        response = self.client.post('/api/attendance/', {
            'fencing_class': self.junior.id, 'member': self.alex.id, 'status': 'enrolled',
        })

        self.assertEqual(response.status_code, 400)

    def test_marking_a_member_present(self):
        row = Attendance.objects.create(
            fencing_class=self.junior, member=self.alex, status='enrolled'
        )

        response = self.client.patch(f'/api/attendance/{row.id}/', {'status': 'present'})

        self.assertEqual(response.status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.status, 'present')
```

| Test | Protects |
| --- | --- |
| `test_member_can_only_appear_once_per_class` | The `UniqueConstraint` |
| `test_deleting_class_deletes_its_attendance` | `on_delete=CASCADE` |
| `test_logged_out_users_are_refused`, `test_non_managers_are_refused` | `IsAdminUser` |
| `test_week_filter_returns_overlapping_classes` | The overlap filter |
| `test_class_includes_headcounts` | `annotate(Count(...))` |
| `test_dragging_a_class_saves_new_times` | The PATCH a drag sends |
| `test_class_cannot_end_before_it_starts` | The serializer's `validate` |
| `test_adding_the_same_member_twice_is_refused` | A clean 400 error, not a crash |

| Status code | Meaning |
| --- | --- |
| 200 | OK |
| 201 | Created |
| 204 | Deleted |
| 400 | Bad data (React reverts the change) |
| 403 | Not allowed |

## Break something on purpose

A test you've never seen fail might not be testing anything. Change the filter in `views.py` to `start__gte=start, start__lt=end` and run the tests:

```
FAIL: test_week_filter_returns_overlapping_classes
AssertionError: Lists differ: ['Junior Foil'] != ['Junior Foil', 'Overnight camp']
```

Change it back. Then try deleting `validate` from the serializer, see which test fails, and undo.

## Habits

- Run `python manage.py test` before every commit.
- Add a test with every new feature.
- Before committing, check that `git status` shows no `.venv`, `node_modules` or `db.sqlite3`.

**Challenges:**

1. Deleting a class through the API returns 204, and its attendance is gone.
2. The member list is sorted by name.
3. `/api/attendance/?fencing_class=<id>` returns only that class's rows.

---

# Lesson 7: Recurring classes

**Goal:** set up "Junior Foil, every Tuesday until December" once, instead of creating each week by hand.

## The design

| Approach | How it works | Problem for us |
| --- | --- | --- |
| **Virtual:** store one rule, and FullCalendar draws the repeats | One row, drawn many times | No row per week, so **nowhere to store attendance** |
| **Materialized:** create a real row for every week | 10 weeks = 10 `FencingClass` rows | None. Each week is a normal class |

We materialize. Every copy is an ordinary class, so dragging, attendance, headcounts and tests all keep working, and moving one week (say, a public holiday) moves only that week. Copies share a **`series`** ID.

**What's added:**

1. A `series` field on `FencingClass`.
2. `POST /api/classes/<id>/repeat/` with `{"until": "2026-12-15"}`, which creates weekly copies, **including the roster** (statuses reset to *enrolled*).
3. `POST /api/classes/<id>/delete-following/`, which deletes this class and all later ones in its series.
4. Repeat and delete controls in the side panel.

## Step 1: The `series` field

In `club/models.py`, add this to `FencingClass` after `notes`:

```python
    series = models.UUIDField(null=True, blank=True, db_index=True)
```

```bash
python manage.py makemigrations
python manage.py migrate
```

- **A UUID** is a random, practically unique ID. Every class in a series shares one.
- **`null=True`**: one-off classes have no series. Existing rows get NULL, so no default is needed.
- **`db_index=True`** makes "find every class in this series" fast.

## Step 2: Serializers

In `FencingClassSerializer`:

```python
    class Meta:
        model = FencingClass
        fields = [
            'id', 'name', 'start', 'end', 'coach', 'capacity', 'notes',
            'member_count', 'present_count', 'series',
        ]
        read_only_fields = ['series']
```

At the bottom of `serializers.py`:

```python
class RepeatSerializer(serializers.Serializer):
    until = serializers.DateField()
```

- **`read_only_fields`**: React can see the series, but only the repeat action sets it.
- **A plain `Serializer`** isn't tied to a table. It just validates the request: `until` must be a valid date, or DRF returns a 400 error.

## Step 3: The two actions

Imports at the top of `club/views.py`:

```python
import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Attendance, FencingClass, Member
from .serializers import (
    AttendanceSerializer, FencingClassSerializer, MemberSerializer, RepeatSerializer,
)
```

Inside `FencingClassViewSet`, below `get_queryset`:

```python
    @action(detail=True, methods=['post'])
    def repeat(self, request, pk=None):
        fencing_class = self.get_object()
        serializer = RepeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        until = serializer.validated_data['until']

        if until > timezone.localdate(fencing_class.start) + timedelta(days=366):
            raise ValidationError({'until': 'Repeat for at most one year.'})
        if fencing_class.series and FencingClass.objects.filter(
            series=fencing_class.series, start__gt=fencing_class.start
        ).exists():
            raise ValidationError({'detail': 'Repeat from the last class in the series.'})

        roster = list(fencing_class.attendance.values_list('member_id', flat=True))
        created = 0
        with transaction.atomic():
            if fencing_class.series is None:
                fencing_class.series = uuid.uuid4()
                fencing_class.save(update_fields=['series'])
            week = 1
            while timezone.localdate(fencing_class.start + timedelta(weeks=week)) <= until:
                copy = FencingClass.objects.create(
                    name=fencing_class.name,
                    start=fencing_class.start + timedelta(weeks=week),
                    end=fencing_class.end + timedelta(weeks=week),
                    coach=fencing_class.coach,
                    capacity=fencing_class.capacity,
                    notes=fencing_class.notes,
                    series=fencing_class.series,
                )
                Attendance.objects.bulk_create([
                    Attendance(fencing_class=copy, member_id=member_id, status='enrolled')
                    for member_id in roster
                ])
                created += 1
                week += 1
        return Response({'created': created}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='delete-following')
    def delete_following(self, request, pk=None):
        fencing_class = self.get_object()
        if fencing_class.series is None:
            raise ValidationError({'detail': 'This class is not part of a series.'})
        following = FencingClass.objects.filter(
            series=fencing_class.series, start__gte=fencing_class.start
        )
        count = following.count()
        following.delete()
        return Response({'deleted': count})
```

- **`@action`** adds your own endpoint to a ViewSet.
  - `detail=True` puts it on one class: `/api/classes/<id>/repeat/`.
  - `url_path` sets the URL, since Python names can't contain `-`.
  - The router picks it up automatically, so `urls.py` doesn't change.
- **`self.get_object()`** loads the class from the URL, returning a 404 if it's missing. It also enforces permissions.
- **Safety rules:**
  - **At most one year:** a typo like `2062` would otherwise create about 1,800 classes.
  - **Only from the last class in a series:** repeating from the middle would create duplicate weeks.
- **`values_list('member_id', flat=True)`** gets just the ids, like `[1, 4, 7]`.
- **`timezone.localdate(...)`** converts stored UTC to a Singapore date before comparing. A 7am Singapore class is 11pm the previous day in UTC. Singapore has no daylight saving, so "+7 days" keeps the same time of day.
- **`bulk_create`** inserts all of a copy's attendance in one query.
- **`transaction.atomic()`** means all of it succeeds or none of it does: no half-made series if something fails partway.
- **`delete_following`** deletes this class and all later ones in the series, and CASCADE removes their attendance.

## Step 4: Tests

Added to `club/tests.py`:

```python
class RepeatTests(APITestCase):
    def setUp(self):
        manager = User.objects.create_user('manager', is_staff=True)
        self.client.force_login(manager)
        self.alex = Member.objects.create(name='Alex Tan')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18), coach='Coach Lim'
        )
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='present')

    def repeat(self, fencing_class, until):
        return self.client.post(f'/api/classes/{fencing_class.id}/repeat/', {'until': until})

    def test_repeat_creates_weekly_copies_until_the_date(self):
        response = self.repeat(self.junior, '2026-11-10')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['created'], 3)
        starts = list(FencingClass.objects.values_list('start', flat=True))
        self.assertEqual(starts, [at(20, 17) + timedelta(weeks=n) for n in range(4)])

    def test_copies_share_a_series_and_details(self):
        self.repeat(self.junior, '2026-11-03')

        self.junior.refresh_from_db()
        copies = FencingClass.objects.exclude(id=self.junior.id)
        self.assertIsNotNone(self.junior.series)
        for copy in copies:
            self.assertEqual(copy.series, self.junior.series)
            self.assertEqual(copy.coach, 'Coach Lim')

    def test_copies_enrol_the_same_members(self):
        self.repeat(self.junior, '2026-10-27')

        copy = FencingClass.objects.get(start=at(27, 17))
        self.assertEqual(list(copy.attendance.values_list('member', 'status')),
                         [(self.alex.id, 'enrolled')])

    def test_repeat_is_limited_to_one_year(self):
        response = self.repeat(self.junior, '2028-01-01')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(FencingClass.objects.count(), 1)

    def test_repeat_only_from_the_last_class_in_a_series(self):
        self.repeat(self.junior, '2026-11-03')

        response = self.repeat(self.junior, '2026-12-01')

        self.assertEqual(response.status_code, 400)

    def test_delete_following_keeps_earlier_classes(self):
        self.repeat(self.junior, '2026-11-10')
        second = FencingClass.objects.get(start=at(27, 17))

        response = self.client.post(f'/api/classes/{second.id}/delete-following/')

        self.assertEqual(response.json()['deleted'], 3)
        self.assertEqual(list(FencingClass.objects.all()), [self.junior])
```

Running `python manage.py test` gives 17 tests, all passing. `self.repeat(...)` is a **helper**: it doesn't start with `test_`, so it isn't run as a test, but every test can use it.

## Step 5: The side panel

In `frontend/src/AttendancePanel.jsx`, add new state:

```jsx
  const [until, setUntil] = useState('')
  const [message, setMessage] = useState('')
```

Add new functions above `if (!fencingClass) return …`:

```jsx
  async function repeatWeekly(event) {
    event.preventDefault()
    try {
      const result = await api(`classes/${classId}/repeat/`, {
        method: 'POST',
        body: { until },
      })
      setMessage(`Added ${result.created} more classes.`)
      await load()
      onChange()
    } catch (err) {
      setMessage(err.message)
    }
  }

  async function deleteFollowing() {
    if (!window.confirm(`Delete this and all later ${fencingClass.name} classes?`)) return
    await api(`classes/${classId}/delete-following/`, { method: 'POST' })
    onChange()
    onClose()
  }
```

Replace the single `Delete class` button with:

```jsx
      <h3>Repeat weekly</h3>
      {fencingClass.series && <p className="meta">Part of a weekly series.</p>}
      <form className="repeat" onSubmit={repeatWeekly}>
        <label>
          Until <input type="date" value={until} onChange={(e) => setUntil(e.target.value)} required />
        </label>
        <button>Repeat</button>
      </form>
      {message && <p className="meta">{message}</p>}

      <button className="danger" onClick={deleteClass}>Delete class</button>
      {fencingClass.series && (
        <button className="danger" onClick={deleteFollowing}>Delete this and following</button>
      )}
```

Add to `App.css`:

```css
.repeat {
  display: flex;
  gap: 8px;
  align-items: center;
}
```

- **`onSubmit` + `event.preventDefault()`**: React handles the form instead of the browser reloading the page.
- **`<input type="date">`** gives a date picker, and its value is in Django's `2026-12-15` format.
- **A controlled input** (`value` + `onChange`): React state always holds what's typed.
- **`{fencingClass.series && …}`** shows the series controls only for classes in a series.
- **`try/catch`** shows Django's error message in the panel.

## Try it

1. Click a class with members, pick a date about 4 weeks ahead, and click **Repeat**. You should see "Added 4 more classes."
2. Click **next**. The copies appear, with the same members enrolled.
3. Drag one copy. Only that week moves.
4. Try repeating the first class. You'll get an error: it's not the last in the series.
5. On week 3, click **Delete this and following**. Weeks 1 and 2 remain.

## Limits of this design

- **Editing a series:** changing one class changes only that week. "Edit all following" would be a similar `@action` using `.update()`.
- **Holidays:** use "Delete class" on that week.
- **Moving the whole series**, say Tuesdays to Wednesdays: delete the following classes, move the remaining one, then repeat again.

---

# Lesson 8: List view and filters

**Goal:** three new ways to look at the same classes:

1. A **list view**: the month's classes as a plain list instead of a grid.
2. A **coach filter**: show only one coach's classes.
3. A **member filter**: show only the classes one fencer is on the roster for.

## The design

All three are **views of the same `classes/` endpoint**. Nothing new is stored, so there are no model changes and no migrations.

| View | Where the work happens |
| --- | --- |
| List | Only in React. FullCalendar has a built-in list view, fed by the same `loadClasses` |
| Per coach | Django filters by `?coach=Coach Lim` |
| Per member | Django filters by `?member=3` |

Filtering in Django rather than in React means the browser only downloads the classes it shows. It's the same pattern as the `?start=&end=` week filter from Lesson 4.

**What's added:**

1. `?coach=` and `?member=` filters on `GET /api/classes/`.
2. `GET /api/classes/coaches/`, which returns every coach name once, for the dropdown.
3. Tests for both.
4. A **list** button and two dropdowns on the calendar.

## Step 1: The filters

In `club/views.py`, in `FencingClassViewSet.get_queryset`, add two filters after the week filter, just before `return queryset`:

```python
        coach = self.request.query_params.get('coach')
        if coach:
            queryset = queryset.filter(coach=coach)
        member = self.request.query_params.get('member')
        if member:
            queryset = queryset.filter(attendance__member=member)
        return queryset
```

- **`query_params.get(...)`** returns `None` when the parameter is missing, so with no filter you still get every class.
- **`attendance__member=member`** follows the link from a class to its attendance rows to their member: "classes that have an attendance row for this member". The double underscore crosses a relationship, like `attendance__status` in the `present_count` annotation.
- **Filters chain.** `?coach=Coach Lim&member=3` gives Coach Lim's classes that member 3 attends. Each `.filter()` narrows the result further.

## Step 2: The coaches endpoint

Coach is a plain text field on each class, not its own table, so there's no `/api/coaches/` list. Build one from the classes. Add this action to `FencingClassViewSet`, next to `repeat`:

```python
    @action(detail=False)
    def coaches(self, request):
        names = (
            FencingClass.objects.exclude(coach='')
            .order_by('coach')
            .values_list('coach', flat=True)
            .distinct()
        )
        return Response(list(names))
```

Open http://localhost:8000/api/classes/coaches/ to see the list.

- **`detail=False`** makes this a list-level action: `/api/classes/coaches/` rather than `/api/classes/5/coaches/`. `repeat` is `detail=True` because it acts on one class.
- **`exclude(coach='')`** skips classes with no coach.
- **`values_list('coach', flat=True)`** fetches only the coach column, as a flat list of strings, instead of whole `FencingClass` objects.
- **`.distinct()`** removes duplicates: 30 weekly classes by Coach Lim become one "Coach Lim".
- **Why `order_by('coach')` is required:** the model's `Meta.ordering = ['start']` would otherwise add `start` to the query. Django would then treat each (coach, start) pair as distinct, and every name would appear once per class. Ordering by `coach` replaces the default ordering.

## Step 3: Tests

Add to the bottom of `club/tests.py`:

```python
class FilterTests(APITestCase):
    def setUp(self):
        manager = User.objects.create_user('manager', is_staff=True)
        self.client.force_login(manager)
        self.alex = Member.objects.create(name='Alex Tan')
        self.sam = Member.objects.create(name='Sam Lee')
        self.junior = FencingClass.objects.create(
            name='Junior Foil', start=at(20, 17), end=at(20, 18), coach='Coach Lim'
        )
        self.senior = FencingClass.objects.create(
            name='Senior Epee', start=at(21, 19), end=at(21, 21), coach='Coach Wong'
        )
        FencingClass.objects.create(
            name='Open Bouting', start=at(22, 19), end=at(22, 21), coach='Coach Lim'
        )
        Attendance.objects.create(fencing_class=self.junior, member=self.alex, status='present')
        Attendance.objects.create(fencing_class=self.junior, member=self.sam, status='enrolled')
        Attendance.objects.create(fencing_class=self.senior, member=self.sam, status='present')

    def names(self, response):
        return [c['name'] for c in response.data]

    def test_coach_filter(self):
        response = self.client.get('/api/classes/', {'coach': 'Coach Lim'})
        self.assertEqual(self.names(response), ['Junior Foil', 'Open Bouting'])

    def test_member_filter(self):
        response = self.client.get('/api/classes/', {'member': self.sam.id})
        self.assertEqual(self.names(response), ['Junior Foil', 'Senior Epee'])

    def test_member_filter_keeps_whole_class_counts(self):
        response = self.client.get('/api/classes/', {'member': self.alex.id})
        junior = response.data[0]
        self.assertEqual(junior['member_count'], 2)
        self.assertEqual(junior['present_count'], 1)

    def test_coaches_lists_each_name_once(self):
        response = self.client.get('/api/classes/coaches/')
        self.assertEqual(response.data, ['Coach Lim', 'Coach Wong'])
```

Running `python manage.py test` gives 21 tests, all passing.

- **`self.client.get(url, {...})`** turns the dict into a query string: `?coach=Coach+Lim`.
- **Why test the counts?** Filtering on `attendance__member` joins the attendance table a second time. If that join leaked into `Count('attendance')`, Junior Foil would show 1 member (only Alex's row) instead of 2. The test proves the headcount is still for the whole class. It holds because the unique constraint allows only one row per member per class.
- **Break it on purpose:** remove `.order_by('coach')` from `coaches` and run the tests. `test_coaches_lists_each_name_once` fails with "Coach Lim" twice. Put it back.

## Step 4: The list view

In `frontend/src/App.jsx`, import the list plugin with the others:

```jsx
import listPlugin from '@fullcalendar/react/list'
```

Add it to `plugins`, and add a `listMonth` button to the toolbar:

```jsx
          plugins={[classicThemePlugin, timeGridPlugin, listPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          headerToolbar={{
            start: 'prev,next today',
            center: 'title',
            end: 'timeGridWeek,timeGridDay,listMonth',
          }}
```

- **A plugin** adds views or features to FullCalendar. `listPlugin` adds `listDay`, `listWeek`, `listMonth` and `listYear`.
- **No backend change:** the list view calls the same `loadClasses` with the month's `start` and `end`. Clicking a row opens the side panel, as on the grid.

## Step 5: The filter dropdowns

Still in `App.jsx`, change the React import to include `useEffect`:

```jsx
import { useEffect, useRef, useState } from 'react'
```

Add state and loading under `const [error, setError] = useState('')`:

```jsx
  const [coaches, setCoaches] = useState([])
  const [members, setMembers] = useState([])
  const [coach, setCoach] = useState('')
  const [member, setMember] = useState('')

  useEffect(() => {
    api('classes/coaches/').then(setCoaches)
    api('members/').then(setMembers)
  }, [])
```

In `loadClasses`, add the filters to the query string, after `const params = …`:

```jsx
    if (coach) params.set('coach', coach)
    if (member) params.set('member', member)
```

In the JSX, add the dropdowns under the error message, and wrap `<FullCalendar … />` in a `calendar-body` div:

```jsx
        {error && <p className="error">{error}</p>}
        <div className="filters">
          <select value={coach} onChange={(e) => setCoach(e.target.value)}>
            <option value="">All coaches</option>
            {coaches.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
          <select value={member} onChange={(e) => setMember(e.target.value)}>
            <option value="">All members</option>
            {members.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </div>
        <div className="calendar-body">
          <FullCalendar
            …everything as before…
          />
        </div>
```

In `App.css`, replace the `.calendar` rule and add two new ones:

```css
.calendar {
  flex: 1;
  min-width: 0;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.calendar-body {
  flex: 1;
  min-height: 0;
}

.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
```

- **`useEffect(…, [])`** runs once, when the page first loads. The empty `[]` means "don't re-run when anything changes".
- **`.then(setCoaches)`**: when the request finishes, its JSON (an array of names) goes straight into state.
- **`""` means "all".** `if (coach)` skips empty strings, so "All coaches" sends no filter.
- **How a filter change refetches:** choosing a coach calls `setCoach`, React re-renders `App`, and `loadClasses` is created again, holding the new `coach`. FullCalendar sees a different `events` function and refetches with it. You don't need to call `refresh()`.
- **Why the `calendar-body` wrapper?** `height="100%"` makes FullCalendar as tall as its parent. Without the wrapper it would be as tall as `.calendar` *plus* the dropdowns, and the page would scroll. As a flex column, `.calendar` gives the dropdowns their natural height and `calendar-body` (`flex: 1`) the rest.

## Try it

1. Give a few classes a coach in the admin (http://localhost:8000/admin/), then reload the React page.
2. Pick a coach. Only their classes stay, in week view and in **list**.
3. Pick a member as well. Only that coach's classes with that member on the roster stay. The headcount still shows the whole class.
4. Click a row in list view. The side panel opens.
5. Set both back to "All".

## Limits of this design

- **The coach list is loaded once.** A coach added in the admin appears in the dropdown after a page reload.
- **With a member filter on, a new class disappears** as soon as you create it, because it has no members yet. Add members with the filter set to "All members".
- **Coach is free text,** so "Coach Lim" and "coach lim" count as two coaches. A `Coach` model with a `ForeignKey`, like `Member`, would fix that. It's a natural next lesson.

---

# Lesson 9: Member profiles, "Needs marking", and a Notion-style redesign

**Goal:** two new pages a manager uses every week, plus a sidebar to move between pages. Claude built this one; read through the files below to learn from it.

## What was added

| Where | What |
| --- | --- |
| `club/views.py` | `MemberViewSet` annotates `present_count`, `marked_count`, `last_present`. `AttendanceViewSet` takes `?member=` and has an `unmarked` action |
| `club/serializers.py` | Members return those three stats. Attendance rows also return `class_name` and `class_start` |
| `club/tests.py` | `MemberStatsTests` and `UnmarkedTests` (25 tests in total) |
| `main.jsx`, `App.jsx` | React Router, the sidebar, and one `<Route>` per page |
| `CalendarPage.jsx` | The old `App.jsx` calendar, moved into its own page |
| `UnmarkedPage.jsx` | Past classes with members still *enrolled*, grouped by class |
| `MembersPage.jsx`, `MemberPage.jsx` | A members table, and one member's profile with their class history |
| `StatusSelect.jsx`, `format.js` | Shared pieces: the coloured status dropdown and date/rate helpers |
| `App.css` | Notion-style colours, typography, tables, tags and dark mode |

## Key ideas

### Aggregating across a relationship

```python
Member.objects.annotate(
    present_count=Count('attendance', filter=Q(attendance__status='present')),
    marked_count=Count('attendance', filter=Q(attendance__status__in=['present', 'absent'])),
    last_present=Max('attendance__fencing_class__start', filter=Q(attendance__status='present')),
)
```

- **`Count(..., filter=Q(...))`** counts only the matching rows, in one query for every member at once.
- **`Max('attendance__fencing_class__start')`** walks member → attendance → class and takes the latest start.
- **Attendance rate = present ÷ (present + absent).** Excused classes and ones not yet marked don't count against anyone. The division happens in React (`attendanceRate` in `format.js`), because Django already supplies both numbers.

### "Unmarked" is just a filter

```python
status='enrolled', fencing_class__end__lt=timezone.now()
```

"Still enrolled after the class ended" means nobody took the register. It's sorted by class start, then class, so each class's rows sit together and React can group them in one pass (`groupByClass`).

### Avoiding N+1 again

The attendance serializer now reads `fencing_class.name`, so `get_queryset` uses `select_related('member', 'fencing_class')`. Without it, each row would run its own query for its class.

### Routing

- **`<BrowserRouter>`** in `main.jsx` lets the URL decide which page shows.
- **`<Routes>` / `<Route path="/members/:id">`** maps URLs to pages. **`useParams()`** reads `:id` inside `MemberPage`.
- **`<NavLink>`** is a link that adds the `active` class when you're on its page. The sidebar uses it for highlighting.
- **The sidebar badge** reloads its count whenever the URL changes, and pages call `onChange` after marking someone.

### Styling with CSS variables

All colours are variables on `:root` (`--text`, `--border`, `--tag-green-bg`, …), redefined inside `@media (prefers-color-scheme: dark)`. FullCalendar's theme is also driven by variables (`--fc-classic-*`), so setting those to ours makes the calendar match, in both light and dark. The FullCalendar CSS is imported in `main.jsx` before `App.css`, so our values win.

## Try it

1. Make sure you're logged in at http://localhost:8000/admin/, then open http://localhost:5173.
2. **Needs marking** shows a red count if any past class still has *enrolled* members. Mark one present; it disappears and the count drops. Try **Mark all present**.
3. **Members** shows each fencer's attendance bar. Click a name.
4. On the profile, change a status in the history. The rate updates.
5. Click a name in the calendar's side panel. It opens that member's profile.
6. Switch macOS to dark mode. The whole app follows.

---

# Lesson 10: Logins for managers, coaches and members

**Goal:** the app was manager-only. Now coaches and members log in too, and each role sees and changes only what it should. Claude built this one; read through the files below to learn from it.

## Who can do what

| | Manager | Coach | Member |
| --- | --- | --- | --- |
| **Who they are** | A staff user (*Staff status* ticked) | A login with a coach profile | A login with a member profile |
| **Calendar** | Every class. Drag, create, delete, repeat | Every class, read-only | Only classes they're on |
| **Mark attendance** | Any class | Only classes they coach | No |
| **Class notes** | Edit any | Edit their own classes' notes | Read |
| **Needs marking** | Every class | Their own classes | Hidden |
| **Members** | Everyone, editable in the admin | Everyone, read-only | Only their own profile ("My attendance") |

## What was added

| Where | What |
| --- | --- |
| `club/models.py` | `Profile`: a one-to-one link from a login to a role, plus the `Member` or coach name it belongs to |
| `club/permissions.py` | `role_of(user)` and `RoleAccess`, the permission class every API view now uses |
| `config/settings.py` | `DEFAULT_PERMISSION_CLASSES` changed from `IsAdminUser` to `club.permissions.RoleAccess` |
| `club/views.py` | Each viewset says what coaches and members may do. Querysets shrink for members. New `me`, `login_view`, `logout_view` |
| `club/urls.py` | `/api/me/`, `/api/login/`, `/api/logout/` |
| `club/admin.py` | The *Users* page gets a *Profile* section, and a *Role* column |
| `club/serializers.py` | Attendance rows also return the class's `coach` |
| `club/tests.py` | `CoachTests`, `MemberRoleTests`, `AccountTests` (44 tests in total) |
| `auth.js` | `MeContext`, `useMe()` and `canEdit(me, coach)` |
| `LoginPage.jsx` | The login form |
| `App.jsx` | Asks `/api/me/` who's logged in; shows the login page or a sidebar for that role, with *Log out* |
| `CalendarPage.jsx`, `AttendancePanel.jsx`, `MemberPage.jsx`, `StatusSelect.jsx` | Hide or lock what the role can't change. The panel now shows class notes |

## Key ideas

### Managers are just staff

Managers need the Django admin to create logins, and the admin only lets in staff. So "manager" means `is_staff`, and the existing superuser is a manager without any changes. Only coaches and members get a `Profile`:

```python
def role_of(user):
    if not user.is_authenticated:
        return None
    if user.is_staff:
        return MANAGER
    profile = getattr(user, 'profile', None)
    return profile.role if profile else None
```

A login with neither is refused everywhere, the same as being logged out.

### `OneToOneField`

`Profile.user` and `Profile.member` are one-to-one: each login has at most one profile, and each member at most one login. Django gives you `user.profile` and `member.profile` in both directions, and lookups can walk them: `Member.objects.filter(profile__user=request.user)` means "the member whose profile belongs to this login".

`Profile.clean()` makes sure a member profile picks a member and a coach profile has a coach name. The admin calls `clean()` before saving, so a manager can't save a half-filled profile.

### Two layers: what you can see, what you can change

**Seeing** is done in `get_queryset`. For a member, the classes list is filtered to their own:

```python
if role_of(self.request.user) == MEMBER:
    queryset = queryset.filter(attendance__member__profile__user=self.request.user)
```

Asking for someone else's member page then gives **404**, as if it doesn't exist, rather than 403. That way it doesn't reveal which IDs are real.

**Changing** is done by the permission class. Each viewset lists what the other roles may do:

```python
class AttendanceViewSet(viewsets.ModelViewSet):
    role_actions = {
        COACH: {'list', 'retrieve', 'partial_update', 'unmarked'},
        MEMBER: {'list', 'retrieve'},
    }
    role_fields = {COACH: {'status'}}

    def can_edit(self, user, row):
        return row.fencing_class.coach == user.profile.coach_name
```

`RoleAccess` checks these in two steps:

- **`has_permission`** runs before anything is loaded. It refuses an action that isn't listed (a coach's `destroy`), and a change touching fields that aren't listed (a coach's PATCH that includes `fencing_class`).
- **`has_object_permission`** runs once DRF has fetched the row, when a view calls `get_object()`. It calls the viewset's `can_edit`, so a coach can only change rows in their own classes.

`partial_update` is DRF's name for PATCH. Leaving `update` (PUT) out of the list means coaches can only send the fields they're changing.

### Hiding buttons is not security

React hides the drag handles, delete buttons and dropdowns a role can't use. That's only for comfort: anyone can send requests by hand. The backend checks every request, and the tests prove it. `canEdit` in `auth.js` mirrors the backend rule so the screen matches what will actually be allowed.

### Logging in from React

Before, you logged in at `/admin/`, which only lets in staff. Now:

1. `App` calls **`GET /api/me/`**. It returns who's logged in, or `null`. It's decorated with `@ensure_csrf_cookie`, so the browser has a `csrftoken` cookie before anyone logs in.
2. The login form **`POST`s `/api/login/`**. Django's `authenticate()` checks the password and `login()` starts the session. The session cookie then rides along on every request, as before.
3. **Log out** `POST`s `/api/logout/`.

These three are plain Django views, not DRF ones. DRF switches off Django's CSRF check for logged-out requests, which would let another site log you in to an account of its choosing. Plain views keep `CsrfViewMiddleware` checking the login form too.

### React context

Almost every page needs to know who's logged in. Instead of passing `me` down through every component, `App` wraps everything in `<MeContext.Provider value={me}>`, and any component can call `useMe()`.

### Coaches are matched by name

`FencingClass.coach` is still free text, so a coach profile stores a `coach_name` that must match it exactly. "Coach Lim" and "coach lim" are different people. The `Coach` model in *What's next* would fix this with a real link.

## Try it

1. Run `python manage.py migrate` (adds the profile table), then start both servers.
2. In the admin, open **Users → Add user**. Make `lim` with a password and save. In the **Profile** section pick *Coach*, type a coach name exactly as it appears on some classes, and save again.
3. Add another user, pick *Member* and choose a member.
4. Open http://localhost:5173 in a private window and log in as the coach. Drag a class: it won't move. Open one of their classes: statuses and notes can be changed. Open another coach's class: everything is read-only. **Needs marking** lists only their classes.
5. Log in as the member. They see **My classes** and **My attendance**, nothing else.
6. Try going to `/members` as the member: there's no page. Try `http://localhost:5173/api/members/` directly: **403**.

---

# Lesson 11: A calendar and a table for every role

**Goal:** every role gets the same two views of classes, a **calendar** and a **table**, each showing the classes that role cares about. Classes also get a **location**. Claude built this one; read through the files below to learn from it.

## What each role sees now

This replaces the table in Lesson 10.

| | Manager | Coach | Member |
| --- | --- | --- | --- |
| **Sidebar** | Calendar, All classes, Needs marking, Members | My calendar, My classes | My calendar, My classes |
| **Which classes** | Every class, filtered by coach, member and/or location | Only the classes they coach | Only the classes they're on |
| **Table's last column** | Present / capacity | Present / capacity | Their own status |
| **Click a class** | Full side panel | Mark attendance, edit notes | Read-only details |

Both views show past and upcoming classes. The table splits them into **Upcoming** (soonest first) and **Past** (most recent first).

## What was added

| Where | What |
| --- | --- |
| `club/models.py` + migration `0006` | `FencingClass.location`, a text field like `coach` |
| `club/views.py` | `?location=` filter, a `locations` action listing each location once, and `repeat` copies the location |
| `club/admin.py`, `club/serializers.py` | Location shown, filterable and searchable in the admin, and returned by the API |
| `club/tests.py` | Location filter, combined filters, `locations`, repeat copies location (47 tests) |
| `classes.js` | `classParams(me, filters)`: the classes query for a role. Also `NO_FILTERS` and `attendanceCount` |
| `ClassFilters.jsx` | The coach / member / location dropdowns and a *Clear* button, taken out of `CalendarPage` |
| `ClassesTablePage.jsx` | The table view, with the same side panel as the calendar |
| `App.jsx` | Holds the filters, so they stay put when you switch views. Builds each role's sidebar and routes |
| `CalendarPage.jsx`, `AttendancePanel.jsx` | Use the shared filters. The panel shows the location and only links names for managers |

## Key ideas

### Two views, one query

The calendar and the table ask the same question: "which classes should this person see?" Both get the answer from one function:

```js
export function classParams(me, filters) {
  const params = new URLSearchParams()
  if (me.role === 'manager') {
    for (const [key, value] of Object.entries(filters)) {
      if (value) params.set(key, value)
    }
  } else if (me.role === 'coach') {
    params.set('coach', me.coach_name)
  }
  return params
}
```

The calendar then adds `start` and `end` for the visible week. The table leaves them off, so it gets every class.

Filters combine with AND, because each one is another `.filter()` on the same queryset: `?location=Hall A&member=3` means classes in Hall A *that* member 3 is on.

### Lifting state up

Filters used to live inside `CalendarPage`. Now both pages need them, and switching pages unmounts the old one, which would throw its state away. So the state moves up to their common parent, `Layout` in `App.jsx`, and goes down as props (`filters`, `onFiltersChange`). This is React's standard answer to "two components need the same state".

### Whose job is "only my classes"?

- **Members:** the backend. Lesson 10's `get_queryset` already returns only their classes, whatever React asks for.
- **Coaches:** React, by sending `?coach=` with their own name. The API still lets a coach read other classes, which is what we chose: this is about what's useful to show, not about secrets. Changing other coaches' classes is still refused by the backend.

### A member's own status

The classes API returns counts, not one person's status. So the member's table makes a second request, for `attendance/?member=<their id>`, and turns the rows into a lookup: `{ classId: status }`. Both requests run at the same time with `Promise.all`.

## Try it

1. Run `python manage.py migrate` (adds the location column). In the admin, give a few classes a location.
2. As a manager, open **All classes**. Pick a location, then a member: both filters apply. Switch to **Calendar**: the same filters are still set. Click **Clear**.
3. Click a row in the table. The side panel opens, as on the calendar.
4. Log in as a coach. The sidebar has just **My calendar** and **My classes**, showing only their classes.
5. Log in as a member. **My classes** shows their status for each class.

---

# Lesson 12: Creating classes and members in the app

**Goal:** managers stop needing the Django admin for day-to-day work. A **New class** form replaces the old `window.prompt`, and a **New member** form goes on the Members page. Claude built this one; read through the files below to learn from it.

## What was added

| Where | What |
| --- | --- |
| `club/tests.py` | Creating a class with every detail, creating a member, a member needs a name, coaches can't create members (51 tests) |
| `api.js` | Failed requests now carry the parsed JSON body as `error.data` |
| `Modal.jsx` | A centred dialog. Closes on Escape, on *Cancel*, or a click outside |
| `FormErrors.jsx` | Shows the API's validation errors field by field |
| `ClassForm.jsx` | Name, date, start and end time, coach, location, capacity, notes |
| `MemberForm.jsx` | Name, email, phone, weapon, active |
| `CalendarPage.jsx`, `ClassesTablePage.jsx` | A **+ New class** button. On the calendar, dragging across empty time opens the form with those times filled in. After saving, the new class's side panel opens so you can add members straight away |
| `MembersPage.jsx` | A **+ New member** button |

No backend code changed: `ModelViewSet` has always accepted `POST`, and Lesson 10's permissions already limit it to managers.

## Key ideas

### Controlled forms

Each input's value comes from one `form` state object, and every keystroke updates it:

```js
const [form, setForm] = useState({ name: '', email: '', ... })

function set(key) {
  return (event) => setForm({ ...form, [key]: event.target.value })
}

<input value={form.name} onChange={set('name')} />
```

`set('name')` returns a change handler for that one field. `{ ...form, [key]: value }` copies the object with one field replaced, because React state should be replaced, not changed in place.

### Dates, times and time zones

The form shows a separate date and start/end times, because that's how people think about classes. On submit they're joined and converted:

```js
new Date(`${form.date}T${form.startTime}`).toISOString()
```

`new Date('2026-10-27T18:00')` is read as **local** time (Singapore), and `toISOString()` turns it into UTC for Django. Going the other way, `toDateInput` and `toTimeInput` in `format.js` build the input values from local time. Using `toISOString().slice(...)` there would show the UTC date, which is the previous day for early-morning classes.

### Letting the server validate

The form only does basic browser checks (`required`, `type="email"`, `min="1"`). The real rules, such as "end must be after start" or a valid weapon choice, live in the serializer. When one fails, DRF replies **400** with JSON like:

```json
{ "end": ["End must be after start."] }
```

`api.js` attaches that to the error, and `FormErrors` shows each field's message. One set of rules, in one place, also applies to anything else that uses the API.

### Why the test sends JSON

`test_creating_a_member` uses `format='json'`. Sent as form data instead, a missing `active` would mean **False**: in an HTML form an unticked checkbox sends nothing, so DRF treats "missing" as unticked. React sends JSON, where a missing field falls back to the model's default (`True`). The test sends what the app actually sends.

### `<datalist>`

The coach and location fields are free text, but `<input list="coach-options">` plus a `<datalist>` suggests names already in use. That cuts down on near-duplicates like "Coach Lim" and "Coach  Lim", which matter because coaches are matched by name.

## Try it

1. As a manager, open **Calendar** and click **+ New class**. It suggests the next full hour. Fill it in and create it: the side panel opens on the new class. Add a member.
2. Drag across an empty slot. The form opens with those times.
3. Set the end time before the start. The form shows *"end: End must be after start."*
4. Open **All classes** and create one from there.
5. Open **Members**, click **+ New member**, and add someone. They appear in the table.

---

# Lesson 13: Putting it online with Render

**Goal:** run the app on the internet. One Render **web service** runs Django, which also serves the built React app, and a **persistent disk** keeps the SQLite database between deploys. Claude made the code changes; you do the Render setup.

## What was added

| Where | What |
| --- | --- |
| `requirements.txt` | `gunicorn` (a production web server) and `whitenoise` (serves static files from Django) |
| `config/settings.py` | Debug, secret key, allowed hosts and database path now come from environment variables. Local development needs none of them |
| `config/urls.py` | `react_app`: every URL that isn't `/api/`, `/admin/` or `/static/` returns React's `index.html` |
| `.gitignore` | `staticfiles/`, the output of `collectstatic` |

## Key ideas

### One codebase, two environments

Settings read **environment variables**, values set outside the code:

```python
DEBUG = os.environ.get('DJANGO_DEBUG', 'true').lower() == 'true'
```

On your Mac none are set, so you get the development defaults. On Render you set `DJANGO_DEBUG=false` and a real secret key. When debug is off and `DJANGO_SECRET_KEY` is missing, `os.environ['DJANGO_SECRET_KEY']` crashes on purpose. Starting with a key that's published in git would let anyone forge login cookies.

### Why development and production serve React differently

| | Development | Production |
| --- | --- | --- |
| React | Vite dev server on :5173, reloading as you edit | `npm run build` writes plain files to `frontend/dist/` |
| Django | `runserver` on :8000 | `gunicorn`, on Render's `$PORT` |
| Same address via | Vite's proxy sends `/api` to Django | Django serves the React files itself |

Either way the browser sees **one address**, so the session cookie and CSRF token work with no extra setup.

- **WhiteNoise** serves `frontend/dist/assets/...` (via `WHITENOISE_ROOT`) and the admin's CSS (via `collectstatic` into `staticfiles/`).
- **The catch-all route** returns `index.html` for `/table`, `/members/3` and so on. Without it, reloading any page except `/` gives Django's 404, because only React Router knows those URLs.

### Why `migrate` runs at start, not at build

Render builds your app on a separate machine, without the disk attached. The disk, and so the database, only exists once the service starts. So the build command makes files (`npm run build`, `collectstatic`), and the start command runs `migrate` before starting gunicorn.

### HTTPS settings

Render handles HTTPS and passes requests to gunicorn as plain HTTP, with an `X-Forwarded-Proto: https` header. `SECURE_PROXY_SSL_HEADER` tells Django to trust that header. `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` stop the browser from ever sending those cookies over plain HTTP.

## Set it up on Render

1. Push your work to GitHub.
2. In Render: **New → Web Service**, connect the `fencing-club-app` repo. Pick a **paid instance type**, because disks need one.

    | Field | Value |
    | --- | --- |
    | Language | Python 3 |
    | Root Directory | *(leave blank)* |
    | Build Command | `pip install -r backend/requirements.txt && cd frontend && npm ci && npm run build && cd ../backend && python manage.py collectstatic --noinput` |
    | Start Command | `cd backend && python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` |

3. **Environment variables:**

    | Key | Value |
    | --- | --- |
    | `DJANGO_DEBUG` | `false` |
    | `DJANGO_SECRET_KEY` | A long random string (Render's **Generate** button, or the command below) |
    | `SQLITE_PATH` | `/var/data/db.sqlite3` |
    | `PYTHON_VERSION` | `3.12.10` |
    | `NODE_VERSION` | `24` |

    To make a key yourself: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

4. **Advanced → Add Disk:** mount path `/var/data`, 1 GB is plenty.
5. Create the service and watch the logs. When it's live, open its **Shell** tab and run `cd backend && python manage.py createsuperuser`.
6. Open `https://<your-service>.onrender.com`, log in, and add members, classes and logins as before.

You don't set `RENDER_EXTERNAL_HOSTNAME`: Render provides it, and the settings add it to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

## Rehearse it locally

You can run the production setup on your Mac before deploying:

```bash
cd frontend && npm run build && cd ../backend
export DJANGO_DEBUG=false DJANGO_SECRET_KEY=any-long-test-string RENDER_EXTERNAL_HOSTNAME=localhost
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8123
```

Open http://localhost:8123. Pages and the admin should load. Logging in won't work, because secure cookies need HTTPS. Afterwards, close that terminal (or `unset` the variables), and delete `frontend/dist` and `backend/staticfiles`.

## Limits

- **Backups are up to you.** Render keeps the disk, but download a copy of `db.sqlite3` now and then (for example with `scp` or from the Shell).
- **Deploys cause a short outage.** A service with a disk can't run two copies at once, so the old one stops before the new one starts.
- **No email yet**, so there's no "forgot password". A manager resets passwords in the admin.

---

# Lesson 14: Editing classes, and names that write themselves

**Goal:** managers can edit a class from the app, including renaming it, and a **Generate** button names a class from its details, e.g. *Monday Sabre BT Class*. Classes also get a **weapon**. Claude built this one; read through the files below to learn from it.

## What was added

| Where | What |
| --- | --- |
| `club/models.py` + migration `0007` | `FencingClass.weapon`: Foil, Épée, Sabre or Mixed (optional) |
| `club/views.py` | `?weapon=` filter, `repeat` copies the weapon, and a new `update-following` action |
| `club/admin.py`, `club/serializers.py` | Weapon shown and filterable in the admin, and returned by the API |
| `club/tests.py` | Weapon filter, `update-following` only touches this and later classes and never times, and it validates (54 tests) |
| `classes.js` | `locationCode()` and `generateName()` |
| `ClassForm.jsx` | Now edits as well as creates. Adds Weapon, the **Generate** button, and the series checkbox |
| `AttendancePanel.jsx` | An **Edit class** button for managers. Shows the weapon |
| `ClassFilters.jsx`, `ClassesTablePage.jsx` | A weapon filter and a Weapon column |

## Key ideas

### How a name is generated

```js
export function generateName({ date, weapon, location }) {
  const weekday = new Date(`${date}T00:00`).toLocaleDateString('en-US', { weekday: 'long' })
  return [weekday, CLASS_WEAPONS[weapon], location && locationCode(location), 'Class']
    .filter(Boolean)
    .join(' ')
}
```

- **Weekday** comes from the date in the form, read as local time.
- **Location code** is the initials of a multi-word location ("Bukit Timah" → "BT", "Hall A" → "HA"). A one-word location stays whole ("Clementi").
- **`.filter(Boolean)`** drops anything not filled in, so a class with no weapon becomes *Tuesday Clementi Class*.

The button only fills in the Name box. You can still edit it, or type a name of your own. The name is saved like any other text, so changing the weapon later doesn't rename the class unless you click Generate again.

### One form for create and edit

`ClassForm` checks whether it was given a `fencingClass`:

- **No class:** empty form, `POST /api/classes/`, button says *Create class*.
- **A class:** form filled from it, `PATCH /api/classes/<id>/`, button says *Save*.

`useState(() => initialForm(...))` passes a *function*, so the starting values are worked out once, when the form opens, not on every keystroke.

### Changing a whole series

Each week of a series is its own row (Lesson 7). The new action changes this class and every later one in its series:

```python
following = FencingClass.objects.filter(series=fencing_class.series, start__gte=fencing_class.start)
following.update(**serializer.validated_data)
```

- **Only some fields are copied** (`SERIES_FIELDS`): name, coach, location, weapon, capacity. Times would need shifting week by week, and notes are usually about one session, so both stay per class. Anything else in the request is simply ignored.
- **The serializer still validates** the data with `partial=True`, so a bad weapon gives a 400 before anything changes.
- **`.update()`** changes every matching row in one SQL query, without loading them into Python.

In the form, the checkbox only appears for classes in a series. Saving first PATCHes this class with everything, including times and notes. If the box is ticked, it then calls `update-following` with the shared fields.

## Try it

1. Run `python manage.py migrate`.
2. As a manager, click a class, then **Edit class**. Change the name and click **Save**. The calendar and table update.
3. Set the weapon and location and click **Generate**. You get something like *Monday Sabre BT Class*. Change a word and save.
4. Open a class in a weekly series, rename it, tick **Also change … all following classes**, and save. Later weeks are renamed; earlier ones aren't.
5. In **All classes**, filter by weapon.

---

# Lesson 15: Putting it online for free with PythonAnywhere

**Goal:** run the app on the internet at no cost. Render's disks need a paid plan, and without a disk Render wipes `db.sqlite3` on every deploy. On PythonAnywhere's free tier your files are permanent, so SQLite stays where it is. Django still serves the built React app through WhiteNoise, as in Lesson 13. You make one small settings change, then set everything up on PythonAnywhere.

## Key ideas

### What's different from Render

| | Render (Lesson 13) | PythonAnywhere |
| --- | --- | --- |
| Database | SQLite on a paid disk | SQLite in your home folder, which is permanent |
| Building React | Render runs `npm run build` | You build on your Mac and upload `dist/` |
| Environment variables | Render's form | You set them in the WSGI file, and in the virtualenv for the console |
| Web server | gunicorn, started by your start command | PythonAnywhere's server imports `application` from the WSGI file |
| Deploying | Push to GitHub | `git pull` in a console, then **Reload** |

### The WSGI file is the entry point

A WSGI server doesn't run `manage.py`. It imports one Python file and looks for a variable called `application`, which is what your [config/wsgi.py](backend/config/wsgi.py) provides. PythonAnywhere keeps its own WSGI file outside your repo (in `/var/www/`), which makes it a safe place for the secret key: it never goes into git.

### The console needs the same settings

`manage.py` commands you type in a console don't go through the WSGI file. If you run `collectstatic` without `DJANGO_DEBUG=false`, it runs with development settings, and you can end up with a different set of static files from the one the live site expects. To avoid that, you set the same variables in the virtualenv's `postactivate` script, which runs every time you type `workon fencing`.

### Free tier limits

- Your address is `https://<username>.pythonanywhere.com`. Custom domains need a paid plan.
- **Every 3 months, log in and click "Run until 3 months from today"** on the Web tab, or the site gets switched off.
- Outbound internet is limited to an allowlist. GitHub and PyPI are on it, so `git` and `pip` work.

## Step 1: make the allowed host configurable

Right now [settings.py](backend/config/settings.py) only adds the site's address when `RENDER_EXTERNAL_HOSTNAME` is set, and PythonAnywhere doesn't set it. Change the block so it reads a variable of your own, `SITE_HOST`, and falls back to Render's:

```python
# The app's public address, e.g. jorellesee.pythonanywhere.com.
# Render sets RENDER_EXTERNAL_HOSTNAME itself; elsewhere, set SITE_HOST.
SITE_HOST = os.environ.get('SITE_HOST') or os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if SITE_HOST:
    ALLOWED_HOSTS.append(SITE_HOST)
    CSRF_TRUSTED_ORIGINS.append(f'https://{SITE_HOST}')
```

Why both settings?
- `ALLOWED_HOSTS`: Django rejects requests whose `Host` header isn't in this list, so nobody can point another domain at your app.
- `CSRF_TRUSTED_ORIGINS`: Django rejects unsafe requests (`POST`, `PATCH`, `DELETE`) from origins it doesn't trust, and the origin includes `https://`.

Run the tests, then commit and push everything, including migration `0007`:

```bash
cd backend && python manage.py test
cd .. && git add -A && git commit -m "Lesson 14 and configurable site host" && git push
```

## Step 2: build React on your Mac

```bash
cd frontend && npm run build
zip -r dist.zip dist
```

`dist/` is in `frontend/.gitignore`, so it doesn't reach PythonAnywhere through git. You upload it instead.

## Step 3: get the code onto PythonAnywhere

1. Sign up at [pythonanywhere.com](https://www.pythonanywhere.com) (a free "Beginner" account). Your username becomes your web address.
2. Open **Consoles → Bash**:

    ```bash
    git clone https://github.com/jorellesee/fencing-club-app.git
    mkvirtualenv fencing --python=python3.10
    cd ~/fencing-club-app/backend
    pip install -r requirements.txt
    ```

    If the repo is private, GitHub asks for a password. Use a [personal access token](https://github.com/settings/tokens) (read-only access to this repo), not your GitHub password. Python 3.10 matches your Mac. If PythonAnywhere doesn't offer it, use `python3.12`; Django 5.2 supports both.

3. **Files** tab: go to `/home/<username>/fencing-club-app/frontend/`, upload `dist.zip`, then in the console:

    ```bash
    cd ~/fencing-club-app/frontend && unzip dist.zip && rm dist.zip
    ```

## Step 4: set the environment variables for the console

Make a secret key (once) and copy it:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Open `~/.virtualenvs/fencing/bin/postactivate` (in the Files tab or with `nano`) and add:

```bash
export DJANGO_DEBUG=false
export DJANGO_SECRET_KEY='paste-the-key-here'
export SITE_HOST=<username>.pythonanywhere.com
```

Then reload the environment and prepare the database and static files:

```bash
deactivate && workon fencing
cd ~/fencing-club-app/backend
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

`db.sqlite3` is in `.gitignore`, so this is a fresh, empty database. If you'd rather keep the data from your Mac, upload your local `backend/db.sqlite3` to the same folder in the Files tab *before* running `migrate`.

## Step 5: create the web app

1. **Web** tab → **Add a new web app** → **Manual configuration** (not "Django", which would start a new project) → the same Python version as your virtualenv.
2. On the web app's page, set:

    | Field | Value |
    | --- | --- |
    | Source code | `/home/<username>/fencing-club-app/backend` |
    | Working directory | `/home/<username>/fencing-club-app/backend` |
    | Virtualenv | `/home/<username>/.virtualenvs/fencing` |
    | Force HTTPS | On |

3. Click the **WSGI configuration file** link, delete everything in it, and write:

    ```python
    import os
    import sys

    path = '/home/<username>/fencing-club-app/backend'
    if path not in sys.path:
        sys.path.insert(0, path)

    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    os.environ['DJANGO_DEBUG'] = 'false'
    os.environ['DJANGO_SECRET_KEY'] = 'paste-the-same-key-here'
    os.environ['SITE_HOST'] = '<username>.pythonanywhere.com'

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
    ```

    Compare this with `config/wsgi.py`. It does the same job, plus two things that file doesn't need locally: putting `backend/` on Python's import path so `import config` works, and setting the variables.

4. Don't add any entries under **Static files**. WhiteNoise already serves `/static/` and React's files from inside Django.
5. Click **Reload**, then open `https://<username>.pythonanywhere.com` and log in.

**Force HTTPS** matters because of Lesson 13's secure-cookie settings: with debug off, the browser only sends the login cookie over HTTPS.

## If something's wrong

The Web tab links to an **error log** and a **server log**. Check the error log first.

| Symptom | Likely cause |
| --- | --- |
| "Bad Request (400)" | `SITE_HOST` is missing or misspelled in the WSGI file |
| `KeyError: 'DJANGO_SECRET_KEY'` | The key isn't set in the WSGI file |
| "No React build" | `frontend/dist/index.html` doesn't exist. Check where the zip unpacked |
| Page loads with no styles, or a 500 mentioning the manifest | `collectstatic` wasn't run, or was run without `workon fencing` |
| "CSRF verification failed" when saving | `SITE_HOST` doesn't match the address in the browser, or Force HTTPS is off |
| `no such table` | `migrate` wasn't run against this database |

## Updating the site later

On your Mac, push your changes (and rebuild and zip `dist/` if the frontend changed). Then on PythonAnywhere:

```bash
workon fencing
cd ~/fencing-club-app && git pull
cd backend && pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Upload and unzip the new `dist.zip` if needed (delete the old `dist/` first), then click **Reload**.

**Backups:** now and then, download `backend/db.sqlite3` from the Files tab.

---

# Lesson 16: Inviting people to log in

**Goal:** a manager invites a coach or member by email. They click the link, choose their own password, and are logged in. Anyone can reset a forgotten password from the login page, and managers can switch a login off. Claude built this one; read through the files below to learn from it.

## What was added

| Where | What |
| --- | --- |
| `config/settings.py` | `FRONTEND_URL` for links, email settings, and links that last 7 days |
| `club/emails.py` (new) | Builds the set-password link and sends the invite and reset emails |
| `club/serializers.py` | `login_status()`, a `login` field on members, `LoginSerializer` and `InviteSerializer` |
| `club/views.py` | `LoginViewSet` (`/api/logins/`), `password-reset/`, `set-password/<uid>/<token>/`, and login by email with an attempt limit |
| `club/tests.py` | Invites, links working once, resending, switching off, resets, and who can do what |
| `SetPasswordPage.jsx` (new) | Where the email links land, for invites and resets alike |
| `LoginsPage.jsx` (new) | The manager's **Logins** page: everyone's status, **Invite**, **Resend invite**, **Switch off/on** |
| `LoginPage.jsx` | "Email or username", and **Forgot password?** |
| `MemberPage.jsx` | A **Login** row with **Invite to log in** |
| `App.jsx` | `/set-password/...` works logged in or out, and a Logins link for managers |

## Key ideas

### An invite is a password reset in disguise

When the manager invites Alex, the server creates the `User` and `Profile` straight away, but with **no usable password**:

```python
user = User(username=email, email=email)
user.set_unusable_password()
```

The email then contains a link to choose a password. That's exactly what a "forgot password" link does, so both use the same page and the same code. The only difference is the wording.

Until Alex sets a password, nobody can log in as them, and the Logins page shows **Invited**.

### Links that work once, without a table of tokens

Django's `default_token_generator` makes a token from the user's id, their **password hash**, their last login, and the time:

```python
uid = urlsafe_base64_encode(force_bytes(user.pk))
token = default_token_generator.make_token(user)
```

Nothing is saved in the database. To check a link, Django rebuilds the token from the user's *current* data and compares. So:

- **Setting the password changes the hash**, and the link stops working. Each link works once.
- **Resending calls `set_unusable_password()` again**, which makes a new random hash, so the old email's link stops working too.
- **Links expire** after `PASSWORD_RESET_TIMEOUT` (7 days here).

### The role comes from the manager, never the form

The set-password page only sends a password. Who the person is (member or coach, and which member) was decided when the manager invited them, and is already in their `Profile`. Someone can't edit the request to make themselves a manager.

### Not giving anything away

- **Password reset always gives the same answer**, "If that email has a login, we've sent it a link", so nobody can use it to find out who's in the club.
- **Too many attempts:** `too_many_attempts()` counts tries in Django's cache. After 10 logins as one username, or 3 reset requests for one email, in 15 minutes, it refuses. It's counted per username, not per computer, because PythonAnywhere's proxy makes every visitor look like the same address.
- **Switching off** sets `is_active = False`. Django refuses to log them in, and their existing session stops working. Their attendance history stays, which deleting the login would also keep, but this way you can switch them back on.

### Email in development and online

Locally, `EMAIL_BACKEND` is the **console backend**: emails are printed in the `runserver` terminal, link and all. Tests use Django's in-memory outbox, `mail.outbox`, which is how the tests find the link.

Online, set these in the WSGI file and `postactivate` (Lesson 15), e.g. for Gmail with an [app password](https://myaccount.google.com/apppasswords):

```bash
export EMAIL_HOST=smtp.gmail.com
export EMAIL_HOST_USER=yourclub@gmail.com
export EMAIL_HOST_PASSWORD='the 16-letter app password'
export DEFAULT_FROM_EMAIL='Fencing Club <yourclub@gmail.com>'
```

PythonAnywhere's free tier allows SMTP to Gmail. `FRONTEND_URL` becomes `https://<SITE_HOST>` by itself.

## Try it

1. Run both servers. No migration is needed: invites reuse `User` and `Profile`.
2. As a manager, give a member an email, open their page and click **Invite to log in**. The email appears in the `runserver` terminal.
3. Open the link in a private window. Choose a password: try `123` first to see Django's password rules. You land in the app as that member.
4. Click the same link again. It says it has expired or been used.
5. Go to **Logins**, click **Invite**, choose **Coach**, and invite a coach by name and email.
6. **Switch off** the member, then try to log in as them.
7. Log out, click **Forgot password?**, and reset a password.

# Lesson 17: Coaches get their own table

**Goal:** coaches become real records, like members, with a **Coaches** page in the sidebar. A class picks its coach from a list instead of a typed name, and a coach's login is tied to that coach. Claude built this one; read through the files below to learn from it.

## What was added

| Where | What |
| --- | --- |
| `club/models.py` | A `Coach` model. `FencingClass.coach` and `Profile.coach` now point at it, replacing the typed names |
| `club/migrations/0008_coach.py` | Makes a `Coach` for every coach name already in the database and links the classes and logins to it |
| `club/serializers.py` | `CoachSerializer`, a `coach_name` on classes, and invites take a `coach` like they take a `member` |
| `club/views.py` | `CoachViewSet` (`/api/coaches/`) with class counts and the next class. `classes/coaches/` is gone |
| `club/admin.py` | Coaches in the admin, and coach pickers with search |
| `club/tests.py` | Coach CRUD, unique names, counts, and coach logins using the new link |
| `CoachesPage.jsx`, `CoachPage.jsx`, `CoachForm.jsx` (new) | The list, one coach's page (details, login, upcoming and recent classes), and a form to add or edit |
| `ClassForm.jsx`, `ClassFilters.jsx`, `LoginsPage.jsx` | Pick a coach from a dropdown |
| `auth.js`, `classes.js` | `me.coach` is now the coach's id, not their name |

## Key ideas

### Why a typed name wasn't enough

Before, a class's coach was just text, and a coach login worked by having *exactly the same text* in `Profile.coach_name`. Type "Coach Lim" on one class and "coach lim" on another and they were two different coaches, and the login silently stopped seeing one of them. Renaming a coach meant editing every class.

A `ForeignKey` stores the coach's **id** instead. There's one row per coach, so renaming them renames them everywhere, and the login compares ids, which can't be mistyped.

```python
coach = models.ForeignKey(
    Coach, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes'
)
```

`SET_NULL` means deleting a coach leaves their classes in place with no coach, rather than deleting the classes (`CASCADE`) or refusing (`PROTECT`). `related_name='classes'` is what lets the view write `Count('classes')`.

### A migration that moves data

Changing a column's type would lose the names already typed in, so `0008_coach.py` does it in steps:

1. Create the `Coach` table.
2. Rename the old text fields out of the way (`coach` → `coach_name`).
3. Add the new `coach` links, empty.
4. **`RunPython`**: for every name, `get_or_create` a `Coach` and point the class or login at it.
5. Remove the old text fields.

Inside a migration you use `apps.get_model('club', 'Coach')`, not `from .models import Coach`. The real model is how the code looks *today*; `apps.get_model` gives you the model as it was at this point in the migration history. The second function passed to `RunPython` undoes it, so `migrate club 0007` works too.

On PythonAnywhere, `git pull` then `python manage.py migrate` (Lesson 15) runs the same conversion on the live data.

### Invites now match for members and coaches

A coach used to be invited with a name and an email typed into the form. Now the email lives on the coach, just like a member, so `InviteSerializer` takes either `member` or `coach` and treats them the same way: no email, no invite.

### A login with no coach sees nothing

If a coach is deleted, their login's `Profile.coach` becomes `None`. A careless check `class.coach_id == profile.coach_id` would then be `None == None`, which is **true** for every class with no coach. `coaches_class()` in `views.py` checks for `None` first, and there's a test for it.

## Try it

1. Run `python manage.py migrate`. Open **Coaches**: everyone you'd typed as a coach is there already.
2. Click **New coach**, then open them and click **Edit coach** to add an email.
3. Edit a class and pick the new coach from the dropdown. Their page shows it under **Upcoming classes**.
4. On the coach's page, click **Invite to log in**, accept the invite in a private window, and check you can mark that class.
5. Rename the coach. The calendar and table show the new name everywhere.

# Lesson 18: Editing members, and their primary coach

**Goal:** managers can edit a member from their page, and each member can have a **primary coach** picked from the Coaches table. Claude built this one.

## What was added

| Where | What |
| --- | --- |
| `club/models.py` | `Member.primary_coach`, a `ForeignKey` to `Coach` |
| `club/migrations/0009_member_primary_coach.py` | Adds the column. Everyone starts with no primary coach |
| `club/serializers.py` | `primary_coach` (the id) and `primary_coach_name` on members |
| `club/views.py` | `/api/members/?primary_coach=<id>` |
| `club/tests.py` | Editing, setting the coach, the filter, and deleting the coach |
| `MemberForm.jsx` | Adds *or* edits, like `CoachForm`, with a **Primary coach** dropdown |
| `MemberPage.jsx` | **Edit member** for managers, and a **Primary coach** row |
| `MembersPage.jsx`, `CoachPage.jsx` | A Primary coach column, and a coach's **Members they coach** |

## Key ideas

### The backend already allowed edits

`MemberViewSet` is a `ModelViewSet`, so `PATCH /api/members/<id>/` has worked since Lesson 4. Only the page was missing. `RoleAccess` still refuses edits from coaches and members, because neither lists `partial_update` in `role_actions`.

### `'Coach'` in quotes

`Member` is defined above `Coach` in `models.py`, so `Coach` doesn't exist yet when Python reads `Member`. Writing `models.ForeignKey('Coach', ...)` as a string lets Django look it up once every model is loaded.

### `related_name='members'`

That's the name for going the other way: `coach.members.all()` is everyone with that coach as their primary coach. Without it, Django would call it `coach.member_set`.

### PATCH vs POST in one form

The form sends `PATCH` when it was given a member, and `POST` otherwise. With `PATCH`, only the fields you send change, and the attendance counts are read-only, so sending the whole form is safe.

## Try it

1. Run `python manage.py migrate`.
2. Open a member, click **Edit member**, pick a primary coach, and save.
3. Click the coach's name. The member is listed under **Members they coach**.
4. Log in as a coach and open the same member. There's no Edit button, and the API refuses a `PATCH` too.

# Lesson 19: Members book classes and edit their own details

**Goal:** a member can enrol themselves in upcoming classes, cancel an enrolment, and change their own name, phone and weapon. Claude built this one.

## What was added

| Where | What |
| --- | --- |
| `club/views.py` | `POST /api/classes/<id>/enrol/` and `/unenrol/`, `?bookable=1`, and members may `PATCH` themselves |
| `club/tests.py` | Enrolling, full and past classes, cancelling, and which fields a member can change |
| `BookPage.jsx` (new) | **Book a class**: upcoming classes they're not on, with spots left and **Enrol** |
| `AttendancePanel.jsx` | **Enrol** or **Cancel enrolment** for members on an upcoming class |
| `MemberPage.jsx`, `MemberForm.jsx` | **My profile** with **Edit my details**, showing only what a member can change |
| `App.jsx` | **Book a class** and **My profile** in a member's sidebar |

## Key ideas

### Same permission class, more entries

Nothing new was needed in `permissions.py`. `RoleAccess` (Lesson 10) already reads three things from each viewset, so members get access by listing it:

```python
role_actions = {MEMBER: {'retrieve', 'partial_update'}}
role_fields = {MEMBER: {'name', 'phone', 'weapon'}}
```

`role_fields` is why a member's `PATCH` with `email`, `active` or `primary_coach` is refused with 403, even though the manager's form sends them. **Email** stays with the manager because it's also the login: changing it would change where password reset links go.

### Actions instead of letting members write attendance

Members could have been given `create` on `/api/attendance/`, but then the request would say *which* member and *what* status. An `enrol` action takes nothing from the request: the member comes from `request.user.profile.member` and the status is always `enrolled`. The action checks the rules before creating the row:

- The membership is active.
- The class hasn't started yet.
- The member isn't already on the class.
- The class isn't full (`capacity`).

`unenrol` only deletes a row that is still `enrolled` in an upcoming class. Once a coach has marked it, cancelling is up to a manager.

### A subquery keeps the headcounts right

A member now has to be able to open classes they're *not* on yet, so their queryset became "mine **or** upcoming". Writing "mine" as a join (`attendance__member__profile__user=...`) inside an `OR` would repeat each class once per attendance row and inflate `member_count`. So "mine" is a subquery instead:

```python
mine = Q(id__in=Attendance.objects.filter(
    member__profile__user=self.request.user
).values('fencing_class'))
```

## Try it

1. No migration this time. Log in as a member with an active membership.
2. Open **Book a class** and click **Enrol**. The class moves to **My classes** and **My calendar**.
3. Open it there and click **Cancel enrolment**.
4. As a manager, set a class's capacity to how many are already on it. The member sees **Full**.
5. As the member, open **My profile**, click **Edit my details**, and change your phone. The email box is greyed out.

# Lesson 20: Private lessons

**Goal:** a member picks one of their coaches, sees when that coach is busy (but not with what), drags across a free time to ask for a lesson, and the coach accepts or declines. Claude built this one.

## What was added

| Where | What |
| --- | --- |
| `club/models.py` | `LessonRequest`: member, coach, times, note, status, and the class it became |
| `club/migrations/0010_lessonrequest.py` | The new table |
| `club/views.py` | `LessonRequestViewSet` at `/api/lesson-requests/`, with `coaches/`, `busy/`, `accept/`, `decline/` and `cancel/` |
| `club/tests.py` | Which coaches, busy times, clashes, accepting, declining, cancelling, and who can do each |
| `LessonsPage.jsx` (new) | A member's **Private lessons**: pick a coach, their week with **Busy** blocks, and **My requests** |
| `LessonRequestPanel.jsx` (new) | Opens from a dashed request on the calendar, with **Accept** and **Decline** (see Lesson 21) |

## Key ideas

### A request becomes a class

Accepting a request creates a `FencingClass` with `capacity=1`, the member enrolled, and the coach set:

```python
fencing_class = FencingClass.objects.create(
    name=f'Private lesson: {lesson.member.name}', start=lesson.start, end=lesson.end,
    coach=lesson.coach, weapon=lesson.member.weapon, capacity=1, notes=lesson.note,
)
```

Because it's an ordinary class, it shows on the calendars and in the tables, and the coach marks attendance the usual way. Nothing else had to learn about lessons. The one exception: **Book a class** must not offer it to other members, so the member queryset leaves out classes with a `lesson_request`.

### Busy, but not with what

`busy/` returns only `start` and `end`:

```python
slots = [*classes.values('start', 'end'), *pending.values('start', 'end')]
```

`.values()` asks the database for just those columns, so names, members and notes can't leak even by accident. Pending requests count as busy too, so two members can't ask for the same slot. The member's own requests are left out of `busy/`, because the page draws them from `list/` with their status.

### Which coaches are "theirs"

`coaches_of(member)` is their primary coach, plus the coach of any class they're on:

```python
Coach.objects.filter(Q(members=member) | Q(classes__attendance__member=member), active=True).distinct()
```

`members` and `classes` are the `related_name`s from Lessons 17 and 18. `.distinct()` is there because the join returns a coach once per matching class.

### Who can do what

The same `RoleAccess` lists again:

| | List | Request | Cancel | Accept / decline |
| --- | --- | --- | --- | --- |
| Member | Their own | Their own coaches | Their own, before it starts | — |
| Coach | Their own | — | — | Their own |
| Manager | Everyone's | — | — | Anyone's |

Cancelling an accepted lesson deletes its class.

## Try it

1. Run `python manage.py migrate`.
2. As a manager, give a member a primary coach (Lesson 18).
3. As that member, open **Private lessons**. Their coach's classes show as grey **Busy** blocks.
4. Drag across a free time, add a note, and **Send request**. It shows as yellow **Requested**.
5. As the coach (or a manager), click the dashed yellow request on the calendar and **Accept**. It becomes "Private lesson: …".
6. As another member with the same coach, open **Private lessons**. That time is just **Busy**.

# Lesson 21: Peek at members, and requests on the calendar

**Goal:** clicking a member opens a side panel, like classes do, instead of a separate page. Pending lesson requests show on the main calendar instead of their own tab. Claude built this one.

## What changed

| Where | What |
| --- | --- |
| `MemberPage.jsx` → `MemberPanel.jsx` | The same details as a side panel. **My profile** still shows them as a page |
| `MembersPage.jsx` | Clicking a row opens the panel. The member is in the URL: `/members?member=3` |
| `App.jsx` | The **Lesson requests** tab is gone. Old `/members/3` links redirect to the panel |
| `LessonRequestPanel.jsx` (new) | Replaces `LessonRequestsPage.jsx`. Opens from the calendar |
| `CalendarPage.jsx` | Loads pending requests beside classes, dashed and yellow |
| `club/views.py` | `lesson-requests/` takes `start`, `end`, `coach` and `member`, like `classes/` |
| `LoginRow.jsx` (new) | Replaces the **Logins** tab: the **Login** row on a member or coach now has **Invite**, **Resend invite** and **Switch off/on** |
| `ClassesHeader.jsx` (new) | One **Classes** item in the sidebar, with a **Calendar \| List** switch on the page instead of a separate **All classes** tab |

## Key ideas

### One component, two wrappers

`MemberDetails` holds everything about a member. `MemberPanel` puts it in an `<aside className="panel">` with a close button. `MemberProfilePage` puts it in a `<div className="page">`. The CSS shrinks the avatar and title when they're `.panel` children, so nothing inside had to change.

### The selection lives in the URL

`useSearchParams()` reads and writes `?member=3`. The coach page and the class panel can then link straight to a member with an ordinary `<Link>`, and the browser's back button closes the panel.

### Two kinds of event on one calendar

`loadClasses` fetches classes and pending requests together, then merges them. Each request carries its data in `extendedProps`, so `eventClick` knows which panel to open:

```js
const lesson = event.extendedProps.lesson
```

Requests have no location or weapon, so when either of those filters is set, requests are hidden rather than shown wrongly.

### One sidebar item, two routes

The calendar is still `/` and the list is still `/table`, so the filters App keeps carry across. The switch is two `NavLink`s, which add an `active` class by themselves. The sidebar item checks `useLocation().pathname` instead, so it stays highlighted on both.

## Try it

1. As a manager, open **Members** and click a row. Edit them from the panel, then press back.
2. As a member, request a lesson from **Private lessons**. It shows dashed on **My calendar**.
3. As the coach, it's dashed on their calendar too. Click it and **Accept**. The new class's panel opens.

---

# Lesson 22: The frontend in htmx and Alpine.js (branch `htmx-frontend`)

**Goal:** the same app with no React and no npm. Django renders every page from templates, htmx swaps parts of a page in place, and Alpine.js keeps the little state that only lives in the browser. Claude built this one, on its own branch, so `main` keeps the React version.

## What changed

| Where | What |
| --- | --- |
| `frontend/` | Gone. No `npm run build`, no `dist.zip` to upload |
| `backend/web/` (new app) | `views.py`, `forms.py`, `urls.py` and `templates/web/`: one Django view per page or piece of a page |
| `web/static/web/vendor/` | htmx 2.0.11, Alpine.js 3.17.4 and FullCalendar 7.1.3, saved as plain files, so nothing loads from a CDN |
| `web/static/web/app.js` | The Alpine components: `peek` (side panels), `filters`, `classCalendar`, `lessonCalendar` |
| `web/static/web/app.css` | The old `App.css`, plus a few lines for htmx and Alpine |
| `club/services.py` (new) | The club's rules (enrol, repeat weekly, accept a lesson, invite…), moved out of the API's viewsets so the API and the pages share them |
| `club/views.py` | The viewsets call `services`. A small `exception_handler` turns the services' errors into the API's usual 400s |
| `config/settings.py` | `'web'` in `INSTALLED_APPS`, `LOGIN_URL`, and `SITE_URL` (was `FRONTEND_URL`) for email links |
| `web/tests.py` (new) | Tests for the pages: logins, roles, the calendar feed, dialogs, panels, lessons |

The JSON API at `/api/` is still there, with all its tests, but no page uses it now.

## Key ideas

### HTML over the wire

React fetched JSON and built the HTML in the browser. Now the server sends HTML. A button says where its result goes:

```html
<button hx-post="/classes/5/enrol/" hx-vals='{"enrolled": "1"}'
        hx-target="closest .panel" hx-swap="outerHTML">Enrol</button>
```

The view runs `services.enrol(...)` and renders `class_panel.html` again, which replaces the old panel. There's no client-side state to keep in sync: the template is the only description of what a class panel looks like.

### Response headers steer the page

A view can change what happens next with htmx's headers (see the `htmx()` helper in `web/views.py`):

- `HX-Trigger: classesChanged` fires an event in the browser. The calendar listens and calls `refetchEvents()`; the list's `<div hx-trigger="classesChanged from:body">` reloads itself.
- `HX-Retarget: #panel` puts the response somewhere else. A saved **New class** dialog comes back as the new class's panel.
- `HX-Trigger-After-Swap: closeModal` closes the dialog, *after* the swap. Closing it first would remove the form that made the request, and htmx skips the swap for a request whose element is gone.

### One page, many fragments: `hx-select`

The list view reloads with `hx-get="/table/" hx-select="#class-table"`. The server returns the whole page and htmx keeps just that part, so there's no separate "rows only" view. `hx-disinherit="*"` on that div matters: htmx attributes are inherited, and without it each row's click would also try to `hx-select="#class-table"` out of the panel it fetched, and find nothing.

### Where Alpine fits

htmx covers anything that talks to the server. Alpine covers state that never needs to:

- **`peek`**: which side panel is open. Each panel's `x-init="selected = '5'"` tells the page which row to highlight; the × and Escape call `close()`. On Members it also keeps `?member=5` in the URL.
- **`filters`**: the four filter dropdowns use `x-model`. A `$watch` updates the URL and fires `filters-changed`, which the calendar and the list both listen for. The **Calendar | List** links use `:href` to carry the filters across.
- **Calendars**: `x-data="classCalendar({...})"` makes the FullCalendar when Alpine starts. Clicking an event calls `htmx.ajax('GET', panelUrl, {target: '#panel'})`, so even the calendar opens panels the htmx way.

### Forms are Django forms

`ClassForm`, `MemberForm`, `OwnDetailsForm` and friends do the validation React did by hand. `OwnDetailsForm` makes `email` a `disabled` field, so Django ignores whatever is posted for it: a member can't change their login email even with a hand-made request.

## Running it

```bash
cd backend
source .venv/bin/activate
python manage.py runserver
```

Open http://localhost:8000. There's no second server any more.

To deploy on PythonAnywhere (Lesson 15), skip the steps about building React and uploading `dist.zip`: `git pull`, `python manage.py collectstatic --noinput`, `python manage.py migrate`, then **Reload**.

## Try it

1. As a manager, pick a weapon filter, then switch to **List**. The filter comes with you, and the URL shows it.
2. Click a row: the panel opens and the row highlights. Press Escape.
3. **+ New class**, fill in a weapon and location, press **Generate**, then **Create class**. The dialog closes, the panel opens and the calendar updates, all from one response.
4. As a member, drag across a free time on **Private lessons**. As the coach, click the dashed request and **Accept**.

---

# Lesson 23: One Django project, organised by job (branch `htmx-frontend`)

**Goal:** with React gone, stop pretending there's a backend and a frontend. The repo is now one Django project, the JSON API is gone, and the code is grouped by what it does. Claude built this one.

## What changed

| Where | What |
| --- | --- |
| `backend/` | Gone. `manage.py`, `requirements.txt`, `config/`, `club/` and `web/` are at the top of the repo, and so are `db.sqlite3` and `.venv` |
| The JSON API | Deleted: `club/views.py`, `club/urls.py`, `club/serializers.py`, `club/permissions.py`, and `djangorestframework` from `requirements.txt`. git still has it on `main` |
| `club/roles.py` (new) | `role_of()` and login status, which used to live beside DRF's permission class |
| `club/queries.py` (new) | Who can see what: `visible_classes(user)`, `shown_classes(user, filters)`, `can_edit_class(user, c)` and friends. These used to be inside the views |
| `club/tests.py` | Rewritten to test models, `services` and `queries` directly. The rules the API tests checked are kept here |
| `web/views.py` → `web/views/` | One module per sidebar area: `auth`, `classes`, `book`, `lessons`, `members`, `coaches`, plus `common` for `role_required` and `htmx()` |
| `web/templates/web/` | Grouped the same way: `classes/`, `lessons/`, `members/`… and `partials/` for pieces many pages use (`field.html`, `modal.html`) |
| `web/tests.py` → `web/tests/` | One file per area, testing the pages and who may use them |
| `club/emails.py` | Invite and reset links now end in `/` |

## Key ideas

### Three layers, three questions

- **`club/queries.py`: what may this person see?** `visible_classes(user)` is the only place that says a member can open their own classes and ones they could book. Every view that loads a class goes through it, so a new page can't forget the rule.
- **`club/services.py`: what happens when they act?** Enrolling checks capacity and start time. Accepting a lesson makes a one-person class. These raise `ValidationError` with a message to show.
- **`web/views/`: which HTML goes back?** Views are now mostly "ask queries, call a service, render a template, add htmx headers".

`club` doesn't import anything from `web`. That's the boundary to keep: if you ever add an API or a phone app again, it would sit beside `web` and use the same `club`.

### Testing rules without HTTP

`club/tests.py` calls `services.enrol(member, fencing_class)` directly instead of posting to a URL. Those tests are shorter and faster, and they say exactly which rule they check. `web/tests/` then only has to check the parts that are about pages: the right template, the right htmx headers, and 403s for the wrong role.

## Moving the PythonAnywhere site

Do these once, in this order, after pushing the branch and merging it into `main`:

1. **Bash console:**
    ```bash
    cd ~/fencing-club-app
    git pull
    mv backend/db.sqlite3 db.sqlite3     # git doesn't move files it doesn't track
    workon fencing
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py collectstatic --noinput
    rm -rf backend frontend               # only old, untracked files are left in them
    ```
2. **Web tab:** change **Source code** and **Working directory** to `/home/<username>/fencing-club-app` (no `/backend`).
3. **WSGI file:** change the `path = ...` line to `/home/<username>/fencing-club-app`.
4. **Reload**, then log in to check.

If you use the backup step from Lesson 15, the database is now at `~/fencing-club-app/db.sqlite3`.

## Running it locally

```bash
cd ~/Projects/fencing_club_app
source .venv/bin/activate
python manage.py test        # 98 tests
python manage.py runserver
```

---

# Lesson 24: A side peek for coaches

**Goal:** clicking a coach opens a side panel, like members, instead of a separate page. Claude built this one.

## What changed

| Where | What |
| --- | --- |
| `coaches/list.html` | The table sits in a `peek` Alpine component, and each row loads the coach with `hx-get` into `#panel`. The open coach is in the URL: `/coaches/?coach=3` |
| `coaches/panel.html`, `coaches/details.html` (new) | The panel, and the details inside it. `detail.html`, the old full page, is gone |
| `web/views/coaches.py` | `coach_panel` replaces `coach_page`. Saving **Edit coach** replaces `#coach-details`; **New coach** opens the new coach's panel. Both fire `coachesChanged`, which reloads the table |
| `members/details.html` | A member's primary coach links to `/coaches/?coach=3` |
| `club/queries.py` | `classes()` and `coaches()` now `order_by` explicitly (see below) |

## Key ideas

### Same pattern, new data

This is the Members peek again, with nothing new in `app.js`: `peek(selected, 'coach')` keeps `?coach=` in the URL, and the panel's `x-init="selected = '3'"` highlights its row.

### A normal visit to a panel URL

`/coaches/3/` and `/members/3/` return just a panel, which only makes sense inside a page. So when the request doesn't come from htmx (`is_htmx(request)` is false), the view redirects to the list with that panel open. Old bookmarks keep working.

### Django drops default ordering when it counts

`FencingClass.Meta.ordering = ['start']` doesn't apply to a query with `annotate(Count(...))`. Django leaves it out on purpose, because it would change what gets grouped together. So `queries.classes()` came back in no particular order: on the coach panel, a private lesson on 6 Nov showed up after a class on 24 Nov. The fix is an explicit `.order_by('start')`, with a test for it.

---

# Lesson 25: Working on two branches at once with git worktrees

**Goal:** keep `mobile-optimized` open and running while you start something else on a second branch, in a second folder, without stashing or switching.

## Key ideas

### One repository, several folders

`git switch` swaps the files in your one folder, so you have to commit or stash first, and the running server reloads into the other branch. A **worktree** is a second folder checked out from the *same* repository. Each folder has its own branch and its own files; they share the history, the branches and the commits. A commit made in one folder is visible from the other straight away, with no push or pull.

You already have one: `../fencing_club_app-lesson10`, from Lesson 10.

### One branch, one folder

Git won't let the same branch be checked out in two worktrees (`fatal: 'main' is already checked out at ...`). That's on purpose: two folders writing to one branch would trample each other. Each worktree gets its own branch.

### Only committed work travels

A new worktree starts from a **commit**. Anything staged or unstaged in this folder stays here. Right now the Lesson 23–24 changes are staged but not committed, so a worktree made from `mobile-optimized` would not have them. Commit first if you want them in both places.

### Ignored files don't come along

Everything in `.gitignore` is missing from a new worktree: `.venv/`, `db.sqlite3`, `staticfiles/`. Each folder needs its own virtual environment and its own database. The separate database is the point: a migration on one branch can't break the other branch's data.

## Steps

### 1. Make the worktree

Put it next to the project, not inside it, so the two folders never see each other's files:

```bash
cd ~/Projects/fencing_club_app
git worktree add -b coach-calendar ../fencing_club_app-coach-calendar mobile-optimized
git worktree list
```

`-b coach-calendar` creates the new branch, `../fencing_club_app-coach-calendar` is the folder, `mobile-optimized` is where the branch starts.

### 2. Give it a venv and a database

```bash
cd ../fencing_club_app-coach-calendar
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../fencing_club_app/db.sqlite3 .     # a copy of your test data
python manage.py migrate
```

### 3. Run both servers

Two servers can't share a port, and browser cookies ignore the port, so logging in on `localhost:8001` would log you out of `localhost:8000`. Use the other allowed host name for the second one:

```bash
python manage.py runserver 127.0.0.1:8001
```

Main folder: http://localhost:8000. New worktree: http://127.0.0.1:8001.

Open the folder in its own VS Code window (`code .`) so the editor, terminal and any Claude Code session there all work on that branch.

### 4. Bring the work back

Commit in the worktree as usual. Then, from the main folder:

```bash
cd ~/Projects/fencing_club_app
git merge coach-calendar
```

**Watch the migrations.** If both branches ran `makemigrations`, both will have a `0011_...`. After merging, `python manage.py migrate` stops with *Conflicting migrations detected*. Fix it with:

```bash
python manage.py makemigrations --merge
```

That adds a small migration that depends on both.

### 5. Clean up

```bash
git worktree remove ../fencing_club_app-coach-calendar
git branch -d coach-calendar          # -d refuses if it isn't merged yet
```

`remove` refuses if the folder has uncommitted changes; that's your safety net. If you deleted a worktree folder by hand, `git worktree prune` tidies up the leftovers.

## Try it

1. Run `git worktree list`. What branch is `fencing_club_app-lesson10` on, and is that layout (`backend/`, `frontend/`) still useful to you? If not, remove it.
2. Make a worktree, change a template there, and run both servers side by side to compare.
3. In the worktree, run `git log -1`. Then commit something in the *main* folder and run `git log mobile-optimized -1` from the worktree. Why do you see the new commit without pulling?

---

# Lesson 26: Syncing classes to Google Calendar

**Goal:** let anyone see their classes in Google Calendar by subscribing to a secret link, without OAuth or Google API keys. Claude built this one, in a parallel worktree (Lesson 25).

## What changed

| Where | What |
| --- | --- |
| `club/models.py` | `CalendarFeed`: one secret `token` per user, with `reset()` to swap it for a new one. Its own model because managers have no `Profile` |
| `club/migrations/0011_calendarfeed.py` | Creates the table |
| `club/ical.py` (new) | Turns classes into iCalendar text: escaping, UTC times, line folding, CRLF |
| `club/queries.py` | `feed_classes(user)`: the classes on their calendar, from 60 days ago onwards |
| `web/views/feeds.py` (new) | The Calendar sync page, Reset link, and the public `.ics` feed |
| `web/urls.py` | `calendar-sync/`, `calendar-sync/reset/`, `calendar/<token>.ics` |
| `web/templates/web/feeds/` (new) | The page, and the link box that Reset swaps out |
| `web/templates/web/layout.html` | A Calendar sync item in the sidebar for every role ("Sync" in the phone tab bar) |
| `web/tests/test_feeds.py` (new) | Tokens, who sees what, reset, escaping and folding |

## Key ideas

### Subscribe, don't sync

Writing into someone's Google Calendar would need OAuth, Google credentials and outbound requests, and PythonAnywhere's free tier blocks most outbound requests. Instead the app *publishes* an `.ics` file at a URL, and Google *pulls* it (Other calendars → From URL). Nothing leaves our server. The catch: Google decides when to fetch again, every few hours and sometimes up to a day, so changes aren't instant.

### A secret URL instead of a login

Google fetches the feed anonymously, so `calendar_feed` has no `@role_required`. The long random token (`secrets.token_urlsafe(32)`) is the password. Anyone holding the URL can read the calendar, so **Reset link** saves a new token, and the old URL returns 404 straight away. Reset is a POST with CSRF protection, because it changes data.

### Reusing "who sees what"

The feed doesn't write its own filters. It calls `queries.shown_classes(user, {})`, the same function behind the calendar page, so a member's feed can't contain someone else's private lesson. One extra guard: a login with no role, or a switched-off one, gets a 404, because `shown_classes` returns everything for a user without a role.

### The .ics format (RFC 5545)

Plain text inside `BEGIN:VCALENDAR` … `END:VCALENDAR`, with one `VEVENT` per class. The rules that bite:

- Lines end with `\r\n`, not just `\n`.
- `,` `;` `\` and newlines inside text are escaped (`\,` `\;` `\\` `\n`).
- Lines over 75 *bytes* fold onto the next line, which starts with a space. Count bytes, not characters ("é" is 2), and never split a character.
- Times are written in UTC with a `Z` (`20261106T020000Z`), so the file needs no time zone definitions.
- Each event's `UID` (`class-42@yourhost`) stays the same between fetches, so Google updates the event instead of adding a copy.

### A partial for htmx to swap

`link.html` is the box with the URL and buttons. The page includes it, and Reset link returns just that box (`hx-target="#feed-link" hx-swap="outerHTML"`), so the new URL appears without a reload. Copy is Alpine only: `navigator.clipboard.writeText(...)` and a `copied` flag that changes the button text for two seconds.

## Putting it online

After pulling on PythonAnywhere, run `python manage.py migrate` and reload. Then the link on the Calendar sync page works in Google Calendar under **Other calendars → + → From URL**. Locally, Google can't reach `localhost`, so open the link in a browser tab, or import the file instead.

---

# Lesson 27: One model for every session (branch `training-sessions`)

**Goal:** merge `FencingClass` and `LessonRequest` into one `TrainingSession` model, with a category (fencing or physical conditioning) and a status (confirmed or unconfirmed). A capacity of 1 makes a session individual (a private lesson). Class becomes Session in the UI and URLs too. Claude built this one.

## What changed

| Where | What |
| --- | --- |
| `club/models.py` | `FencingClass` is now `TrainingSession`, with `category` and `status`, and an `is_individual` property (`capacity == 1`). `LessonRequest` is gone. `Attendance.fencing_class` is now `Attendance.session`, and a coach's sessions are `coach.sessions` |
| `club/migrations/0012_trainingsession.py` (new) | Written by hand: renames the table, adds the fields, moves lesson requests across, then deletes their table. It can be reversed |
| `club/queries.py` | `sessions()` returns **confirmed** sessions only. `lessons()` and `requests()` are the only ways to get unconfirmed ones. A new `scoped()` holds the "coach's own, member's own, or manager's filters" rule once, for sessions and requests alike |
| `club/services.py` | A request is created as an unconfirmed individual session with the member on it. Accepting it just sets `status`. Declining or cancelling deletes it. `coach_bookings` is now one query |
| `web/views/classes.py` → `sessions.py` | Renamed, and so are its views (`session_panel`, `session_form`…). Manager actions look sessions up through `queries.sessions()`, so they can't reach a request |
| `web/urls.py` | `/classes/…` is now `/sessions/…`, and URL names went from `class_*` to `session_*` |
| `web/forms.py` | `SessionForm` has category, and capacity's hint says 1 makes it a private lesson |
| Templates | `classes/` → `sessions/`. "Classes" → "Sessions" everywhere, a Category filter, a "Physical conditioning" tag in the list and on Book a session |
| `app.js`, `app.css` | `category` added to `FILTERS`, `classesChanged` → `sessionsChanged`, and a green tag for conditioning |
| Tests | `test_classes.py` → `test_sessions.py`, plus new tests that requests stay out of every session list, decline/cancel delete, conditioning in the form, Generate and the filter. 121 tests |

## Key ideas

### One table, two kinds of row

A private lesson used to live in two places: a `LessonRequest` while it was pending, then a copy made as a `FencingClass` when the coach accepted it. Now it's one row that changes `status`. Accepting goes from "create a class, create its attendance row, link the request to it" to one line:

```python
lesson.status = TrainingSession.Status.CONFIRMED
lesson.save(update_fields=['status'])
```

The member is recorded the same way as on a group session, with an `Attendance` row, so "who is on this session?" has only one answer. `TrainingSession.member` is a small `@property` that reads it for individual sessions.

### The risk: a request showing up where it shouldn't

With requests in the same table, any list of sessions could accidentally include them: on the calendar, on Book a session, in a feed, in the headcounts or in a member's history. The fix is to make the safe choice the default:

- `queries.sessions()` filters `status=CONFIRMED`. Everything else builds on it: `visible_sessions`, `shown_sessions`, `feed_sessions`, `bookable_sessions`
- `queries.requests()` and `queries.lessons()` are the only places that ask for unconfirmed sessions on purpose
- `can_edit_session()` returns False for anything unconfirmed, so nobody can mark attendance on a request
- `test_requests_are_not_sessions_yet` checks every one of these in one test

The rule of thumb is in `queries.py`'s docstring: start from those functions, never from `TrainingSession.objects`.

### Capacity decides individual or group

A first version also had a `type` field (group or individual). It was dropped because it said the same thing as capacity: a group session with room for one person *is* a private lesson. Two fields that must agree will eventually disagree, e.g. an "individual" session with capacity 8. That's a contradiction the app has to pick a side on. With one field, it can't happen.

So "individual" is now derived from capacity rather than stored:

```python
# club/models.py
@property
def is_individual(self):
    return self.capacity == 1

# club/queries.py: the same rule, for filtering in the database
INDIVIDUAL = Q(capacity=1)
...
return Q(start__gt=timezone.now()) & ~INDIVIDUAL   # bookable: upcoming group sessions
```

A property works in Python and templates (`{% if c.is_individual %}`), but the database can't filter on it. That's why there's also a `Q` object. The two must stay in sync, so each points at the other in a comment.

**The NULL trap:** blank capacity is stored as NULL ("no limit"). In SQL, `NOT (capacity = 1)` is *unknown*, not true, for NULL, so a hand-written query would quietly drop every unlimited session. Django's `~Q(capacity=1)` knows the column can be NULL and adds `OR capacity IS NULL` for you. `test_capacity_decides_individual_or_group` checks that capacity 1 is hidden from Book a session while 2 and blank are shown.

The trade-off: you can't have a group class capped at one person. For this club that's not a real case.

To filter by it, the Sessions page has a **size** filter (Group / Private lessons) next to category, and the admin has a matching `SizeFilter`. Both reuse `queries.INDIVIDUAL`: `.filter(INDIVIDUAL)` for private lessons and `.exclude(INDIVIDUAL)` for group. A plain `list_filter = ['capacity']` would list every capacity number instead, so the admin needs a small `SimpleListFilter` subclass with `lookups()` (the choices) and `queryset()` (what each one does).

### Renaming a model without losing data

If you rename a model and run `makemigrations`, Django asks *"Did you rename club.FencingClass to club.TrainingSession?"*. Answer yes and it writes `RenameModel`. Answer no and it writes `DeleteModel` + `CreateModel`, which **drops the table and every class in it**. Because this migration did several things at once, it's written by hand:

1. `RenameModel`: the table becomes `club_trainingsession`. Every row keeps its `id`
2. `AddField` ×2, each with a default, so existing rows become fencing and confirmed
3. `RenameField` on `Attendance`, with the unique constraint dropped and added again around it
4. `RunPython(merge_lesson_requests, split_lesson_requests)`: the data move
5. `DeleteModel('LessonRequest')`, only once its rows have been moved

Inside `RunPython`, use `apps.get_model('club', 'TrainingSession')`, never `from club.models import ...`. The imported model matches today's code, but the migration runs against the database as it was at that step. In step 4, the historical `LessonRequest` still exists even though `models.py` no longer has it.

### A reversible data migration

The second function in `RunPython` runs when you migrate backwards (`python manage.py migrate club 0011`). It turns individual sessions back into lesson requests, so going back doesn't lose anything that was pending. Without it, Django would refuse to go back past this migration. Declined and cancelled requests can't come back, since the forward step drops them.

### Stable calendar IDs

`ical.py` still writes `UID:class-42@host`. Sessions kept the ids they had as classes, and if the UID changed, Google Calendar would see every event as new and delete and re-add the whole calendar. A comment explains why it still says "class".

## Putting it online

The migration changes data, so **back up `db.sqlite3` first**. Then pull, and run `python manage.py migrate` and `collectstatic`, then reload. Old `/classes/42/` bookmarks now give a 404. The calendar at `/` and `/table/` are unchanged.

---

# Lesson 28: Your own server with Coolify on Oracle Cloud

**Goal:** run the app on a server you control, for free, with HTTPS and deploys from GitHub. Oracle Cloud's Always Free tier gives you a real Linux machine. Coolify is a self-hosted dashboard, like your own Render, that builds the app from GitHub and runs it in Docker. You write two small files in the repo, and the rest is setup on Oracle and in Coolify.

## Key ideas

### What's different from PythonAnywhere

| | PythonAnywhere (Lesson 15) | Coolify on Oracle |
| --- | --- | --- |
| What you get | A slot on someone else's server | A whole virtual machine (up to 4 ARM cores, 24 GB RAM) |
| How the app runs | PythonAnywhere's server imports your WSGI file | gunicorn inside a Docker container that Coolify builds |
| Database | SQLite in your home folder | SQLite in a Docker **volume**, which survives rebuilds |
| Environment variables | WSGI file and `postactivate` | Coolify's Environment Variables tab |
| Deploying | `git pull` in a console, then **Reload** | Push to GitHub, Coolify rebuilds (or click **Deploy**) |
| Outbound internet | Allowlist only | Open (except port 25), so SMTP on 587 works |
| You look after | Nothing | Ubuntu updates, the firewall, backups |

### Containers are thrown away

Each deploy, Coolify builds a fresh **image** from your `Dockerfile` and starts a new **container** from it. Anything the old container wrote to its own files is gone, which is what happened to SQLite on Render without a disk. A **volume** is a folder that lives outside the container and is mounted into each new one. You mount one at `/data` and point `SQLITE_PATH` at `/data/db.sqlite3`. The setting already reads it ([config/settings.py](config/settings.py)).

### Build time vs run time

The `Dockerfile` runs in two phases:
- **Build** (`RUN` lines): install requirements and run `collectstatic`. The result is baked into the image. No secrets are needed, and the volume isn't mounted yet.
- **Run** (`CMD`): every time the container starts, run `migrate` (now the volume *is* mounted), then start gunicorn.

`collectstatic` with `DJANGO_DEBUG=false` insists on a secret key, because `settings.py` crashes without one. A throwaway key on the `RUN` line is fine: collecting files signs nothing. The real key only exists at run time, in Coolify.

### Who handles HTTPS

Coolify runs a proxy (Traefik) on ports 80 and 443. It gets a free Let's Encrypt certificate for your domain, decrypts the traffic, and passes plain HTTP to gunicorn on port 8000 with an `X-Forwarded-Proto: https` header. That header is what `SECURE_PROXY_SSL_HEADER` in `settings.py` trusts, the same as on Render.

### Two firewalls on Oracle

Oracle blocks traffic twice: once in the cloud network (the **Security List**) and again inside Ubuntu (`iptables`). A port has to be open in both. This is the step most people get stuck on.

## Step 1: a Dockerfile

Create `Dockerfile` in the project folder, next to `manage.py`:

```dockerfile
FROM python:3.12-slim

# Print logs straight away, and don't litter the image with .pyc files.
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Requirements first: Docker caches this layer, so a code-only change skips pip.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hashed static files for WhiteNoise. The key is a placeholder: the real one is set at run time.
RUN DJANGO_DEBUG=false DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

EXPOSE 8000

# The volume is mounted by now, so migrate the real database, then serve.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --access-logfile -"]
```

Why copy `requirements.txt` on its own before the rest? Docker rebuilds from the first line whose inputs changed. Most deploys only change code, so the slow `pip install` layer is reused.

## Step 2: a .dockerignore

`COPY . .` copies everything, including your local database and your venv. Create `.dockerignore`:

```
.git
.venv
.claude
.gstack
__pycache__
*.pyc
db.sqlite3
staticfiles
.DS_Store
.env
```

Leaving out `db.sqlite3` matters most. Otherwise your Mac's data would be baked into every image.

## Step 3: try it on your Mac (optional)

If you have Docker Desktop:

```bash
docker build -t fencing .
docker run --rm -p 8000:8000 -v fencing-data:/data \
  -e DJANGO_DEBUG=false -e DJANGO_SECRET_KEY=test -e SQLITE_PATH=/data/db.sqlite3 \
  fencing
```

Open http://localhost:8000. Stop it with Ctrl+C, run it again, and the data is still there, because it lives in the `fencing-data` volume. (With debug off, cookies are marked secure. Chrome and Firefox still accept them on `localhost`, but Safari may not, so log in with one of those. Online it's HTTPS, so this doesn't come up.)

Then run the tests, commit, and push. Coolify deploys from GitHub, so it only sees what you've pushed:

```bash
python manage.py test
git add -A && git commit -m "Dockerfile for Coolify" && git push
```

Deploy from `main` once this branch is merged, or pick this branch in Step 8.

## Step 4: an Oracle Cloud server

1. Sign up at [cloud.oracle.com](https://cloud.oracle.com). It asks for a card but doesn't charge for Always Free resources. Pick a **home region** carefully: Always Free machines can only be made there, and you can't change it later. Singapore is the obvious choice.
2. **Compute → Instances → Create instance**:
    - **Image:** Canonical Ubuntu 24.04.
    - **Shape:** Ampere → `VM.Standard.A1.Flex`, 2 OCPUs and 12 GB RAM (the free tier allows up to 4 and 24 in total). It's an ARM machine. That's fine, because Coolify builds the image on the server itself.
    - **Networking:** create a new VCN with a public subnet, and assign a public IPv4 address.
    - **SSH keys:** **Generate a key pair** and download the private key.
    - **Boot volume:** the default (about 47 GB) is enough. Coolify wants 30 GB or more.
3. If it says **Out of capacity**, try another availability domain, or try again later. Upgrading the account to **Pay As You Go** usually fixes it, and Always Free resources stay free.
4. Copy the instance's **Public IP** and log in from your Mac:

    ```bash
    mv ~/Downloads/ssh-key-*.key ~/.ssh/oracle.key && chmod 600 ~/.ssh/oracle.key
    ssh -i ~/.ssh/oracle.key ubuntu@<public-ip>
    ```

    `chmod 600` matters: ssh refuses a key file that other users could read.

## Step 5: open the ports (both firewalls)

| Port | For |
| --- | --- |
| 22 | SSH (already open) |
| 80, 443 | The website, and Let's Encrypt |
| 8000 | The Coolify dashboard |
| 6001, 6002 | Coolify's live updates and in-browser terminal |

**In Oracle:** Instance → the subnet → its **Security List** → **Add Ingress Rules**: source `0.0.0.0/0`, TCP, destination ports `80,443,8000,6001,6002`.

**In Ubuntu**, over ssh:

```bash
for port in 80 443 8000 6001 6002; do
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport $port -j ACCEPT
done
sudo netfilter-persistent save
```

Oracle's Ubuntu image ends its `INPUT` rules with a REJECT-everything line. `-I INPUT 6` inserts your rule before it. Look with `sudo iptables -L INPUT --line-numbers`. `netfilter-persistent save` keeps the rules after a reboot.

## Step 6: install Coolify

Still over ssh:

```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash
```

It installs Docker and Coolify, and takes a few minutes. A script piped into `sudo bash` can do anything to the machine, so only do this with sources you trust. This one is Coolify's official installer.

**Then straight away** open `http://<public-ip>:8000` and create your admin account. The first person to visit that page becomes the admin, so don't leave it open to strangers. Choose **This Machine** (localhost) as the server when it asks: the app runs on the same box as Coolify.

## Step 7: a domain

Coolify offers a free address like `http://<random>.<public-ip>.sslip.io`. sslip.io is a DNS service that turns any name containing an IP into that IP. It's fine for trying things out. For the club, a real domain is better: at your registrar, add an **A record** (for example `fencing.yourdomain.com`) pointing at the public IP.

## Step 8: the app in Coolify

1. **Projects → + Add → New resource**:
    - Public repo: **Public Repository**, then paste `https://github.com/jorellesee/fencing-club-app`.
    - Private repo: **Private Repository (with GitHub App)**. Coolify walks you through making a GitHub App, which lets it read just that repo and get told about pushes.
2. Pick the branch. Set **Build Pack** to **Dockerfile**, and **Ports Exposes** to `8000`.
3. **Domains:** `https://fencing.yourdomain.com` (or the sslip.io one with `http` changed to `https`). The `https://` is what tells Coolify to get a certificate.
4. **Environment Variables:**

    ```
    DJANGO_DEBUG=false
    DJANGO_SECRET_KEY=<a fresh key, see below>
    SITE_HOST=fencing.yourdomain.com
    SQLITE_PATH=/data/db.sqlite3
    EMAIL_HOST=smtp.gmail.com
    EMAIL_HOST_USER=<your gmail>
    EMAIL_HOST_PASSWORD=<a gmail app password>
    DEFAULT_FROM_EMAIL=Fencing Club <your gmail>
    ```

    Make the key on your Mac with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`. `SITE_HOST` is the bare host, with no `https://`. `settings.py` adds it to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`, and builds invite links from it.
5. **Persistent Storage → + Add → Volume Mount:** destination path `/data`.
6. Click **Deploy** and watch the build log. When it's green, open your domain.
7. Make the first manager in the app's terminal (the **Terminal** tab in Coolify, or `docker exec -it <container> sh` over ssh):

    ```bash
    python manage.py createsuperuser
    ```

Turn on **Auto Deploy** (on by default with the GitHub App, or add a webhook) and every push to that branch redeploys.

## Step 9: bring your existing data across (optional)

Download `db.sqlite3` from PythonAnywhere's Files tab, then:

```bash
scp -i ~/.ssh/oracle.key db.sqlite3 ubuntu@<public-ip>:~
ssh -i ~/.ssh/oracle.key ubuntu@<public-ip>
docker ps                                   # find the app's container name
sudo docker cp ~/db.sqlite3 <container>:/data/db.sqlite3
```

Then click **Restart** in Coolify. The `CMD` runs `migrate` on startup, which applies migration `0012` (Lesson 27) to the old data.

## Step 10: backups

Nobody backs up the volume for you. Find where it lives on the server with `sudo docker volume ls` and `sudo docker volume inspect <name>` (look at `Mountpoint`). Then add a nightly copy with `sudo crontab -e`:

```
0 3 * * * sqlite3 /var/lib/docker/volumes/<name>/_data/db.sqlite3 ".backup /home/ubuntu/backups/db-$(date +\%F).sqlite3"
```

(Install `sqlite3` with `sudo apt install sqlite3` and make the folder with `mkdir ~/backups` first.) `.backup` makes a consistent copy even while the app is writing, which a plain `cp` doesn't promise. `%` has to be written `\%` in a crontab. Now and then, `scp` a backup back to your Mac, because a backup on the same machine doesn't help if the machine goes.

## Things to know

- **Idle machines get reclaimed.** Oracle may stop Always Free instances that sit nearly idle for a week. A Pay As You Go account isn't affected.
- **Updates are yours.** Run `sudo apt update && sudo apt upgrade` now and then. Coolify updates itself from its dashboard.
- **Once the dashboard has its own HTTPS domain** (Settings → Instance's domain), you can close port 8000 again in both firewalls.
- **Logs:** the app's **Logs** tab in Coolify shows gunicorn's output, including errors. That's why the `CMD` passes `--access-logfile -` and the image sets `PYTHONUNBUFFERED=1`.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `http://<ip>:8000` times out | A port closed in one of the two firewalls (Step 5) |
| Certificate errors, or the site only loads over HTTP | DNS not pointing at the IP yet, or port 80 closed, so Let's Encrypt can't check |
| `Bad Request (400)` | `SITE_HOST` doesn't match the domain exactly |
| `CSRF verification failed` on login | Same: `CSRF_TRUSTED_ORIGINS` comes from `SITE_HOST` |
| Data gone after a deploy | No volume at `/data`, or `SQLITE_PATH` not set |
| Build fails at `collectstatic` | A template points at a static file that doesn't exist. Run the same command locally to see which |
| `KeyError: 'DJANGO_SECRET_KEY'` | The variable isn't set in Coolify |

## Try it

1. Change some text in a template, push, and watch Coolify redeploy. Then check that your sessions are still there.
2. Run `sudo docker ps` on the server. Why is there a new container after each deploy, and why does your data survive?
3. Delete the `.dockerignore` line `db.sqlite3`, rebuild locally with `docker build`, and run `docker run --rm fencing ls -la /app`. What's in there that shouldn't be? Then put the line back.

---

# Check your understanding: questions and answers

<details>
<summary><b>Lesson 2</b></summary>

1. **What's the difference between `makemigrations` and `migrate`?** `makemigrations` compares your models to the existing migration files and writes a new migration file describing the change. `migrate` applies unapplied migration files to the database, creating or altering tables.
2. **Why does `capacity` need `null=True` but `notes` doesn't?** `capacity` is a number, and a number column can't hold an empty string, so "no capacity" must be stored as NULL. `notes` is text, so it can be left empty as `''`, and `blank=True` is enough.
3. **With `on_delete=models.PROTECT`, what would `junior.delete()` do?** It would raise `ProtectedError` and delete nothing, because attendance rows still point at the class.
4. **What does `related_name='attendance'` let you write?** It names the reverse link, so you can write `junior.attendance.all()` or `alex.attendance.all()` instead of `attendance_set`.

</details>

<details>
<summary><b>Lesson 3</b></summary>

1. **Why register a model before it appears in the admin?** The admin only shows models you explicitly register in `admin.py`, so you choose what managers can see and edit.
2. **What does an inline let you do?** Edit a class's attendance rows on the class's own page, all at once, without choosing the class for each row.
3. **Why did `autocomplete_fields` need `search_fields`?** The autocomplete box searches the linked model's admin, so that admin needs to know which fields to search.

</details>

<details>
<summary><b>Lesson 4</b></summary>

1. **What does a serializer do?** It converts model objects to JSON for responses, and converts incoming JSON back into validated data that can be saved.
2. **Why does dragging use PATCH, not PUT?** PATCH updates only the fields sent, and a drag only changes `start` and `end`. PUT replaces the whole row, so you'd have to send every field.
3. **Why `start__lt=end, end__gt=start`?** It finds classes that **overlap** the week, including ones that start before it or end after it. "Starts within the week" would miss a class running across midnight into Monday.
4. **What do `annotate(Count(...))` and `select_related` both solve?** The N+1 problem. They fetch the counts or linked rows in the same query, instead of one extra query per row.

</details>

<details>
<summary><b>Lesson 5</b></summary>

1. **Why a proxy instead of calling `http://localhost:8000/api/` directly?** The browser then sees one address. Requests carry the login cookie automatically, and there's no cross-origin (CORS) setup.
2. **What if `api.js` didn't send `X-CSRFToken`?** Django would reject every POST, PATCH and DELETE with *"CSRF token missing"*, and drags would revert.
3. **Why does the panel `load()` again after every change?** So the screen always shows what's really in the database, including server-side results like counts or rejected changes, instead of guessing.
4. **What does `info.revert()` protect against?** The calendar showing a change the database rejected or never received, such as a 400 error or Django being down.

</details>

<details>
<summary><b>Lesson 6</b></summary>

1. **Why `at(20, 17)` instead of `timezone.now()`?** Fixed dates give the same result every day. `now()` would make tests depend on when they run.
2. **How many members exist when `setUp` starts?** Zero. Tests use a separate, empty test database.
3. **What goes wrong without `refresh_from_db()`?** You'd check the old copy in Python memory, which still has the old times, so the test would fail or check nothing real.
4. **Why break the code on purpose?** To prove the test can actually fail. A test that never fails might not be testing anything.

</details>

<details>
<summary><b>Lesson 7</b></summary>

1. **Why real rows instead of FullCalendar drawing repeats?** Attendance needs a real `FencingClass` row to attach to. Real rows also let you move or delete a single week.
2. **What does `transaction.atomic()` protect against?** A half-finished series. If anything fails partway, every copy created so far is undone.
3. **Why `timezone.localdate(...)` rather than `.date()`?** Times are stored in UTC. An early-morning Singapore class falls on the previous day in UTC, so `.date()` could be off by a day.
4. **Why only repeat from the last class in a series?** Repeating from an earlier class would create copies for weeks that already exist, giving duplicates.

</details>

<details>
<summary><b>Lesson 8</b></summary>

1. **Why filter in Django instead of hiding classes in React?** The browser downloads only the classes it shows, and the filter works for anything that uses the API, not just this page.
2. **What does `detail=False` change?** The URL. The action lives at `/api/classes/coaches/` and works on the whole list, not on one class at `/api/classes/5/...`.
3. **Why does `coaches` need `order_by('coach')`?** The model's default ordering adds `start` to the query, and `.distinct()` would then keep one row per (coach, start) pair, repeating names.
4. **Why does choosing a coach refetch without calling `refresh()`?** The re-render creates a new `loadClasses`, and FullCalendar refetches whenever its `events` function changes.

</details>

<details>
<summary><b>Lesson 9</b></summary>

1. **Why doesn't an excused class lower the attendance rate?** The rate is present ÷ (present + absent). Excused and not-yet-marked rows are left out of both numbers.
2. **What does "unmarked" mean in database terms?** An attendance row whose status is still `enrolled` and whose class's `end` is in the past.
3. **Why was `'fencing_class'` added to `select_related`?** The serializer now reads the class's name and start for each row. Without the join, that's one extra query per row.
4. **What does `useParams()` return on `/members/7`?** `{ id: '7' }`. Note that it's a string.

</details>

<details>
<summary><b>Lesson 10</b></summary>

1. **Why does another member's profile give 404, not 403?** The member's queryset doesn't contain it, so DRF can't find it. That hides which IDs exist.
2. **What stops a coach from moving a class by PATCHing `start`?** `role_fields` only allows `notes` on classes, so `has_permission` refuses the request before anything is loaded.
3. **When does `has_object_permission` run?** When the view calls `get_object()`, i.e. for one specific row (retrieve, update, delete, or an action with `detail=True`). It never runs for `list`.
4. **Why are login and logout plain Django views?** So `CsrfViewMiddleware` checks them. DRF skips the CSRF check for logged-out requests.
5. **If React hides the delete button, why test the backend?** Anyone can send requests without the app. Only the backend's checks actually protect the data.

</details>

<details>
<summary><b>Lesson 11</b></summary>

1. **Why do the filters live in `App.jsx` instead of each page?** Switching pages unmounts the old page and loses its state. The common parent outlives both pages, so it keeps the filters.
2. **Why doesn't React send a filter for members?** The backend already limits members to their own classes, whatever is asked.
3. **Can a coach still read another coach's class through the API?** Yes. Only the views limit them to their own. Changing it is still refused.
4. **Why does the member's table make two requests?** Class rows carry counts for the whole class, not one member's status. That comes from their attendance rows.

</details>

<details>
<summary><b>Lesson 12</b></summary>

1. **Why didn't the backend need changing?** `ModelViewSet` already handles `POST` (create), and `RoleAccess` already allows it for managers only.
2. **Why `{ ...form, [key]: value }` rather than `form[key] = value`?** React only re-renders when state is replaced with a new object. Changing the old one in place wouldn't update the screen.
3. **What would `toISOString().slice(0, 10)` get wrong as the date input's value?** It gives the UTC date. For a Singapore class before 8am, that's the previous day.
4. **Where does "end must be after start" get checked?** In `FencingClassSerializer.validate`. React just shows the message it sends back.

</details>

<details>
<summary><b>Lesson 13</b></summary>

1. **Why does the app crash if `DJANGO_SECRET_KEY` is missing online?** The fallback key is in git. Running with it would let anyone forge session cookies, so failing loudly is safer.
2. **Why does reloading `/table` need the catch-all route?** Django has no `/table` URL. Only React Router knows it, so Django has to send `index.html` and let React pick the page.
3. **Why is `migrate` in the start command?** The disk holding the database isn't attached during the build, only while the service runs.
4. **What happens without the persistent disk?** Each deploy starts from fresh files, so `db.sqlite3` and all your data would be wiped.

</details>

<details>
<summary><b>Lesson 14</b></summary>

1. **Why doesn't changing a class's weapon rename it?** The name is stored text. *Generate* fills it in once; nothing recomputes it later.
2. **Why doesn't `update-following` copy start and end?** Each week's class needs a different date. Copying one time onto all of them would stack them on the same day.
3. **What does `.update()` skip, compared with saving each row?** It runs one SQL `UPDATE`, without loading the objects or calling `save()` on each one. That makes it fast, but any custom `save()` logic wouldn't run.
4. **Why `useState(() => initialForm(...))` instead of `useState(initialForm(...))`?** With a function, React only calls it on the first render. Otherwise it would rebuild the starting values on every render and throw them away.

</details>

<details>
<summary><b>Lesson 15</b></summary>

1. **Why does SQLite work on PythonAnywhere's free tier but not Render's?** PythonAnywhere's home folder is permanent. Render's free tier starts from fresh files on every deploy and restart, and only paid plans can attach a disk.
2. **Why set the variables in both the WSGI file and `postactivate`?** The web server only reads the WSGI file, and console commands like `migrate` and `collectstatic` only see the virtualenv. Both need the same settings, or the console works against development settings.
3. **Why is the WSGI file a safe place for the secret key?** It lives in `/var/www/` on PythonAnywhere, outside your repo, so it never gets committed.
4. **What would happen if `SITE_HOST` were missing?** `ALLOWED_HOSTS` would only contain `localhost` and `127.0.0.1`, so with debug off Django would answer every request with "Bad Request (400)".
5. **Why build React on your Mac?** `dist/` is gitignored, and the free tier's limited internet makes running `npm` there unreliable. Building locally and uploading the output is simpler.

</details>

<details>
<summary><b>Lesson 16</b></summary>

1. **Why create the user at invite time instead of when they accept?** The profile, role and member link are decided by the manager, so they're saved then. The person only adds a password. It also lets the Logins page show who's been invited.
2. **How does a link stop working after it's used, with no tokens in the database?** The token is built from the password hash. Setting the password changes the hash, so the rebuilt token no longer matches.
3. **Why does the reset page say the same thing for unknown emails?** Otherwise anyone could type in emails to find out who has a login at the club.
4. **Why count login attempts per username, not per IP address?** Behind PythonAnywhere's proxy, every visitor can look like the same address, so a per-address limit would lock everyone out at once.
5. **Why switch a login off instead of deleting it?** It can be switched back on, and the person keeps the same profile and email.

</details>

<details>
<summary><b>Lesson 27</b></summary>

1. **Why does `queries.sessions()` filter to confirmed sessions instead of each page doing it?** So that leaving requests out is the default. A page that forgets a filter shows less, not a request that looks booked.
2. **What would happen if you answered "no" when `makemigrations` asked whether FencingClass was renamed?** Django would delete the old table and create a new, empty one, losing every class and its attendance.
3. **Why does `RunPython` use `apps.get_model()` rather than importing the model?** The migration has to see the models as they were at that step. `LessonRequest` no longer exists in `models.py`, but it still exists at that point in the migration.
4. **Why is a pending lesson's member stored as an `Attendance` row rather than a `member` field?** It's how every session records who's on it, so rosters, busy times and "my sessions" all work the same way for lessons and group sessions.
5. **Why is "individual" worked out from capacity instead of stored in its own field?** A separate field could contradict capacity (an "individual" session with room for 8). Deriving it means there's only one fact to keep right.
6. **Why does `queries.py` need `Q(capacity=1)` when the model already has `is_individual`?** A property runs in Python on one object. Filtering a list happens in SQL, which can only use real columns.

</details>

---

# What's next

- **A `Coach` model:** pick coaches from a list instead of typing names. Coach logins would then link to it instead of matching `coach_name` text.
- **Overlap warnings** when two classes clash, using the same overlap rule.
- **Edit members** in the app, reusing `MemberForm` the way `ClassForm` now edits classes.
- **Rebuild the frontend in htmx:** done on the `htmx-frontend` branch (Lesson 22).
