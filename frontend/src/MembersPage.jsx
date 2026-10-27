import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'
import { api } from './api'
import { WEAPONS, attendanceRate, formatDate } from './format'
import MemberForm from './MemberForm'
import MemberPanel from './MemberPanel'

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
  // In the URL, so other pages can link straight to a member: /members?member=3
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('member')

  useEffect(() => {
    api('members/').then(setMembers).catch((err) => setError(err.message))
  }, [])

  function refresh() {
    api('members/').then(setMembers).catch((err) => setError(err.message))
  }

  function select(id) {
    setSearchParams(id ? { member: id } : {})
  }

  async function memberCreated(saved) {
    setCreating(false)
    refresh()
    select(String(saved.id))
  }

  return (
    <div className="calendar-page">
      <div className="page-scroll">
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
            <table className="table database clickable">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Weapon</th>
                  <th>Primary coach</th>
                  <th>Attendance</th>
                  <th>Last attended</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr
                    key={member.id}
                    className={String(member.id) === selectedId ? 'selected' : ''}
                    onClick={() => select(String(member.id))}
                  >
                    <td className="strong">{member.name}</td>
                    <td>
                      {member.weapon && (
                        <span className={`tag weapon-${member.weapon}`}>{WEAPONS[member.weapon]}</span>
                      )}
                    </td>
                    <td>{member.primary_coach_name}</td>
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
      </div>
      {selectedId && (
        <MemberPanel
          key={selectedId}
          id={selectedId}
          onChange={refresh}
          onClose={() => select(null)}
        />
      )}
    </div>
  )
}
