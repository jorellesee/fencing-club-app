import { useEffect, useState } from 'react'
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate, useParams } from 'react-router'
import { api } from './api'
import { MeContext } from './auth'
import BookPage from './BookPage'
import CalendarPage from './CalendarPage'
import { NO_FILTERS } from './classes'
import ClassesTablePage from './ClassesTablePage'
import CoachesPage from './CoachesPage'
import CoachPage from './CoachPage'
import LessonsPage from './LessonsPage'
import LoginPage from './LoginPage'
import { MemberProfilePage } from './MemberPanel'
import MembersPage from './MembersPage'
import SetPasswordPage from './SetPasswordPage'
import './App.css'

const ROLE_LABELS = { manager: 'Manager', coach: 'Coach', member: 'Member' }

export default function App() {
  // undefined while checking the session, null when logged out.
  const [me, setMe] = useState(undefined)

  useEffect(() => {
    api('me/').then(setMe).catch(() => setMe(null))
  }, [])

  if (me === undefined) return <p className="page muted">Loading…</p>

  return (
    <Routes>
      {/* Links in invite and reset emails work whether or not someone is logged in. */}
      <Route path="/set-password/:uid/:token" element={<SetPasswordPage onLogin={setMe} />} />
      <Route
        path="*"
        element={
          me === null ? (
            <LoginPage onLogin={setMe} />
          ) : (
            <MeContext.Provider value={me}>
              <Layout me={me} onLogout={() => setMe(null)} />
            </MeContext.Provider>
          )
        }
      />
    </Routes>
  )
}

function Layout({ me, onLogout }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  // Shared by the calendar and the table, so switching views keeps them.
  const [filters, setFilters] = useState(NO_FILTERS)
  const isManager = me.role === 'manager'
  const isMember = me.role === 'member'

  async function logout() {
    await api('logout/', { method: 'POST' })
    navigate('/')
    onLogout()
  }

  const viewProps = { filters, onFiltersChange: setFilters }

  return (
    <div className="app">
      <nav className="sidebar">
        <div className="workspace">
          <span className="workspace-icon">🤺</span>
          Fencing Club
        </div>
        {/* One item for both views; the page itself switches between them. */}
        <NavLink
          to="/"
          className={`nav-item ${pathname === '/' || pathname === '/table' ? 'active' : ''}`}
        >
          <span className="nav-icon">📅</span>{isManager ? 'Classes' : 'My classes'}
        </NavLink>
        {isMember && (
          <NavLink to="/book" className="nav-item">
            <span className="nav-icon">➕</span>Book a class
          </NavLink>
        )}
        {isMember && (
          <NavLink to="/lessons" className="nav-item">
            <span className="nav-icon">🎯</span>Private lessons
          </NavLink>
        )}
        {isMember && (
          <NavLink to="/profile" className="nav-item">
            <span className="nav-icon">👤</span>My profile
          </NavLink>
        )}
        {isManager && (
          <NavLink to="/members" className="nav-item">
            <span className="nav-icon">👥</span>Members
          </NavLink>
        )}
        {isManager && (
          <NavLink to="/coaches" className="nav-item">
            <span className="nav-icon">🧑‍🏫</span>Coaches
          </NavLink>
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
          {isMember && (
            <>
              <Route path="/book" element={<BookPage />} />
              <Route path="/lessons" element={<LessonsPage />} />
              <Route path="/profile" element={<MemberProfilePage id={me.member} />} />
            </>
          )}
          {isManager && (
            <>
              <Route path="/members" element={<MembersPage />} />
              <Route path="/members/:id" element={<OldMemberLink />} />
              <Route path="/coaches" element={<CoachesPage />} />
              <Route path="/coaches/:id" element={<CoachPage />} />
            </>
          )}
        </Routes>
      </main>
    </div>
  )
}

// Member pages became a side peek on /members. Keeps old bookmarks working.
function OldMemberLink() {
  const { id } = useParams()
  return <Navigate to={`/members?member=${id}`} replace />
}
