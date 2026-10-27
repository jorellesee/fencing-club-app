import { useState } from 'react'
import { api } from './api'
import { useMe } from './auth'
import { formatDateTime } from './format'
import FormErrors from './FormErrors'

const LESSON_STATUS = {
  pending: 'Pending', accepted: 'Accepted', declined: 'Declined', cancelled: 'Cancelled',
}
const STATUS_CLASSES = {
  pending: 'status-excused', accepted: 'status-present', declined: 'status-absent', cancelled: 'status-enrolled',
}

export function LessonStatus({ status }) {
  return <span className={`tag ${STATUS_CLASSES[status]}`}>{LESSON_STATUS[status]}</span>
}

// A pending lesson request, opened from the calendar. The coach or a manager
// answers it; the member who asked can cancel it. `onAccepted` gets the new class's id.
export default function LessonRequestPanel({ lesson, onChange, onAccepted, onClose }) {
  const me = useMe()
  const [error, setError] = useState(null)

  async function run(verb) {
    setError(null)
    try {
      const updated = await api(`lesson-requests/${lesson.id}/${verb}/`, { method: 'POST' })
      onChange()
      if (verb === 'accept') onAccepted(String(updated.fencing_class))
      else onClose()
    } catch (err) {
      setError(err)
    }
  }

  return (
    <aside className="panel">
      <button className="close" onClick={onClose} aria-label="Close">×</button>
      <h2>Lesson request</h2>
      <p className="meta">
        {formatDateTime(lesson.start)} – {new Date(lesson.end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </p>
      <dl className="properties">
        <dt>Member</dt>
        <dd>{lesson.member_name}</dd>
        <dt>Coach</dt>
        <dd>{lesson.coach_name}</dd>
        <dt>Status</dt>
        <dd><LessonStatus status={lesson.status} /></dd>
      </dl>
      <h3>Note</h3>
      <p className="meta">{lesson.note || 'No note.'}</p>
      <FormErrors error={error} />
      <div className="row-actions panel-actions">
        {me.role === 'member' ? (
          <button className="button" onClick={() => run('cancel')}>Cancel request</button>
        ) : (
          <>
            <button className="button" onClick={() => run('decline')}>Decline</button>
            <button className="button primary" onClick={() => run('accept')}>Accept</button>
          </>
        )}
      </div>
      {me.role !== 'member' && (
        <p className="meta">Accepting puts it on the calendar as a one-person class.</p>
      )}
    </aside>
  )
}
