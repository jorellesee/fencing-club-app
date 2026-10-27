# Fencing Club App PRD

Oct 20, 2026 · Updated Oct 27, 2026 · @Jorelle

## Overview

A web app for running a fencing club's class schedule and attendance. The main screen is a calendar of classes. Managers run everything; coaches and members log in to see their own classes.

**Roles**

- **Manager:** a staff login. Can do everything
- **Coach:** sees the full schedule and marks attendance for their own classes
- **Member:** sees their own classes, books upcoming ones, and edits their own profile

**In scope:** members, coaches, classes, weekly repeating classes, attendance, bookings, logins with email invites, and the calendar and table views.

**Out of scope for now:** payments, announcements, competitions, waitlists, and reminder notifications.

## Main screens

### Calendar

A weekly calendar built with React FullCalendar. Members see "My calendar" with only their own classes.

- Classes show as blocks with name, time, and headcount (for example 8/12)
- Managers can drag a class to move it, or drag its edge to change its length. The change saves straight away
- Click a class to open a side panel with its details and attendance list
- Switch between week and day view
- Filter by coach, member, location, and weapon. Filters are shared with the table view

### Classes table

The same classes as a list ("All classes" for managers, "My classes" for others), with the same filters.

### Book a class (members)

Upcoming classes the member isn't on yet. A member can book a class if their membership is active, the class hasn't started, and it isn't full. They can cancel an upcoming booking that hasn't been marked yet.

### Members, Coaches, and Logins (managers)

- **Members:** a list with each member's last attended class, and a page per member with their attendance record (for example 9 of 12 classes) and class history
- **Coaches:** a list with each coach's class count and next class, and a page per coach with upcoming and past classes
- **Logins:** invite a coach or member by email, resend an invite, or switch a login off

## Data

### Members

| Field | Type | Notes |
| --- | --- | --- |
| id | ID | |
| name | Text | Required |
| email | Text | Optional |
| phone | Text | Optional |
| weapon | Choice | Foil, épée, or sabre |
| active | Yes/No | Inactive members can't book and are hidden from attendance lists |
| primary_coach | Link to Coaches | Optional |

### Coaches

| Field | Type | Notes |
| --- | --- | --- |
| id | ID | |
| name | Text | Required, unique |
| email | Text | Optional |
| phone | Text | Optional |
| weapon | Choice | Foil, épée, or sabre |
| active | Yes/No | |

Deleting a coach leaves their classes and members without a coach.

### Classes

| Field | Type | Notes |
| --- | --- | --- |
| id | ID | |
| name | Text | For example "Junior Foil" |
| start | Date and time | |
| end | Date and time | Must be after start |
| coach | Link to Coaches | Optional |
| location | Text | Optional |
| weapon | Choice | Foil, épée, sabre, or mixed |
| capacity | Number | Optional. Bookings stop when it's reached |
| notes | Text | Optional |
| series | ID | Set on classes that repeat weekly, linking them together |

### Attendance

One row per member per class.

| Field | Type | Notes |
| --- | --- | --- |
| id | ID | |
| class_id | Link to Classes | |
| member_id | Link to Members | |
| status | Choice | Enrolled, present, absent, or excused |

A member can appear only once per class. A booking creates an "enrolled" row, which becomes present, absent, or excused once marked. Deleting a class deletes its attendance rows.

### Logins

Each coach or member login is a Django user with a profile that gives it a role and links it to one coach or one member. Managers are staff users and have no profile.

- The username is the person's email address
- An invite email links to a page where they choose a password. Resending an invite makes older links stop working
- Anyone can ask for a password reset email. The reply is the same whether or not the email has a login
- Login and reset attempts are rate limited
- Emails print to the terminal locally and go out over SMTP when `EMAIL_HOST` is set

## Repeating classes

- From a class's side panel, a manager repeats it weekly until a chosen date, for at most one year. Copies keep the class's details and its member list
- Repeating must start from the last class in a series
- When editing a class in a series, the manager can also apply the name, weapon, location, coach, and capacity to all following classes. Times and notes stay per class
- "Delete this and following" removes the class and every later class in the series

## Permissions

| Action | Manager | Coach | Member |
| --- | --- | --- | --- |
| See classes | All | All | Own and upcoming |
| Add, move, edit, delete classes | Yes | Notes on own classes | No |
| Mark attendance | Yes | Own classes | No |
| Book or cancel a class | No | No | Self |
| See members | Yes | Yes | Self |
| Edit members | Yes | No | Own name, phone, and weapon |
| Manage coaches | Yes | View only | No |
| Manage logins | Yes | No | No |

## User stories

As a manager, I can:

1. **See the week.** Open the app and see this week's classes on a calendar, then move to other weeks
2. **Add a class.** Click an empty slot to create a class at that time, and fill in its name, coach, location, weapon, and capacity
3. **Reschedule a class.** Drag a class to a new day or time, or resize it, and the change saves
4. **Edit or delete a class.** Change a class's details from the side panel, or delete it, optionally along with the rest of its series
5. **Repeat a class.** Repeat a class weekly until a date, and change or delete the rest of the series in one go
6. **Take attendance.** Select a class and mark each member enrolled, present, absent, or excused
7. **Manage members.** Add, edit, and deactivate members, assign a primary coach, and see each member's attendance record
8. **Manage coaches.** Add, edit, and deactivate coaches and see their upcoming and past classes
9. **Invite people.** Send a coach or member a login invite by email, resend it, or switch the login off
10. **Filter the schedule.** Narrow the calendar or table to one coach, member, location, or weapon

As a coach, I can:

1. **See the schedule.** See every class on the calendar and table
2. **Take attendance.** Mark attendance for my own classes and add notes to them

As a member, I can:

1. **See my classes.** See the classes I'm on, past and upcoming
2. **Book a class.** Book an upcoming class that has space, and cancel a booking before it starts
3. **Edit my profile.** Update my name, phone, and weapon, and see my attendance record

## Open questions

- The backend can list past classes with unmarked attendance (`attendance/unmarked/`), but the page for it was removed. Should it come back, perhaps as a reminder on the calendar?
- Should members be able to cancel closer to the start, or should there be a cut-off (for example 24 hours before)?
- Should full classes have a waitlist?
- Should the calendar warn when two classes overlap, or when a coach is double-booked?
- Should coaches be able to add or remove members from their own classes?
