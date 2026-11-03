"""Sessions as an iCalendar (.ics) file, the format Google Calendar subscribes to.

Written by hand rather than with a library, since a feed only needs a few of
RFC 5545's rules: escape the text, write times in UTC, fold long lines and end
every line with CRLF.
"""
from datetime import timezone as dt_timezone

from django.utils import timezone


def escape(text):
    """Backslashes first, so the ones added for , ; and newlines aren't doubled."""
    text = text.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
    return text.replace('\r\n', '\\n').replace('\r', '\\n').replace('\n', '\\n')


def fold(line, limit=75):
    """Splits a line longer than `limit` bytes, each continuation starting with a
    space. Counts UTF-8 bytes, as the RFC does, without splitting a character."""
    parts, current, size = [], '', 0
    for char in line:
        width = len(char.encode())
        if size + width > limit:
            parts.append(current)
            current, size = ' ', 1
        current += char
        size += width
    parts.append(current)
    return '\r\n'.join(parts)


def utc(moment):
    """e.g. 20261106T020000Z. UTC needs no time zone definitions in the file."""
    return moment.astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def description(session):
    lines = []
    if session.category != session.Category.FENCING:
        lines.append(session.get_category_display())
    if session.coach:
        lines.append(f'Coach: {session.coach.name}')
    if session.weapon:
        lines.append(f'Weapon: {session.get_weapon_display()}')
    if session.notes:
        lines += ['', session.notes]
    return '\n'.join(lines)


def event(session, host, stamp):
    lines = [
        'BEGIN:VEVENT',
        # Stays the same when the session changes, so calendars update it in place.
        # Still "class-": sessions kept their ids from when they were classes, and a
        # new UID would make every calendar delete each event and add it again.
        f'UID:class-{session.pk}@{host}',
        f'DTSTAMP:{stamp}',
        f'DTSTART:{utc(session.start)}',
        f'DTEND:{utc(session.end)}',
        f'SUMMARY:{escape(session.name)}',
    ]
    if session.location:
        lines.append(f'LOCATION:{escape(session.location)}')
    text = description(session)
    if text:
        lines.append(f'DESCRIPTION:{escape(text)}')
    lines.append('END:VEVENT')
    return lines


def calendar(name, sessions, host):
    """The whole .ics file for `sessions`, as text. `host` makes each event's UID
    unique to this club."""
    stamp = utc(timezone.now())
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Fencing Club//Sessions//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{escape(name)}',
        # A hint to check hourly. Google ignores it and refreshes every few hours.
        'REFRESH-INTERVAL;VALUE=DURATION:PT1H',
        'X-PUBLISHED-TTL:PT1H',
    ]
    for session in sessions:
        lines += event(session, host, stamp)
    lines.append('END:VCALENDAR')
    return ''.join(fold(line) + '\r\n' for line in lines)
