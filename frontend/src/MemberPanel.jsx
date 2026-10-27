import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api } from './api'
import { canEdit, useMe } from './auth'
import { WEAPONS, attendanceRate, formatDate, formatDateTime } from './format'
import LoginRow from './LoginRow'
import MemberForm from './MemberForm'
import { RateBar } from './MembersPage'
import StatusSelect from './StatusSelect'

// Managers peek at a member from the Members table.
export default function MemberPanel({ id, onChange, onClose }) {
  return (
    <aside className="panel">
      <button className="close" onClick={onClose} aria-label="Close">×</button>
      <MemberDetails id={id} onChange={onChange} />
    </aside>
  )
}

// Members see their own details as a page, under My profile.
export function MemberProfilePage({ id }) {
  return (
    <div className="page">
      <MemberDetails id={id} />
    </div>
  )
}

// `onChange` tells the Members table to reload after an edit or a status change.
function MemberDetails({ id, onChange = () => {} }) {
  const me = useMe()
  const [member, setMember] = useState(null)
  const [history, setHistory] = useState([])
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)

  useEffect(() => {
    Promise.all([api(`members/${id}/`), api(`attendance/?member=${id}`)])
      .then(([memberData, rows]) => {
        setMember(memberData)
        setHistory(rows)
      })
      .catch((err) => setError(err.message))
  }, [id])

  async function reload() {
    const [memberData, rows] = await Promise.all([
      api(`members/${id}/`),
      api(`attendance/?member=${id}`),
    ])
    setMember(memberData)
    setHistory(rows)
    onChange()
  }

  async function setStatus(row, status) {
    await api(`attendance/${row.id}/`, { method: 'PATCH', body: { status } })
    await reload()
  }

  if (error) return <p className="error">{error}</p>
  if (!member) return <p className="muted">Loading…</p>

  return (
    <>
      <div className="avatar">{member.name[0]}</div>
      <h1 className="page-title">{member.name}</h1>
      {me.role !== 'coach' && (
        <button className="button" onClick={() => setEditing(true)}>
          {me.role === 'member' ? 'Edit my details' : 'Edit member'}
        </button>
      )}

      <dl className="properties">
        <dt>Attendance</dt>
        <dd>
          <RateBar rate={attendanceRate(member)} />
          {member.marked_count > 0 && (
            <span className="muted"> · {member.present_count} of {member.marked_count}</span>
          )}
        </dd>
        <dt>Last attended</dt>
        <dd>{member.last_present ? formatDate(member.last_present) : <span className="muted">Never</span>}</dd>
        <dt>Weapon</dt>
        <dd>
          {member.weapon
            ? <span className={`tag weapon-${member.weapon}`}>{WEAPONS[member.weapon]}</span>
            : <span className="muted">Empty</span>}
        </dd>
        <dt>Primary coach</dt>
        <dd>
          {member.primary_coach ? (
            me.role === 'manager'
              ? <Link to={`/coaches/${member.primary_coach}`}>{member.primary_coach_name}</Link>
              : member.primary_coach_name
          ) : <span className="muted">Empty</span>}
        </dd>
        <dt>Email</dt>
        <dd>{member.email || <span className="muted">Empty</span>}</dd>
        <dt>Phone</dt>
        <dd>{member.phone || <span className="muted">Empty</span>}</dd>
        <dt>Status</dt>
        <dd>
          <span className={`tag ${member.active ? 'status-present' : 'status-enrolled'}`}>
            {member.active ? 'Active' : 'Inactive'}
          </span>
        </dd>
        {me.role === 'manager' && <LoginRow person={member} kind="member" onChange={reload} />}
      </dl>
      {editing && (
        <MemberForm
          member={member}
          onSaved={async () => {
            setEditing(false)
            await reload()
          }}
          onClose={() => setEditing(false)}
        />
      )}

      <h3 className="section-title">Class history</h3>
      {history.length === 0 ? (
        <p className="empty">Not on any class rosters yet.</p>
      ) : (
        <ul className="attendance history">
          {history.map((row) => (
            <li key={row.id}>
              <span className="history-class">
                {row.class_name}
                <span className="muted">{formatDateTime(row.class_start)}</span>
              </span>
              <StatusSelect
                value={row.status}
                readOnly={!canEdit(me, row.coach)}
                onChange={(status) => setStatus(row, status)}
              />
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
