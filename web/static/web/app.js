// htmx fetches and swaps the HTML. Alpine holds the little state that lives only in
// the browser: which side peek is open, the session filters, and the calendars.

function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]').content
}

function closeModal() {
  document.getElementById('modal').innerHTML = ''
}

// The server sends `HX-Trigger-After-Swap: closeModal` once a dialog’s form has saved.
document.body.addEventListener('closeModal', closeModal)

const FILTERS = ['coach', 'member', 'location', 'category', 'weapon', 'size']

// Below this width the app uses its phone layout. Keep in step with app.css.
const phone = window.matchMedia('(max-width: 768px)')

// From 8am to 10pm, like the club's timetable. A week on a computer. On a phone,
// three days with hour-high rows, so the whole day fits on screen without scrolling.
// `views` is the view switcher shown on a computer.
function timetable(views = '') {
  const base = {
    height: '100%',
    slotMinTime: '08:00',
    slotMaxTime: '22:00',
    expandRows: true,
    allDaySlot: false,
  }
  if (!phone.matches) {
    return {
      ...base,
      initialView: 'timeGridWeek',
      headerToolbar: { start: 'prev,next today', center: 'title', end: views },
      // A month's days are too short to drag an end time in, and a busy day shows
      // a few sessions and "+N more".
      views: { dayGridMonth: { eventDurationEditable: false, dayMaxEvents: true } },
    }
  }
  return {
    ...base,
    initialView: 'threeDays',
    views: { threeDays: { type: 'timeGrid', duration: { days: 3 }, buttonText: '3 days' } },
    headerToolbar: { start: 'title', center: '', end: 'today prev,next' },
    titleFormat: { month: 'short', day: 'numeric' },
    dayHeaderFormat: { weekday: 'short', day: 'numeric' },
    slotDuration: '01:00',
    snapDuration: '00:30',
    longPressDelay: 300,
  }
}

// Renders a FullCalendar, and rebuilds it on the same date whenever the window
// crosses the phone breakpoint. Returns a function that gives the current one.
function mountCalendar(el, options) {
  let calendar
  const mount = () => {
    const date = calendar?.getDate()
    calendar?.destroy()
    calendar = new FullCalendar.Calendar(el, { ...options(), ...(date && { initialDate: date }) })
    calendar.render()
  }
  mount()
  phone.addEventListener('change', mount)
  return () => calendar
}

// Fetches a JSON list of events for the dates FullCalendar is showing.
function eventsFrom(url, params = () => new URLSearchParams()) {
  return async (info) => {
    const query = params()
    query.set('start', info.start.toISOString())
    query.set('end', info.end.toISOString())
    const response = await fetch(`${url}?${query}`)
    if (!response.ok) throw new Error(`Couldn't load the calendar (${response.status})`)
    return response.json()
  }
}

document.addEventListener('alpine:init', () => {
  // A side peek, like Notion's. Each panel sets `selected` when htmx swaps it into
  // #panel, so the matching row is highlighted. With `param`, the open one is also
  // kept in the URL, e.g. /members/?member=3, so it can be linked to and reloaded.
  Alpine.data('peek', (selected = null, param = null) => ({
    selected,

    init() {
      if (!param) return
      this.$watch('selected', (id) => {
        const url = new URL(window.location)
        if (id) url.searchParams.set(param, id)
        else url.searchParams.delete(param)
        history.replaceState(history.state, '', url)
      })
    },

    close() {
      this.selected = null
      document.getElementById('panel').innerHTML = ''
    },
  }))

  // The Sessions page's filters, shared by the calendar and the list through the URL.
  // Changing one updates the URL and fires `filters-changed`, which the calendar
  // and the list's htmx trigger listen for.
  Alpine.data('filters', (initial) => ({
    ...initial,

    get query() {
      const params = new URLSearchParams()
      for (const key of FILTERS) if (this[key]) params.set(key, this[key])
      return params.toString()
    },

    get active() {
      return FILTERS.some((key) => this[key])
    },

    clear() {
      for (const key of FILTERS) this[key] = ''
    },

    init() {
      this.$watch('query', (query) => {
        history.replaceState(history.state, '', query ? `?${query}` : window.location.pathname)
        this.$dispatch('filters-changed')
      })
    },
  }))

  // The Sessions calendar. Managers drag to move or resize sessions, and drag across
  // an empty time to make one. Clicking an event opens its panel with htmx, and
  // clicking a day in the month view opens that day.
  Alpine.data('sessionCalendar', ({ events, editable, moveUrl, newUrl }) => ({
    init() {
      const calendar = mountCalendar(this.$el, () => ({
        ...timetable('dayGridMonth,timeGridWeek,timeGridDay'),
        events: eventsFrom(events, () => new URLSearchParams(window.location.search)),
        editable,
        selectable: editable,
        // Day names link to that day. Not on a phone, which has no way back.
        navLinks: !phone.matches,
        eventDrop: save,
        eventResize: save,
        dateClick(info) {
          if (info.view.type === 'dayGridMonth') calendar().changeView('timeGridDay', info.date)
        },
        select(info) {
          calendar().unselect()
          // A month's selection is whole days, with no times for a session.
          if (info.allDay) return
          const query = new URLSearchParams({ start: info.start.toISOString(), end: info.end.toISOString() })
          htmx.ajax('GET', `${newUrl}?${query}`, { target: '#modal' })
        },
        eventClick(info) {
          htmx.ajax('GET', info.event.extendedProps.panel, { target: '#panel' })
        },
      }))

      async function save(info) {
        const response = await fetch(moveUrl.replace('0', info.event.id), {
          method: 'POST',
          headers: { 'X-CSRFToken': csrfToken() },
          body: new URLSearchParams({
            start: info.event.start.toISOString(),
            end: info.event.end.toISOString(),
          }),
        })
        if (!response.ok) info.revert()
      }

      const refetch = () => calendar().refetchEvents()
      document.body.addEventListener('sessionsChanged', refetch)
      window.addEventListener('filters-changed', refetch)
    },
  }))

  // Private lessons: one coach's week. Grey times are busy. Dragging across a free
  // time opens the request form.
  Alpine.data('lessonCalendar', ({ events, newUrl }) => ({
    coach: '',

    init() {
      this.coach = this.$refs.coach.value
      const calendar = mountCalendar(this.$refs.calendar, () => ({
        ...timetable(),
        events: eventsFrom(events, () => new URLSearchParams({ coach: this.coach })),
        selectable: true,
        selectOverlap: false,
        selectAllow: (info) => info.start > new Date(),
        select: (info) => {
          calendar().unselect()
          const query = new URLSearchParams({
            coach: this.coach, start: info.start.toISOString(), end: info.end.toISOString(),
          })
          htmx.ajax('GET', `${newUrl}?${query}`, { target: '#modal' })
        },
      }))
      this.$watch('coach', () => calendar().refetchEvents())
      document.body.addEventListener('lessonsChanged', () => calendar().refetchEvents())
    },
  }))
})
