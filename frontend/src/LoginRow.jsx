import { useState } from 'react'
import { api } from './api'
import FormErrors from './FormErrors'

const STATUS_LABELS = { invited: 'Invited', active: 'Active', deactivated: 'Switched off' }
const STATUS_CLASSES = { invited: 'status-excused', active: 'status-present', deactivated: 'status-enrolled' }

// The Login property on a member's or coach's details: invite them, resend the
// invite, or switch their login off and on. `kind` is 'member' or 'coach'.
export default function LoginRow({ person, kind, onChange }) {
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState('')
  const { login } = person

  async function run(request, message) {
    setError(null)
    try {
      await request
      setNotice(message)
      await onChange()
    } catch (err) {
      setError(err)
    }
  }

  // Inviting someone who already has a pending invite sends them a fresh link.
  function invite() {
    run(api('logins/', { method: 'POST', body: { [kind]: person.id } }), `Sent to ${person.email}`)
  }

  function setActive(isActive) {
    run(
      api(`logins/${login.id}/`, { method: 'PATCH', body: { is_active: isActive } }),
      isActive ? 'They can log in again' : 'They can no longer log in',
    )
  }

  return (
    <>
      <dt>Login</dt>
      <dd className="login-row">
        {login
          ? <span className={`tag ${STATUS_CLASSES[login.status]}`}>{STATUS_LABELS[login.status]}</span>
          : <span className="muted">None</span>}
        {(!login || login.status === 'invited') && (
          person.email ? (
            <button className="button" onClick={invite}>
              {login ? 'Resend invite' : 'Invite to log in'}
            </button>
          ) : (
            <span className="muted">Add an email to invite them</span>
          )
        )}
        {login && login.status !== 'deactivated' && (
          <button className="button" onClick={() => setActive(false)}>Switch off</button>
        )}
        {login?.status === 'deactivated' && (
          <button className="button" onClick={() => setActive(true)}>Switch on</button>
        )}
        {notice && <span className="muted">{notice}</span>}
        <FormErrors error={error} />
      </dd>
    </>
  )
}
