import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api } from './api'
import CoachForm from './CoachForm'
import { WEAPONS, formatDateTime } from './format'

export default function CoachesPage() {
  const [coaches, setCoaches] = useState(null)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    api('coaches/').then(setCoaches).catch((err) => setError(err.message))
  }, [])

  async function coachCreated() {
    setCreating(false)
    setCoaches(await api('coaches/'))
  }

  return (
    <div className="page">
      <h1 className="page-title">
        <span className="page-icon">🧑‍🏫</span>Coaches
      </h1>
      <div className="toolbar">
        <span />
        <button className="button primary" onClick={() => setCreating(true)}>+ New coach</button>
      </div>
      {error && <p className="error">{error}</p>}
      {coaches && coaches.length > 0 && (
        <table className="table database">
          <thead>
            <tr>
              <th>Name</th>
              <th>Weapon</th>
              <th>Classes</th>
              <th>Next class</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {coaches.map((coach) => (
              <tr key={coach.id}>
                <td>
                  <Link className="row-link strong" to={`/coaches/${coach.id}`}>{coach.name}</Link>
                </td>
                <td>
                  {coach.weapon && (
                    <span className={`tag weapon-${coach.weapon}`}>{WEAPONS[coach.weapon]}</span>
                  )}
                </td>
                <td>{coach.class_count}</td>
                <td className="muted">{coach.next_class && formatDateTime(coach.next_class)}</td>
                <td>
                  <span className={`tag ${coach.active ? 'status-present' : 'status-enrolled'}`}>
                    {coach.active ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {coaches?.length === 0 && <p className="empty">No coaches yet. Click New coach to add one.</p>}
      {creating && <CoachForm onSaved={coachCreated} onClose={() => setCreating(false)} />}
    </div>
  )
}
