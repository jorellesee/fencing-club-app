import { useEffect, useState } from 'react'
import { api } from './api'

const STATUSES = ['enrolled', 'present', 'absent', 'excused']

function formatTime(iso) {
  return new Date(iso).toLocaleString([], {
    weekday: 'short', hour: '2-digit', minute: '2-digit',
  })
}

export default function AttendancePanel({ classId, onChange, onClose }) {
  const [fencingClass, setFencingClass] = useState(null)
  const [rows, setRows] = useState([])
  const [members, setMembers] = useState([])
  const [until, setUntil] = useState('')
  const [message, setMessage] = useState('')

  async function load() {
    const [classData, attendance, allMembers] = await Promise.all([
      api(`classes/${classId}/`),
      api(`attendance/?fencing_class=${classId}`),
      api('members/'),
    ])
    setFencingClass(classData)
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

  const available = members.filter(
    (member) => member.active && !rows.some((row) => row.member === member.id),
  )

  return (
    <aside className="panel">
      <button className="close" onClick={onClose}>×</button>
      <h2>{fencingClass.name}</h2>
      <p className="meta">
        {formatTime(fencingClass.start)} – {formatTime(fencingClass.end)}
        {fencingClass.coach && ` · ${fencingClass.coach}`}
      </p>

      <h3>Attendance ({fencingClass.present_count} present)</h3>
      <ul className="attendance">
        {rows.map((row) => (
          <li key={row.id}>
            <span>{row.member_name}</span>
            <select value={row.status} onChange={(e) => setStatus(row, e.target.value)}>
              {STATUSES.map((status) => (
                <option key={status} value={status}>{status}</option>
              ))}
            </select>
            <button onClick={() => removeRow(row)}>Remove</button>
          </li>
        ))}
      </ul>

      <select value="" onChange={(e) => addMember(e.target.value)}>
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
        <button>Repeat</button>
      </form>
      {message && <p className="meta">{message}</p>}

      <button className="danger" onClick={deleteClass}>Delete class</button>
      {fencingClass.series && (
        <button className="danger" onClick={deleteFollowing}>Delete this and following</button>
      )}
    </aside>
  )
}
