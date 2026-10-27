import { useState } from 'react'
import { api } from './api'

export default function LoginPage({ onLogin }) {
  const [forgot, setForgot] = useState(false)

  return (
    <div className="login">
      {forgot
        ? <ForgotPasswordForm onBack={() => setForgot(false)} />
        : <LoginForm onLogin={onLogin} onForgot={() => setForgot(true)} />}
    </div>
  )
}

function LoginForm({ onLogin, onForgot }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    try {
      onLogin(await api('login/', { method: 'POST', body: { username, password } }))
    } catch (err) {
      setError(err.data?.detail || 'Wrong username or password.')
    }
  }

  return (
    <form className="login-card" onSubmit={submit}>
      <div className="workspace-icon login-icon">🤺</div>
      <h1>Fencing Club</h1>
      <label>
        Email or username
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          autoFocus
          required
        />
      </label>
      <label>
        Password
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
      </label>
      {error && <p className="error">{error}</p>}
      <button className="button primary">Log in</button>
      <button type="button" className="link-button" onClick={onForgot}>Forgot password?</button>
    </form>
  )
}

function ForgotPasswordForm({ onBack }) {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState('')
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    try {
      const response = await api('password-reset/', { method: 'POST', body: { email } })
      setSent(response.detail)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <form className="login-card" onSubmit={submit}>
      <div className="workspace-icon login-icon">🤺</div>
      <h1>Reset password</h1>
      {sent ? (
        <p className="muted">{sent} Check your inbox, and your spam folder too.</p>
      ) : (
        <>
          <p className="muted">Enter the email address your login uses and we’ll email you a link.</p>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              autoFocus
              required
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button className="button primary">Email me a link</button>
        </>
      )}
      <button type="button" className="link-button" onClick={onBack}>Back to log in</button>
    </form>
  )
}
