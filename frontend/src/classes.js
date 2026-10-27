import { CLASS_WEAPONS } from './format'

export const NO_FILTERS = { coach: '', member: '', location: '', weapon: '' }

// Query string for the classes API. Managers pick filters; coaches only get
// their own classes. Members need nothing: the backend only returns theirs.
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

export function attendanceCount(fencingClass) {
  return `${fencingClass.present_count}/${fencingClass.capacity ?? fencingClass.member_count}`
}

// "Bukit Timah" -> "BT". A one-word location is kept whole: "Clementi".
export function locationCode(location) {
  const words = location.trim().split(/\s+/).filter(Boolean)
  if (words.length === 1) return words[0]
  return words.map((word) => word[0].toUpperCase()).join('')
}

// e.g. "Monday Sabre BT Class". Leaves out anything not filled in yet.
export function generateName({ date, weapon, location }) {
  const weekday = new Date(`${date}T00:00`).toLocaleDateString('en-US', { weekday: 'long' })
  return [weekday, CLASS_WEAPONS[weapon], location && locationCode(location), 'Class']
    .filter(Boolean)
    .join(' ')
}
