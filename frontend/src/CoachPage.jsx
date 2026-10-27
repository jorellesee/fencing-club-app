import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { api } from './api'
import { attendanceCount } from './classes'
import CoachForm from './CoachForm'
import { CLASS_WEAPONS, WEAPONS, formatDateTime } from './format'
import LoginRow from './LoginRow'

// How many classes each section shows, so a long weekly series doesn't fill the page.
const SHOWN = 10

export default function CoachPage() {
  const { id } = useParams()
  const [coach, setCoach] = useState(null)
  const [classes, setClasses] = useState([])
  const [members, setMembers] = useState([])
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)

  useEffect(() => {
    Promise.all([
      api(`coaches/${id}/`),
      api(`classes/?coach=${id}`),
      api(`members/?primary_coach=${id}`),
    ])
      .then(([coachData, rows, memberRows]) => {
        setCoach(coachData)
        setClasses(rows)
        setMembers(memberRows)
      })
      .catch((err) => setError(err.message))
  }, [id])

  async function reloadCoach() {
    setCoach(await api(`coaches/${id}/`))
  }

  if (error) return <div className="page"><p className="error">{error}</p></div>
  if (!coach) return <div className="page muted">Loading…</div>

  const now = new Date()
  const upcoming = classes.filter((c) => new Date(c.end) >= now).slice(0, SHOWN)
  const past = classes.filter((c) => new Date(c.end) < now).reverse().slice(0, SHOWN)

  return (
    <div className="page">
      <div className="breadcrumbs">
        <Link to="/coaches">Coaches</Link> / {coach.name}
      </div>
      <div className="avatar">{coach.name[0]}</div>
      <h1 className="page-title">{coach.name}</h1>
      <div className="toolbar">
        <span />
        <button className="button" onClick={() => setEditing(true)}>Edit coach</button>
      </div>

      <dl className="properties">
        <dt>Classes</dt>
        <dd>{coach.class_count}</dd>
        <dt>Next class</dt>
        <dd>{coach.next_class ? formatDateTime(coach.next_class) : <span className="muted">None booked</span>}</dd>
        <dt>Weapon</dt>
        <dd>
          {coach.weapon
            ? <span className={`tag weapon-${coach.weapon}`}>{WEAPONS[coach.weapon]}</span>
            : <span className="muted">Empty</span>}
        </dd>
        <dt>Email</dt>
        <dd>{coach.email || <span className="muted">Empty</span>}</dd>
        <dt>Phone</dt>
        <dd>{coach.phone || <span className="muted">Empty</span>}</dd>
        <dt>Status</dt>
        <dd>
          <span className={`tag ${coach.active ? 'status-present' : 'status-enrolled'}`}>
            {coach.active ? 'Active' : 'Inactive'}
          </span>
        </dd>
        <LoginRow person={coach} kind="coach" onChange={reloadCoach} />
      </dl>

      <h2 className="section-title">Members they coach</h2>
      {members.length === 0 ? (
        <p className="empty">No members have {coach.name} as their primary coach.</p>
      ) : (
        <table className="table database">
          <thead>
            <tr>
              <th>Name</th>
              <th>Weapon</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <tr key={member.id}>
                <td>
                  <Link className="row-link strong" to={`/members?member=${member.id}`}>{member.name}</Link>
                </td>
                <td>
                  {member.weapon && (
                    <span className={`tag weapon-${member.weapon}`}>{WEAPONS[member.weapon]}</span>
                  )}
                </td>
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

      <ClassList title="Upcoming classes" rows={upcoming} emptyText="No upcoming classes." />
      <ClassList title="Recent classes" rows={past} emptyText="No past classes." />

      {editing && (
        <CoachForm
          coach={coach}
          onSaved={async () => {
            setEditing(false)
            await reloadCoach()
          }}
          onClose={() => setEditing(false)}
        />
      )}
    </div>
  )
}

function ClassList({ title, rows, emptyText }) {
  return (
    <>
      <h2 className="section-title">{title}</h2>
      {rows.length === 0 ? (
        <p className="empty">{emptyText}</p>
      ) : (
        <table className="table database">
          <thead>
            <tr>
              <th>When</th>
              <th>Class</th>
              <th>Weapon</th>
              <th>Location</th>
              <th>Present</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id}>
                <td className="muted">{formatDateTime(c.start)}</td>
                <td className="strong">{c.name}</td>
                <td>
                  {c.weapon && <span className={`tag weapon-${c.weapon}`}>{CLASS_WEAPONS[c.weapon]}</span>}
                </td>
                <td>{c.location}</td>
                <td>{attendanceCount(c)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}
