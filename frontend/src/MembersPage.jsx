import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api } from './api'
import { WEAPONS, attendanceRate, formatDate } from './format'
import MemberForm from './MemberForm'

export function RateBar({ rate }) {
  if (rate === null) return <span className="muted">No classes yet</span>
  return (
    <span className="rate">
      <span className="rate-bar">
        <span className="rate-fill" style={{ width: `${rate}%` }} />
      </span>
      {rate}%
    </span>
  )
}

export default function MembersPage() {
  const [members, setMembers] = useState(null)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    api('members/').then(setMembers).catch((err) => setError(err.message))
  }, [])

  async function memberCreated() {
    setCreating(false)
    setMembers(await api('members/'))
  }

  return (
    <div className="page">
      <h1 className="page-title">
        <span className="page-icon">👥</span>Members
      </h1>
      <div className="toolbar">
        <span />
        <button className="button primary" onClick={() => setCreating(true)}>+ New member</button>
      </div>
      {error && <p className="error">{error}</p>}
      {members && (
        <table className="table database">
          <thead>
            <tr>
              <th>Name</th>
              <th>Weapon</th>
              <th>Attendance</th>
              <th>Last attended</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <tr key={member.id}>
                <td>
                  <Link className="row-link strong" to={`/members/${member.id}`}>{member.name}</Link>
                </td>
                <td>
                  {member.weapon && (
                    <span className={`tag weapon-${member.weapon}`}>{WEAPONS[member.weapon]}</span>
                  )}
                </td>
                <td><RateBar rate={attendanceRate(member)} /></td>
                <td className="muted">{member.last_present && formatDate(member.last_present)}</td>
                <td>
                  <span className={`tag ${member.active ? 'status-present' : 'status-enrolled'}`}>
                    {member.active ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {members?.length === 0 && <p className="empty">No members yet. Click New member to add one.</p>}
      {creating && <MemberForm onSaved={memberCreated} onClose={() => setCreating(false)} />}
    </div>
  )
}
