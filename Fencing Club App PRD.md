# Fencing Club App PRD

Oct 20, 2026 · Updated Oct 30, 2026 · @Jorelle

## Overview

A web app for running a fencing club's training sessions and attendance. A session is anything on the club's timetable: a group fencing class, a private lesson, or physical conditioning. The main screen is a calendar of sessions. Managers run everything; coaches and members log in to see their own sessions.

**Roles**

- **Manager:** a staff login. Can do everything
- **Coach:** sees their own sessions, marks attendance and writes notes for them, and answers private lesson requests
- **Member:** sees their own sessions, books upcoming ones, asks their coaches for private lessons, and edits their own profile

**In scope:** members, coaches, sessions, weekly repeating sessions, attendance, bookings, private lessons, logins with email invites, calendar sync to Google Calendar, and the calendar and list views on a computer or a phone.

**Out of scope for now:** payments, announcements, competitions, waitlists, and reminder notifications.

**Built with:** Django, with pages made from Django templates. htmx swaps parts of a page without reloading it, Alpine.js holds small bits of browser state, and FullCalendar draws the calendars. Data is stored in SQLite.

## Main screens

The sidebar shows only the screens a role can use. On a phone it becomes a tab bar along the bottom.

| Screen | Manager | Coach | Member |
| --- | --- | --- | --- |
| Sessions (calendar and list) | "Sessions" | "My sessions" | "My sessions" |
| Book a session | | | Yes |
| Private lessons | | | Yes |
| My profile | | | Yes |
| Members | Yes | | |
| Coaches | Yes | | |
| Calendar sync | Yes | Yes | Yes |

### Sessions: calendar

A weekly calendar from 8am to 10pm. Managers see every session, coaches see the sessions they coach, and members see the sessions they're on.

- Sessions show as blocks with name, time, and headcount: present out of capacity (for example 3/12), or out of the number enrolled if there's no capacity
- Switch between month, week, and day view. On a phone it shows three days at a time
- Month view lists each day's sessions by start time. A busy day shows the first few and a "+N more" link. Clicking a day opens it in day view
- Click a session to open a side panel with its details, notes, and attendance list
- Unconfirmed private lessons show as dashed yellow blocks. Clicking one opens the request
- **Managers only:**
  - Drag across empty time (press and hold on a phone) to create a session at that time
  - Drag a session to move it, or drag its edge to change its length. The change saves straight away
  - Filter by coach, member, location, category, and weapon. The filters are kept in the URL and carry over to the list view

### Sessions: list

The same sessions as a table, split into upcoming and past, with the same filters. Members also see their own status for each session.

### Session side panel

- Shows the session's time, weapon, coach, location, notes, and attendance list with a present count
- **Managers** can edit the session, add any active member to it, remove a member, repeat it weekly, and delete it (or it and the rest of its series)
- **Managers, and coaches on their own sessions,** can change each member's status and edit the notes. Notes save when you click away
- **Members** see only their own row. They can enrol in an upcoming session, or cancel an enrolment that hasn't been marked yet

### Session form (managers)

A dialog for a new session or editing one: name, date, start and end time, category, type, weapon, location, coach, capacity, and notes.

- A new session defaults to an hour starting at the next full hour, or to the time dragged across on the calendar
- **Generate** suggests a name from what's filled in, for example "Monday Sabre BT Class", or "Friday BT Conditioning" for conditioning. Locations of more than one word are shortened to initials
- Location suggests the locations used before
- Only active coaches can be chosen, except a session keeps its current coach even if they've been made inactive

### Book a session (members)

A list of upcoming group sessions the member isn't on yet, with the spots left in each. A member can book a session if their membership is active, the session hasn't started, and it isn't full. Private lessons are never listed.

### Private lessons (members)

A member asks one of their coaches for a one-to-one lesson.

1. Pick a coach. The choices are the member's primary coach and the coaches of any session they're on
2. The coach's week shows. Times when the coach is busy are grey, without saying what they are. The member's own requests and lessons show in full
3. Drag across a free time (press and hold on a phone) and add an optional note for the coach
4. The request is saved as an unconfirmed individual session (capacity 1) with the member enrolled. It stays unconfirmed until the coach or a manager answers it from the calendar
5. Accepting it confirms the session. It then shows on calendars and in calendar feeds, and attendance can be marked like any other session
6. Declining it deletes it
7. The member can cancel an unconfirmed or confirmed lesson before it starts, which deletes it

