import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { api } from './api'
import FormErrors from './FormErrors'

// Where invite and password reset emails link to.
export default function SetPasswordPage({ onLogin }) {
  const { uid, token } = useParams()
  const navigate = useNavigate()
  const [link, setLink] = useState(null)
  const [badLink, setBadLink] = useState('')
  const [password, setPassword] = useState('')
  const [passwordAgain, setPasswordAgain] = useState('')
  const [error, setError] = useState(null)

  useEffect(() => {
    api(`set-password/${uid}/${token}/`)
      .then(setLink)
      .catch((err) => setBadLink(err.data?.detail || err.message))
  }, [uid, token])

  async function submit(event) {
    event.preventDefault()
    try {
      const account = await api(`set-password/${uid}/${token}/`, {
        method: 'POST',
        body: { password, password_again: passwordAgain },
      })
      navigate('/')
      onLogin(account)
    } catch (err) {
      setError(err)
    }
  }

  if (badLink) {
    return (
      <div className="login">
        <div className="login-card">
          <div className="workspace-icon login-icon">🤺</div>
          <h1>Link not working</h1>
          <p className="muted">{badLink} Ask the club manager to resend your invite, or reset your password from the login page.</p>
          <Link className="button primary login-link-button" to="/">Go to login</Link>
        </div>
      </div>
    )
  }
  if (!link) return <p className="page muted">Loading…</p>

  return (
    <div className="login">
      <form className="login-card" onSubmit={submit}>
        <div className="workspace-icon login-icon">🤺</div>
        <h1>{link.invited ? `Welcome, ${link.name}` : 'Choose a new password'}</h1>
        <p className="muted">Your username is <strong>{link.username}</strong>.</p>
        <label>
          New password
          <input
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
            required
          />
        </label>
        <label>
          New password again
          <input
            type="password"
            autoComplete="new-password"
            value={passwordAgain}
            onChange={(e) => setPasswordAgain(e.target.value)}
            required
          />
        </label>
        <FormErrors error={error} />
        <button className="button primary">{link.invited ? 'Set password and log in' : 'Save and log in'}</button>
      </form>
    </div>
  )
}
