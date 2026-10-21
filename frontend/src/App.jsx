import { useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import classicThemePlugin from '@fullcalendar/react/themes/classic'
import timeGridPlugin from '@fullcalendar/react/timegrid'
import interactionPlugin from '@fullcalendar/react/interaction'
import '@fullcalendar/react/skeleton.css'
import '@fullcalendar/react/themes/classic/theme.css'
import '@fullcalendar/react/themes/classic/palette.css'
import { api } from './api'
import AttendancePanel from './AttendancePanel'
import './App.css'

function toEvent(fencingClass) {
  const limit = fencingClass.capacity ?? fencingClass.member_count
  return {
    id: String(fencingClass.id),
    title: `${fencingClass.name} (${fencingClass.present_count}/${limit})`,
    start: fencingClass.start,
    end: fencingClass.end,
  }
}

export default function App() {
  const calendarRef = useRef(null)
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState('')

  function refresh() {
    calendarRef.current.getApi().refetchEvents()
  }

  async function loadClasses(info) {
    const params = new URLSearchParams({
      start: info.start.toISOString(),
      end: info.end.toISOString(),
    })
    try {
      const classes = await api(`classes/?${params}`)
      setError('')
      return classes.map(toEvent)
    } catch (err) {
      setError(err.message)
      return []
    }
  }

  async function saveTimes(info) {
    try {
      await api(`classes/${info.event.id}/`, {
        method: 'PATCH',
        body: {
          start: info.event.start.toISOString(),
          end: info.event.end.toISOString(),
        },
      })
    } catch (err) {
      setError(err.message)
      info.revert()
    }
  }

  async function createClass(info) {
    calendarRef.current.getApi().unselect()
    const name = window.prompt('Class name')
    if (!name) return
    try {
      await api('classes/', {
        method: 'POST',
        body: { name, start: info.start.toISOString(), end: info.end.toISOString() },
      })
      refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="layout">
      <main className="calendar">
        {error && <p className="error">{error}</p>}
        <FullCalendar
          ref={calendarRef}
          plugins={[classicThemePlugin, timeGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          headerToolbar={{
            start: 'prev,next today',
            center: 'title',
            end: 'timeGridWeek,timeGridDay',
          }}
          height="100%"
          events={loadClasses}
          editable
          selectable
          eventDrop={saveTimes}
          eventResize={saveTimes}
          select={createClass}
          eventClick={(info) => setSelectedId(info.event.id)}
        />
      </main>
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
