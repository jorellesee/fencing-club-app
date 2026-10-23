import { useCallback, useEffect, useState } from 'react'
import { NavLink, Route, Routes, useLocation, useNavigate } from 'react-router'
import { api } from './api'
import { MeContext } from './auth'
import CalendarPage from './CalendarPage'
import { NO_FILTERS } from './classes'
import ClassesTablePage from './ClassesTablePage'
import LoginPage from './LoginPage'
import MemberPage from './MemberPage'
import MembersPage from './MembersPage'
import UnmarkedPage from './UnmarkedPage'
import './App.css'

const ROLE_LABELS = { manager: 'Manager', coach: 'Coach', member: 'Member' }

export default function App() {
  // undefined while checking the session, null when logged out.
  const [me, setMe] = useState(undefined)

  useEffect(() => {
    api('me/').then(setMe).catch(() => setMe(null))
  }, [])

  if (me === undefined) return <p className="page muted">Loading…</p>
  if (me === null) return <LoginPage onLogin={setMe} />

  return (
    <MeContext.Provider value={me}>
      <Layout me={me} onLogout={() => setMe(null)} />
    </MeContext.Provider>
  )
}

function Layout({ me, onLogout }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [unmarkedCount, setUnmarkedCount] = useState(0)
  // Shared by the calendar and the table, so switching views keeps them.
  const [filters, setFilters] = useState(NO_FILTERS)
  const isManager = me.role === 'manager'

  const refreshCount = useCallback(() => {
    if (!isManager) return
    api('attendance/unmarked/')
      .then((rows) => setUnmarkedCount(rows.length))
      .catch(() => setUnmarkedCount(0))
  }, [isManager])

  useEffect(() => {
    refreshCount()
  }, [location.pathname, refreshCount])

  async function logout() {
    await api('logout/', { method: 'POST' })
    navigate('/')
    onLogout()
  }

  const viewProps = { filters, onFiltersChange: setFilters, onChange: refreshCount }

  return (
    <div className="app">
      <nav className="sidebar">
        <div className="workspace">
          <span className="workspace-icon">🤺</span>
          Fencing Club
        </div>
        <NavLink to="/" end className="nav-item">
          <span className="nav-icon">📅</span>{isManager ? 'Calendar' : 'My calendar'}
        </NavLink>
        <NavLink to="/table" className="nav-item">
          <span className="nav-icon">📋</span>{isManager ? 'All classes' : 'My classes'}
        </NavLink>
        {isManager && (
          <>
            <NavLink to="/unmarked" className="nav-item">
              <span className="nav-icon">✅</span>Needs marking
              {unmarkedCount > 0 && <span className="badge">{unmarkedCount}</span>}
            </NavLink>
            <NavLink to="/members" className="nav-item">
              <span className="nav-icon">👥</span>Members
            </NavLink>
          </>
        )}
        <div className="account">
          <div className="account-name">
            {me.username}
            <span className="muted"> · {ROLE_LABELS[me.role]}</span>
          </div>
          <button className="nav-item account-logout" onClick={logout}>
            <span className="nav-icon">↩</span>Log out
          </button>
        </div>
      </nav>
      <main className="main">
        <Routes>
          <Route path="/" element={<CalendarPage {...viewProps} />} />
          <Route path="/table" element={<ClassesTablePage {...viewProps} />} />
          {isManager && (
            <>
              <Route path="/unmarked" element={<UnmarkedPage onChange={refreshCount} />} />
              <Route path="/members" element={<MembersPage />} />
              <Route path="/members/:id" element={<MemberPage onChange={refreshCount} />} />
            </>
          )}
        </Routes>
      </main>
    </div>
  )
}
