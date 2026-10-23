import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { api } from './api'
import { canEdit, useMe } from './auth'
import { WEAPONS, attendanceRate, formatDate, formatDateTime } from './format'
import { RateBar } from './MembersPage'
import StatusSelect from './StatusSelect'

export default function MemberPage({ onChange }) {
  const me = useMe()
  const { id } = useParams()
  const [member, setMember] = useState(null)
  const [history, setHistory] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api(`members/${id}/`), api(`attendance/?member=${id}`)])
      .then(([memberData, rows]) => {
        setMember(memberData)
        setHistory(rows)
      })
      .catch((err) => setError(err.message))
  }, [id])

  async function setStatus(row, status) {
    await api(`attendance/${row.id}/`, { method: 'PATCH', body: { status } })
    const [memberData, rows] = await Promise.all([
      api(`members/${id}/`),
      api(`attendance/?member=${id}`),
    ])
    setMember(memberData)
    setHistory(rows)
    onChange()
  }

  if (error) return <div className="page"><p className="error">{error}</p></div>
  if (!member) return <div className="page muted">Loading…</div>

  return (
    <div className="page">
      {me.role !== 'member' && (
        <div className="breadcrumbs">
          <Link to="/members">Members</Link> / {member.name}
        </div>
      )}
      <div className="avatar">{member.name[0]}</div>
      <h1 className="page-title">{member.name}</h1>

      <dl className="properties">
        <dt>Attendance</dt>
        <dd>
          <RateBar rate={attendanceRate(member)} />
          {member.marked_count > 0 && (
            <span className="muted"> · {member.present_count} of {member.marked_count} classes</span>
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
      </dl>

      <h2 className="section-title">Class history</h2>
      {history.length === 0 ? (
        <p className="empty">Not on any class rosters yet.</p>
      ) : (
        <table className="table database">
          <thead>
            <tr>
              <th>Date</th>
              <th>Class</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {history.map((row) => (
              <tr key={row.id}>
                <td className="muted">{formatDateTime(row.class_start)}</td>
                <td>{row.class_name}</td>
                <td>
                  <StatusSelect
                    value={row.status}
                    readOnly={!canEdit(me, row.coach)}
                    onChange={(status) => setStatus(row, status)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
