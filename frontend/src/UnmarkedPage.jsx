import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api } from './api'
import { formatDateTime } from './format'
import StatusSelect from './StatusSelect'

// Rows arrive sorted by class, so each class's rows are next to each other.
function groupByClass(rows) {
  const classes = []
  for (const row of rows) {
    const last = classes.at(-1)
    if (last?.id === row.fencing_class) {
      last.rows.push(row)
    } else {
      classes.push({ id: row.fencing_class, name: row.class_name, start: row.class_start, rows: [row] })
    }
  }
  return classes
}

export default function UnmarkedPage({ onChange }) {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api('attendance/unmarked/').then(setRows).catch((err) => setError(err.message))
  }, [])

  async function reload() {
    setRows(await api('attendance/unmarked/'))
    onChange()
  }

  async function setStatus(row, status) {
    await api(`attendance/${row.id}/`, { method: 'PATCH', body: { status } })
    await reload()
  }

  async function markAllPresent(classRows) {
    await Promise.all(classRows.map((row) => (
      api(`attendance/${row.id}/`, { method: 'PATCH', body: { status: 'present' } })
    )))
    await reload()
  }

  const classes = rows ? groupByClass(rows) : []

  return (
    <div className="page">
      <h1 className="page-title">
        <span className="page-icon">✅</span>Needs marking
      </h1>
      <p className="page-description">
        Past classes where someone is still <span className="tag status-enrolled">enrolled</span>.
        Mark each one present, absent or excused.
      </p>
      {error && <p className="error">{error}</p>}
      {rows && classes.length === 0 && (
        <p className="empty">All caught up. Every past class is marked.</p>
      )}
      {classes.map((fencingClass) => (
        <section key={fencingClass.id} className="group">
          <div className="group-header">
            <h2>{fencingClass.name}</h2>
            <span className="muted">{formatDateTime(fencingClass.start)}</span>
            <button className="button" onClick={() => markAllPresent(fencingClass.rows)}>
              Mark all present
            </button>
          </div>
          <table className="table">
            <tbody>
              {fencingClass.rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <Link className="row-link" to={`/members/${row.member}`}>{row.member_name}</Link>
                  </td>
                  <td className="cell-right">
                    <StatusSelect value={row.status} onChange={(status) => setStatus(row, status)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  )
}
