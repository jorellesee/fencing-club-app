import { useRef, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import classicThemePlugin from '@fullcalendar/react/themes/classic'
import timeGridPlugin from '@fullcalendar/react/timegrid'
import interactionPlugin from '@fullcalendar/react/interaction'
import { api } from './api'
import AttendancePanel from './AttendancePanel'
import { useMe } from './auth'
import ClassesHeader from './ClassesHeader'
import ClassFilters from './ClassFilters'
import ClassForm from './ClassForm'
import { attendanceCount, classParams } from './classes'
import LessonRequestPanel from './LessonRequestPanel'

function toEvent(fencingClass) {
  return {
    id: String(fencingClass.id),
    title: `${fencingClass.name} (${attendanceCount(fencingClass)})`,
    start: fencingClass.start,
    end: fencingClass.end,
  }
}

// Pending lesson requests sit beside the classes, dashed and yellow, until answered.
function toRequestEvent(lesson, me) {
  return {
    id: `request-${lesson.id}`,
    title: me.role === 'member'
      ? `Requested: lesson with ${lesson.coach_name}`
      : `Lesson request: ${lesson.member_name}`,
    start: lesson.start,
    end: lesson.end,
    editable: false,
    className: 'event-request',
    color: 'var(--tag-yellow-bg)',
    contrastColor: 'var(--tag-yellow-text)',
    extendedProps: { lesson },
  }
}

// Requests have a coach and a member but no location or weapon, so those filters hide them.
function requestParams(me, filters, info) {
  if (me.role === 'manager' && (filters.location || filters.weapon)) return null
  const params = new URLSearchParams({
    status: 'pending', start: info.start.toISOString(), end: info.end.toISOString(),
  })
  if (me.role === 'manager') {
    if (filters.coach) params.set('coach', filters.coach)
    if (filters.member) params.set('member', filters.member)
  }
  return params
}

export default function CalendarPage({ filters, onFiltersChange }) {
  const me = useMe()
  const isManager = me.role === 'manager'
  const calendarRef = useRef(null)
  const [selectedId, setSelectedId] = useState(null)
  const [selectedRequest, setSelectedRequest] = useState(null)
  const [error, setError] = useState('')
  // null when closed; {} for the button, { start, end } for a dragged slot.
  const [newClass, setNewClass] = useState(null)

  function refresh() {
    calendarRef.current.getApi().refetchEvents()
  }

  async function loadClasses(info) {
    const params = classParams(me, filters)
    params.set('start', info.start.toISOString())
    params.set('end', info.end.toISOString())
    const lessonParams = requestParams(me, filters, info)
    try {
      const [classes, lessons] = await Promise.all([
        api(`classes/?${params}`),
        lessonParams ? api(`lesson-requests/?${lessonParams}`) : [],
      ])
      setError('')
      return [...classes.map(toEvent), ...lessons.map((lesson) => toRequestEvent(lesson, me))]
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

  function chooseSlot(info) {
    calendarRef.current.getApi().unselect()
    setNewClass({ start: info.start, end: info.end })
  }

  function openEvent(event) {
    const lesson = event.extendedProps.lesson
    setSelectedRequest(lesson ?? null)
    setSelectedId(lesson ? null : event.id)
  }

  function classCreated(saved) {
    setNewClass(null)
    refresh()
    setSelectedId(String(saved.id))
  }

  return (
    <div className="calendar-page">
      <div className="calendar">
        <ClassesHeader />
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
            eventClick={(info) => openEvent(info.event)}
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
      {selectedRequest && (
        <LessonRequestPanel
          key={selectedRequest.id}
          lesson={selectedRequest}
          onChange={refresh}
          onAccepted={(classId) => {
            setSelectedRequest(null)
            setSelectedId(classId)
          }}
          onClose={() => setSelectedRequest(null)}
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
