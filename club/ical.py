"""Classes as an iCalendar (.ics) file, the format Google Calendar subscribes to.

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


def description(fencing_class):
    lines = []
    if fencing_class.coach:
        lines.append(f'Coach: {fencing_class.coach.name}')
    if fencing_class.weapon:
        lines.append(f'Weapon: {fencing_class.get_weapon_display()}')
    if fencing_class.notes:
        lines += ['', fencing_class.notes]
    return '\n'.join(lines)


def event(fencing_class, host, stamp):
    lines = [
        'BEGIN:VEVENT',
        # Stays the same when the class changes, so calendars update it in place.
        f'UID:class-{fencing_class.pk}@{host}',
        f'DTSTAMP:{stamp}',
        f'DTSTART:{utc(fencing_class.start)}',
        f'DTEND:{utc(fencing_class.end)}',
        f'SUMMARY:{escape(fencing_class.name)}',
    ]
    if fencing_class.location:
        lines.append(f'LOCATION:{escape(fencing_class.location)}')
    text = description(fencing_class)
    if text:
        lines.append(f'DESCRIPTION:{escape(text)}')
    lines.append('END:VEVENT')
    return lines


def calendar(name, classes, host):
    """The whole .ics file for `classes`, as text. `host` makes each event's UID
    unique to this club."""
    stamp = utc(timezone.now())
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Fencing Club//Classes//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{escape(name)}',
        # A hint to check hourly. Google ignores it and refreshes every few hours.
        'REFRESH-INTERVAL;VALUE=DURATION:PT1H',
        'X-PUBLISHED-TTL:PT1H',
    ]
    for fencing_class in classes:
        lines += event(fencing_class, host, stamp)
    lines.append('END:VCALENDAR')
    return ''.join(fold(line) + '\r\n' for line in lines)
