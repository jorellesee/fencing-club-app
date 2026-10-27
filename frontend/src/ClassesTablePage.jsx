import { useEffect, useState } from 'react'
import { api } from './api'
import AttendancePanel from './AttendancePanel'
import { useMe } from './auth'
import ClassesHeader from './ClassesHeader'
import ClassFilters from './ClassFilters'
import ClassForm from './ClassForm'
import { attendanceCount, classParams } from './classes'
import { CLASS_WEAPONS, formatDateTime } from './format'
import StatusSelect from './StatusSelect'

// Members also get their own status for each class, keyed by class id.
async function fetchTable(me, query) {
  const [classes, rows] = await Promise.all([
    api(`classes/?${query}`),
    me.role === 'member' ? api(`attendance/?member=${me.member}`) : [],
  ])
  const myStatus = Object.fromEntries(rows.map((row) => [row.fencing_class, row.status]))
  return { classes, myStatus }
}

export default function ClassesTablePage({ filters, onFiltersChange }) {
  const me = useMe()
  const isManager = me.role === 'manager'
  const query = classParams(me, filters).toString()
  const [data, setData] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    fetchTable(me, query).then(setData).catch((err) => setError(err.message))
  }, [me, query])

  function refresh() {
    fetchTable(me, query).then(setData).catch((err) => setError(err.message))
  }

  function classCreated(saved) {
    setCreating(false)
    refresh()
    setSelectedId(String(saved.id))
  }

  const now = new Date()
  const classes = data?.classes ?? []
  const upcoming = classes.filter((c) => new Date(c.end) >= now)
  const past = classes.filter((c) => new Date(c.end) < now).reverse()

  function section(title, rows, emptyText) {
    return (
      <>
        <h2 className="section-title">{title}</h2>
        {rows.length === 0 ? <p className="empty">{emptyText}</p> : (
          <table className="table database clickable">
            <thead>
              <tr>
                <th>When</th>
                <th>Class</th>
                <th>Weapon</th>
                {me.role !== 'coach' && <th>Coach</th>}
                <th>Location</th>
                <th>{me.role === 'member' ? 'My status' : 'Present'}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr
                  key={c.id}
                  className={String(c.id) === selectedId ? 'selected' : ''}
                  onClick={() => setSelectedId(String(c.id))}
                >
                  <td className="muted">{formatDateTime(c.start)}</td>
                  <td className="strong">{c.name}</td>
                  <td>
                    {c.weapon && <span className={`tag weapon-${c.weapon}`}>{CLASS_WEAPONS[c.weapon]}</span>}
                  </td>
                  {me.role !== 'coach' && <td>{c.coach_name}</td>}
                  <td>{c.location}</td>
                  <td>
                    {me.role === 'member'
                      ? data.myStatus[c.id] && <StatusSelect value={data.myStatus[c.id]} readOnly />
                      : attendanceCount(c)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </>
    )
  }

  return (
    <div className="calendar-page">
      <div className="page-scroll">
        <div className="page">
          <ClassesHeader />
          {isManager && (
            <div className="toolbar">
              <ClassFilters filters={filters} onChange={onFiltersChange} />
              <button className="button primary" onClick={() => setCreating(true)}>+ New class</button>
            </div>
          )}
          {error && <p className="error">{error}</p>}
          {data && section('Upcoming', upcoming, 'No upcoming classes.')}
          {data && section('Past', past, 'No past classes.')}
        </div>
      </div>
      {creating && <ClassForm onSaved={classCreated} onClose={() => setCreating(false)} />}
      {selectedId && (
        <AttendancePanel
          key={selectedId}
          classId={selectedId}
          onChange={refresh}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  )
}
