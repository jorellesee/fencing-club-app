import { NavLink } from 'react-router'
import { useMe } from './auth'

// The classes page's heading, with a switch between the calendar and the list.
// Both views share the filters, which App keeps.
export default function ClassesHeader() {
  const me = useMe()
  return (
    <div className="title-row">
      <h1 className="page-title">
        <span className="page-icon">📅</span>{me.role === 'manager' ? 'Classes' : 'My classes'}
      </h1>
      <div className="view-toggle">
        <NavLink to="/" end>Calendar</NavLink>
        <NavLink to="/table">List</NavLink>
      </div>
    </div>
  )
}
