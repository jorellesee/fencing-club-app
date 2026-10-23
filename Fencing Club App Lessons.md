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

---

# What's next

- **A `Coach` model:** pick coaches from a list instead of typing names.
- **Edit a whole series:** "change the coach for all following classes".
- **Overlap warnings** when two classes clash, using the same overlap rule.
- **Edit forms:** reuse `ClassForm` and `MemberForm` to edit existing classes and members.
- **Rebuild the frontend in htmx:** the Django models, admin and much of the API carry over.
