import { useState } from 'react'
import { api } from './api'

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    try {
      onLogin(await api('login/', { method: 'POST', body: { username, password } }))
    } catch {
      setError('Wrong username or password.')
    }
  }

  return (
    <div className="login">
      <form className="login-card" onSubmit={submit}>
        <div className="workspace-icon login-icon">🤺</div>
        <h1>Fencing Club</h1>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="button primary">Log in</button>
      </form>
    </div>
  )
}
