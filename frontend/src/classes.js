export const NO_FILTERS = { coach: '', member: '', location: '' }

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
