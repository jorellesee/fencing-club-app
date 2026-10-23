export const WEAPONS = { foil: 'Foil', epee: 'Épée', sabre: 'Sabre' }

export function formatDateTime(iso) {
  return new Date(iso).toLocaleString([], {
    weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

export function formatDate(iso) {
  return new Date(iso).toLocaleDateString([], { day: 'numeric', month: 'short', year: 'numeric' })
}

// Present out of present + absent. Excused and not-yet-marked classes don't count.
export function attendanceRate(member) {
  if (!member.marked_count) return null
  return Math.round((100 * member.present_count) / member.marked_count)
}

// Values for <input type="date"> and <input type="time">, in local time.
function pad(n) {
  return String(n).padStart(2, '0')
}

export function toDateInput(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function toTimeInput(date) {
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`
}
