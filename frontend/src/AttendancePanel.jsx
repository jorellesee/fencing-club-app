import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api } from './api'
import { canEdit, useMe } from './auth'
import ClassForm from './ClassForm'
import { CLASS_WEAPONS } from './format'
import StatusSelect from './StatusSelect'

function formatTime(iso) {
  return new Date(iso).toLocaleString([], {
    weekday: 'short', hour: '2-digit', minute: '2-digit',
  })
}

export default function AttendancePanel({ classId, onChange, onClose }) {
  const me = useMe()
  const isManager = me.role === 'manager'
  const [fencingClass, setFencingClass] = useState(null)
  const [rows, setRows] = useState([])
  const [members, setMembers] = useState([])
  const [until, setUntil] = useState('')
  const [message, setMessage] = useState('')
  const [notes, setNotes] = useState('')
  const [editing, setEditing] = useState(false)

  async function load() {
    const [classData, attendance, allMembers] = await Promise.all([
      api(`classes/${classId}/`),
      api(`attendance/?fencing_class=${classId}`),
      isManager ? api('members/') : [],
    ])
    setFencingClass(classData)
    setNotes(classData.notes)
    setRows(attendance)
    setMembers(allMembers)
  }

  useEffect(() => {
    load()
  }, [classId])

  async function setStatus(row, status) {
    await api(`attendance/${row.id}/`, { method: 'PATCH', body: { status } })
    await load()
    onChange()
  }

  async function saveNotes() {
    if (notes === fencingClass.notes) return
    await api(`classes/${classId}/`, { method: 'PATCH', body: { notes } })
    await load()
  }

  async function addMember(memberId) {
    await api('attendance/', {
      method: 'POST',
      body: { fencing_class: classId, member: memberId, status: 'enrolled' },
    })
    await load()
    onChange()
  }

  async function removeRow(row) {
    await api(`attendance/${row.id}/`, { method: 'DELETE' })
    await load()
    onChange()
  }

  // Members only see their own row, so it's the first one if they're on the class.
  async function setEnrolled(enrolled) {
    setMessage('')
    try {
      await api(`classes/${classId}/${enrolled ? 'enrol' : 'unenrol'}/`, { method: 'POST' })
      await load()
      onChange()
    } catch (err) {
      setMessage(err.data?.detail ?? err.message)
    }
  }

  async function deleteClass() {
    if (!window.confirm(`Delete ${fencingClass.name}?`)) return
    await api(`classes/${classId}/`, { method: 'DELETE' })
    onChange()
    onClose()
  }

  async function repeatWeekly(event) {
    event.preventDefault()
    try {
      const result = await api(`classes/${classId}/repeat/`, {
        method: 'POST',
        body: { until },
      })
      setMessage(`Added ${result.created} more classes.`)
      await load()
      onChange()
    } catch (err) {
      setMessage(err.message)
    }
  }

  async function deleteFollowing() {
    if (!window.confirm(`Delete this and all later ${fencingClass.name} classes?`)) return
    await api(`classes/${classId}/delete-following/`, { method: 'POST' })
    onChange()
    onClose()
  }

  if (!fencingClass) return <aside className="panel">Loading…</aside>

  const editable = canEdit(me, fencingClass.coach)

  const available = members.filter(
    (member) => member.active && !rows.some((row) => row.member === member.id),
  )

  return (
    <aside className="panel">
      <button className="close" onClick={onClose} aria-label="Close">×</button>
      <h2>{fencingClass.name}</h2>
      <p className="meta">
        {formatTime(fencingClass.start)} – {formatTime(fencingClass.end)}
        {fencingClass.weapon && ` · ${CLASS_WEAPONS[fencingClass.weapon]}`}
        {fencingClass.coach_name && ` · ${fencingClass.coach_name}`}
        {fencingClass.location && ` · ${fencingClass.location}`}
      </p>
      {isManager && (
        <button className="button" onClick={() => setEditing(true)}>Edit class</button>
      )}
      {me.role === 'member' && new Date(fencingClass.start) > new Date() && (
        <>
          {rows.length === 0 && (
            <button className="button primary" onClick={() => setEnrolled(true)}>Enrol</button>
          )}
          {rows[0]?.status === 'enrolled' && (
            <button className="button" onClick={() => setEnrolled(false)}>Cancel enrolment</button>
          )}
          {message && <p className="meta">{message}</p>}
        </>
      )}
      {editing && (
        <ClassForm
          fencingClass={fencingClass}
          onSaved={async () => {
            setEditing(false)
            await load()
            onChange()
          }}
          onClose={() => setEditing(false)}
        />
      )}

      <h3>Notes</h3>
      {editable ? (
        <textarea
          className="notes"
          value={notes}
          placeholder="Add notes…"
          onChange={(e) => setNotes(e.target.value)}
          onBlur={saveNotes}
        />
      ) : (
        <p className="meta">{fencingClass.notes || 'No notes.'}</p>
      )}

      <h3>Attendance ({fencingClass.present_count} present)</h3>
      <ul className="attendance">
        {rows.map((row) => (
          <li key={row.id}>
            {isManager
              ? <Link className="row-link" to={`/members?member=${row.member}`}>{row.member_name}</Link>
              : <span>{row.member_name}</span>}
            <StatusSelect
              value={row.status}
              readOnly={!editable}
              onChange={(status) => setStatus(row, status)}
            />
            {isManager && (
              <button className="icon-button" onClick={() => removeRow(row)} aria-label="Remove">×</button>
            )}
          </li>
        ))}
      </ul>

      {isManager && (
        <>
          <select className="filter" value="" onChange={(e) => addMember(e.target.value)}>
            <option value="">Add a member…</option>
            {available.map((member) => (
              <option key={member.id} value={member.id}>{member.name}</option>
            ))}
          </select>

          <h3>Repeat weekly</h3>
          {fencingClass.series && <p className="meta">Part of a weekly series.</p>}
          <form className="repeat" onSubmit={repeatWeekly}>
            <label>
              Until <input type="date" value={until} onChange={(e) => setUntil(e.target.value)} required />
            </label>
            <button className="button">Repeat</button>
          </form>
          {message && <p className="meta">{message}</p>}

          <div className="danger-zone">
            <button className="danger" onClick={deleteClass}>Delete class</button>
            {fencingClass.series && (
              <button className="danger" onClick={deleteFollowing}>Delete this and following</button>
            )}
          </div>
        </>
      )}
    </aside>
  )
}
