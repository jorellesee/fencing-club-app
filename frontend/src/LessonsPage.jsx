import { useEffect, useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import classicThemePlugin from '@fullcalendar/react/themes/classic'
import timeGridPlugin from '@fullcalendar/react/timegrid'
import interactionPlugin from '@fullcalendar/react/interaction'
import { api } from './api'
import { formatDateTime, toDateInput, toTimeInput } from './format'
import FormErrors from './FormErrors'
import { LessonStatus } from './LessonRequestPanel'
import Modal from './Modal'

// Busy slots say nothing about what the coach is doing. The member's own
// requests show in full, coloured by status.
const BUSY = { title: 'Busy', color: 'var(--tag-gray-bg)', contrastColor: 'var(--tag-gray-text)' }
const OWN = {
  pending: { title: 'Requested', color: 'var(--tag-yellow-bg)', contrastColor: 'var(--tag-yellow-text)' },
  accepted: { title: 'Your lesson', color: 'var(--tag-green-bg)', contrastColor: 'var(--tag-green-text)' },
}

export default function LessonsPage() {
  const calendarRef = useRef(null)
  const [coaches, setCoaches] = useState(null)
  const [coach, setCoach] = useState('')
  const [lessons, setLessons] = useState([])
  const [slot, setSlot] = useState(null)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    api('lesson-requests/coaches/')
      .then((list) => {
        setCoaches(list)
        if (list.length > 0) setCoach(String(list[0].id))
      })
      .catch(setError)
    api('lesson-requests/').then(setLessons).catch(setError)
  }, [])

  async function loadEvents(info) {
    if (!coach) return []
    const params = new URLSearchParams({
      coach, start: info.start.toISOString(), end: info.end.toISOString(),
    })
    const busy = await api(`lesson-requests/busy/?${params}`)
    const own = lessons.filter((l) => String(l.coach) === coach && OWN[l.status])
    return [
      ...busy.map((b) => ({ ...BUSY, start: b.start, end: b.end })),
      ...own.map((l) => ({ ...OWN[l.status], start: l.start, end: l.end })),
    ]
  }

  async function refresh(message) {
    setNotice(message)
    setLessons(await api('lesson-requests/'))
  }

  // Refetch when the member's own requests change, since they're drawn too.
  useEffect(() => {
    calendarRef.current?.getApi().refetchEvents()
  }, [lessons])

  async function cancel(lesson) {
    setError(null)
    try {
      await api(`lesson-requests/${lesson.id}/cancel/`, { method: 'POST' })
      refresh(`Cancelled your lesson on ${formatDateTime(lesson.start)}.`)
    } catch (err) {
      setError(err)
    }
  }

  const coachName = coaches?.find((c) => String(c.id) === coach)?.name
  const now = new Date()
  const current = lessons.filter((l) => new Date(l.end) >= now)

  return (
    <div className="page page-wide">
      <h1 className="page-title">
        <span className="page-icon">🎯</span>Private lessons
      </h1>
      <p className="page-description">
        Pick a coach, then drag across a free time to ask for a lesson. Grey times are when
        they’re already booked. Your coach accepts or declines.
      </p>
      {notice && <p className="notice">{notice}</p>}
      <FormErrors error={error} />
      {coaches?.length === 0 && (
        <p className="empty">
          You can ask your primary coach, or the coach of a class you’re on. Ask a manager to
          set your primary coach.
        </p>
      )}
      {coaches?.length > 0 && (
        <>
          <div className="toolbar">
            <select className="filter" value={coach} onChange={(e) => setCoach(e.target.value)}>
              {coaches.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <span />
          </div>
          <div className="lesson-calendar">
            <FullCalendar
              key={coach}
              ref={calendarRef}
              plugins={[classicThemePlugin, timeGridPlugin, interactionPlugin]}
              initialView="timeGridWeek"
              headerToolbar={{ start: 'prev,next today', center: 'title', end: '' }}
              height="100%"
              slotMinTime="08:00"
              slotMaxTime="22:00"
              expandRows
              allDaySlot={false}
              events={loadEvents}
              selectable
              selectOverlap={false}
              selectAllow={(info) => info.start > new Date()}
              select={(info) => {
                calendarRef.current.getApi().unselect()
                setSlot({ start: info.start, end: info.end })
              }}
            />
          </div>
        </>
      )}

      <h2 className="section-title">My requests</h2>
      {current.length === 0 ? (
        <p className="empty">No upcoming lessons or requests.</p>
      ) : (
        <table className="table database">
          <thead>
            <tr>
              <th>When</th>
              <th>Coach</th>
              <th>Note</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {current.map((lesson) => (
              <tr key={lesson.id}>
                <td className="muted">{formatDateTime(lesson.start)}</td>
                <td>{lesson.coach_name}</td>
                <td className="muted">{lesson.note}</td>
                <td><LessonStatus status={lesson.status} /></td>
                <td className="row-actions">
                  {(lesson.status === 'pending' || lesson.status === 'accepted') && (
                    <button className="button" onClick={() => cancel(lesson)}>Cancel</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {slot && (
        <RequestForm
          coach={coach}
          coachName={coachName}
          slot={slot}
          onSaved={(lesson) => {
            setSlot(null)
            refresh(`Asked ${coachName} for ${formatDateTime(lesson.start)}. It’s pending until they reply.`)
          }}
          onClose={() => setSlot(null)}
        />
      )}
    </div>
  )
}

function RequestForm({ coach, coachName, slot, onSaved, onClose }) {
  const [form, setForm] = useState({
    date: toDateInput(slot.start),
    startTime: toTimeInput(slot.start),
    endTime: toTimeInput(slot.end),
    note: '',
  })
  const [error, setError] = useState(null)

  function set(key) {
    return (event) => setForm({ ...form, [key]: event.target.value })
  }

  async function submit(event) {
    event.preventDefault()
    try {
      onSaved(await api('lesson-requests/', {
        method: 'POST',
        body: {
          coach: Number(coach),
          start: new Date(`${form.date}T${form.startTime}`).toISOString(),
          end: new Date(`${form.date}T${form.endTime}`).toISOString(),
          note: form.note,
        },
      }))
    } catch (err) {
      setError(err)
    }
  }

  return (
    <Modal title={`Ask ${coachName} for a lesson`} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <div className="form-row">
          <label>
            Date
            <input type="date" value={form.date} onChange={set('date')} required />
          </label>
          <label>
            Start
            <input type="time" value={form.startTime} onChange={set('startTime')} required />
          </label>
          <label>
            End
            <input type="time" value={form.endTime} onChange={set('endTime')} required />
          </label>
        </div>
        <label>
          Note for the coach
          <textarea value={form.note} onChange={set('note')} placeholder="e.g. Want to work on my parry riposte" />
        </label>
        <FormErrors error={error} />
        <div className="form-actions">
          <button type="button" className="button" onClick={onClose}>Cancel</button>
          <button className="button primary">Send request</button>
        </div>
      </form>
    </Modal>
  )
}