Rules for a request:

- It must be in the future, end after it starts, and last at most 3 hours
- It can't overlap any of the coach's sessions, confirmed or not
- Only active members can request lessons

"My requests" on the same page lists the member's upcoming lessons and their status: unconfirmed or confirmed.

### My profile (members)

The member's details, attendance record, and session history. They can change their name, phone, and weapon. Their email can't be changed here because it's also their login.

### Members (managers)

- A list of members with their weapon, primary coach, last attended session, and whether they're active
- Clicking a member opens a side panel with their details, their attendance rate (present out of present plus absent, for example 9 of 12), their session history with editable statuses, and their login
- Add or edit a member: name, email, phone, weapon, primary coach, and active

### Coaches (managers)

- A list of coaches with their session count and next session
- Clicking a coach opens a side panel with their details, their members (those with them as primary coach), their next five and last five sessions, and their login
- Add or edit a coach: name, email, phone, weapon, and active

### Logins (managers)

On a member's or coach's side panel, the Login row shows whether they're not invited yet, invited, active, or switched off.

- **Invite** creates a login and emails them a link to choose a password. The person needs an email address first
- **Resend invite** sends a new link and makes older ones stop working
- **Switch off** stops them logging in. They can be switched back on

### Calendar sync (everyone)

Each person gets a secret link to an `.ics` calendar feed, which Google Calendar (or any calendar app) can subscribe to with "From URL". Managers' feeds show every session. Everyone else's feed shows what their calendar shows.

- The feed covers sessions from two months ago onwards and includes each session's coach, weapon, location, and notes
- Google refreshes subscribed calendars every few hours, so changes take a while to appear there
- The feed is read-only. Changes are made in the app
- **Reset link** makes a new link and stops the old one working, for example if it was shared by mistake
- A switched-off login's feed stops working

### Logging in

- Log in with an email address or username and password
- **Forgot password** emails a link to choose a new one. The page shows the same message whether or not the email has a login, so it can't be used to find out who has one
- Invite and reset links work once and expire after 7 days
- Login and reset attempts are rate limited: 10 logins per username, and 3 reset emails per address, every 15 minutes
- Emails print to the terminal locally and go out over SMTP when `EMAIL_HOST` is set

## Data

### Members

| Field | Type | Notes |
| --- | --- | --- |
| id | ID | |
| name | Text | Required |
| email | Text | Optional. Needed to invite them |
| phone | Text | Optional |
| weapon | Choice | Foil, épée, or sabre |
| active | Yes/No | Inactive members can't book or request lessons, and can't be added to sessions |
| primary_coach | Link to Coaches | Optional |

### Coaches

| Field | Type | Notes |
| --- | --- | --- |
| id | ID | |
| name | Text | Required, unique |
| email | Text | Optional. Needed to invite them |
| phone | Text | Optional |
| weapon | Choice | Foil, épée, or sabre |
| active | Yes/No | Inactive coaches can't be chosen for new sessions or asked for lessons |

Deleting a coach leaves their sessions and members without a coach.

### Training sessions

| Field | Type | Notes |
| --- | --- | --- |
| id | ID | |
| name | Text | For example "Junior Foil" |
| start | Date and time | |
| end | Date and time | Must be after start |
| coach | Link to Coaches | Optional |
| location | Text | Optional |
| category | Choice | Fencing or physical conditioning. Defaults to fencing |
| type | Choice | Group or individual. Defaults to group. Only group sessions can be booked |
| status | Choice | Confirmed or unconfirmed. Defaults to confirmed. Only private lesson requests are unconfirmed, and they're left out of the calendar, list, feeds, bookings, histories, and counts until confirmed |
| weapon | Choice | Foil, épée, sabre, or mixed. Usually empty for conditioning |
| capacity | Number | Optional. Bookings stop when it's reached |
| notes | Text | Optional |
| series | ID | Set on sessions that repeat weekly, linking them together |

### Attendance

One row per member per session.

| Field | Type | Notes |
| --- | --- | --- |
| id | ID | |
| session_id | Link to Training sessions | |
| member_id | Link to Members | |
| status | Choice | Enrolled, present, absent, or excused |

