# Fencing Club App PRD

Oct 20, 2026 · @Jorelle

## Overview

A manager-only web app for running a fencing club's class schedule and attendance. The main screen is a calendar of classes. The manager can drag classes to reschedule them and take attendance for the selected class.

**In scope:** members, classes, attendance, and the calendar screen.

**Out of scope for now:** member and coach logins, payments, announcements, competitions, recurring classes, and notifications.

## Main screen

A weekly calendar built with React FullCalendar.

- Classes show as blocks with name, time, and headcount (for example 8/12)
- Drag a class to move it, or drag its edge to change its length. The change saves straight away
- Click a class to open a side panel with its details and an attendance list
- Switch between week and day view

## Data

### Members

| Field | Type | Notes |
| --- | --- | --- |
| id | ID | |
| name | Text | Required |
| email | Text | Optional |
| phone | Text | Optional |
| weapon | Choice | Foil, épée, or sabre |
| active | Yes/No | Inactive members are hidden from attendance lists |

### Classes

| Field | Type | Notes |
| --- | --- | --- |
| id | ID | |
| name | Text | For example "Junior Foil" |
| start | Date and time | |
| end | Date and time | Must be after start |
| coach | Text | Coach name. No coach accounts yet |
| capacity | Number | Optional |
| notes | Text | Optional |

### Attendance

One row per member per class.

| Field | Type | Notes |
| --- | --- | --- |
| id | ID | |
| class_id | Link to Classes | |
| member_id | Link to Members | |
| status | Choice | Present or absent |

A member can appear only once per class. Deleting a class deletes its attendance rows.

## User stories

As a manager, I can:

1. **See the week.** Open the app and see this week's classes on a calendar, then move to other weeks
2. **Add a class.** Click an empty slot to create a class at that time, and fill in its name, coach, and capacity
3. **Reschedule a class.** Drag a class to a new day or time, or resize it, and the change saves
4. **Edit or delete a class.** Change a class's details from the side panel, or delete it
5. **Take attendance.** Select a class and mark each member present or absent from a searchable member list
6. **Manage members.** Add, edit, and deactivate members from a simple members list

## Open questions

- Should attendance list every active member, or only members added to that class?
- Do we need recurring weekly classes soon, or is creating each class by hand fine to start?
- Should the calendar warn when two classes overlap?
