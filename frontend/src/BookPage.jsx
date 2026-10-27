import { useEffect, useState } from 'react'
import { api } from './api'
import { CLASS_WEAPONS, formatDateTime } from './format'
import FormErrors from './FormErrors'

function spotsLeft(fencingClass) {
  if (fencingClass.capacity === null) return null
  return Math.max(fencingClass.capacity - fencingClass.member_count, 0)
}

// Upcoming classes a member isn't on yet, to enrol themselves in.
export default function BookPage() {
  const [classes, setClasses] = useState(null)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    api('classes/?bookable=1').then(setClasses).catch(setError)
  }, [])

  async function enrol(fencingClass) {
    setError(null)
    try {
      await api(`classes/${fencingClass.id}/enrol/`, { method: 'POST' })
      setNotice(`You’re enrolled in ${fencingClass.name}, ${formatDateTime(fencingClass.start)}.`)
    } catch (err) {
      setError(err)
    }
    setClasses(await api('classes/?bookable=1'))
  }

  return (
    <div className="page">
      <h1 className="page-title">
        <span className="page-icon">➕</span>Book a class
      </h1>
      <p className="page-description">
        Upcoming classes you’re not on yet. Once you enrol, they appear in My calendar and My classes.
      </p>
      {notice && <p className="notice">{notice}</p>}
      <FormErrors error={error} />
      {classes && classes.length > 0 && (
        <table className="table database">
          <thead>
            <tr>
              <th>When</th>
              <th>Class</th>
              <th>Weapon</th>
              <th>Coach</th>
              <th>Location</th>
              <th>Spots</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {classes.map((c) => {
              const spots = spotsLeft(c)
              return (
                <tr key={c.id}>
                  <td className="muted">{formatDateTime(c.start)}</td>
                  <td className="strong">{c.name}</td>
                  <td>
                    {c.weapon && <span className={`tag weapon-${c.weapon}`}>{CLASS_WEAPONS[c.weapon]}</span>}
                  </td>
                  <td>{c.coach_name}</td>
                  <td>{c.location}</td>
                  <td className="muted">{spots === null ? 'Open' : `${spots} left`}</td>
                  <td className="row-actions">
                    <button className="button primary" disabled={spots === 0} onClick={() => enrol(c)}>
                      {spots === 0 ? 'Full' : 'Enrol'}
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
      {classes?.length === 0 && <p className="empty">No upcoming classes to book right now.</p>}
    </div>
  )
}