A member can appear only once per session. A booking creates an "enrolled" row, which becomes present, absent, or excused once marked. Deleting a session deletes its attendance rows.

### Logins

Each coach or member login is a Django user with a profile that gives it a role and links it to one coach or one member. Managers are staff users and have no profile.

- The username is the person's email address
- A login is "invited" until its password is set, then "active", or "switched off" if a manager turns it off

### Calendar feeds

One per login: a random secret token that forms the feed's URL. Resetting it replaces the token.

## Repeating sessions

- From a session's side panel, a manager repeats it weekly until a chosen date, for at most one year. Copies keep the session's details and its member list
- Repeating must start from the last session in a series
- When editing a session in a series, the manager can also apply the name, category, type, weapon, location, coach, and capacity to all following sessions. Times and notes stay per session
- "Delete this and following" removes the session and every later session in the series

## Permissions

| Action | Manager | Coach | Member |
| --- | --- | --- | --- |
| See sessions on the calendar and list | All, with filters | Own | Own |
| Open a session's panel | All | All | Own, and upcoming ones they could book |
| Add, move, edit, repeat, delete sessions | Yes | No | No |
| Add or remove members on a session | Yes | No | No |
| Mark attendance and edit notes | Yes | Own sessions | No |
| Book or cancel a session | No | No | Self |
| Request or cancel a private lesson | No | No | Self |
| Accept or decline a lesson request | Yes | Requests to them | No |
| See and edit members | Yes | No | Self: name, phone, and weapon |
| See and edit coaches | Yes | No | No |
| Manage logins | Yes | No | No |
| Calendar sync | All sessions | Own sessions | Own sessions |

Managers can also use Django's admin site at `/admin/`.

## User stories

As a manager, I can:

1. **See the week or month.** Open the app and see this week's sessions on a calendar, switch to a month or a single day, and move to other weeks or months
2. **Add a session.** Drag across an empty slot to create a session at that time, and fill in its name, category, type, coach, location, weapon, and capacity, or generate a name
3. **Reschedule a session.** Drag a session to a new day or time, or resize it, and the change saves
4. **Edit or delete a session.** Change a session's details from the side panel, or delete it, optionally along with the rest of its series
5. **Repeat a session.** Repeat a session weekly until a date, and change or delete the rest of the series in one go
6. **Take attendance.** Open a session, add members, and mark each one enrolled, present, absent, or excused
7. **Manage members.** Add, edit, and deactivate members, assign a primary coach, and see each member's attendance record and history
8. **Manage coaches.** Add, edit, and deactivate coaches and see their members and their upcoming and past sessions
9. **Invite people.** Send a coach or member a login invite by email, resend it, or switch the login off and on
10. **Filter the schedule.** Narrow the calendar or list to one coach, member, location, category, or weapon
11. **Answer lesson requests.** Accept or decline any private lesson request from the calendar
12. **Sync my calendar.** See every session in Google Calendar

As a coach, I can:

1. **See my sessions.** See the sessions I coach on the calendar and list
2. **Take attendance.** Mark attendance for my own sessions and add notes to them
3. **Answer lesson requests.** See requests for lessons with me on my calendar, and accept or decline them
4. **Sync my calendar.** See my sessions in Google Calendar

As a member, I can:

1. **See my sessions.** See the sessions I'm on, past and upcoming, and my status in each
2. **Book a session.** Book an upcoming session that has space, and cancel a booking before it starts and is marked
3. **Ask for a private lesson.** Pick one of my coaches, see when they're free, and request a lesson, then cancel it if plans change
4. **Edit my profile.** Update my name, phone, and weapon, and see my attendance record
5. **Sync my calendar.** See my sessions in Google Calendar

## Open questions

- Should managers get a reminder about past sessions whose attendance hasn't been marked?
- Should members be able to cancel closer to the start, or should there be a cut-off (for example 24 hours before)?
- Should full sessions have a waitlist?
- Should the calendar warn when two sessions overlap, or when a coach is double-booked? Lesson requests already check the coach's time, but sessions don't
- Should coaches be able to add or remove members from their own sessions?
- Should coaches and members be emailed when a lesson request is made, accepted, or declined? Today they only see it in the app
