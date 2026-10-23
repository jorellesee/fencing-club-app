import { useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import classicThemePlugin from '@fullcalendar/react/themes/classic'
import timeGridPlugin from '@fullcalendar/react/timegrid'
import interactionPlugin from '@fullcalendar/react/interaction'
import { api } from './api'
import AttendancePanel from './AttendancePanel'
import { useMe } from './auth'
import ClassFilters from './ClassFilters'
import ClassForm from './ClassForm'
import { attendanceCount, classParams } from './classes'

function toEvent(fencingClass) {
  return {
    id: String(fencingClass.id),
    title: `${fencingClass.name} (${attendanceCount(fencingClass)})`,
    start: fencingClass.start,
    end: fencingClass.end,
  }
}

export default function CalendarPage({ filters, onFiltersChange, onChange }) {
  const me = useMe()
  const isManager = me.role === 'manager'
  const calendarRef = useRef(null)
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState('')
  // null when closed; {} for the button, { start, end } for a dragged slot.
  const [newClass, setNewClass] = useState(null)

  function refresh() {
    calendarRef.current.getApi().refetchEvents()
    onChange()
  }

  async function loadClasses(info) {
    const params = classParams(me, filters)
    params.set('start', info.start.toISOString())
    params.set('end', info.end.toISOString())
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
      onChange()
    } catch (err) {
      setError(err.message)
      info.revert()
    }
  }

  function chooseSlot(info) {
    calendarRef.current.getApi().unselect()
    setNewClass({ start: info.start, end: info.end })
  }

  function classCreated(saved) {
    setNewClass(null)
    refresh()
    setSelectedId(String(saved.id))
  }

  return (
    <div className="calendar-page">
      <div className="calendar">
        <h1 className="page-title">
          <span className="page-icon">📅</span>{isManager ? 'Calendar' : 'My calendar'}
        </h1>
        {error && <p className="error">{error}</p>}
        {isManager && (
          <div className="toolbar">
            <ClassFilters filters={filters} onChange={onFiltersChange} />
            <button className="button primary" onClick={() => setNewClass({})}>+ New class</button>
          </div>
        )}
        <div className="calendar-body">
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
            slotMinTime="08:00"
            slotMaxTime="22:00"
            expandRows
            allDaySlot={false}
            events={loadClasses}
            editable={isManager}
            selectable={isManager}
            eventDrop={saveTimes}
            eventResize={saveTimes}
            select={chooseSlot}
            eventClick={(info) => setSelectedId(info.event.id)}
          />
        </div>
      </div>
      {newClass && (
        <ClassForm
          start={newClass.start}
          end={newClass.end}
          onSaved={classCreated}
          onClose={() => setNewClass(null)}
        />
      )}
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
