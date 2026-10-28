// htmx fetches and swaps the HTML. Alpine holds the little state that lives only in
// the browser: which side peek is open, the class filters, and the calendars.

function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]').content
}

function closeModal() {
  document.getElementById('modal').innerHTML = ''
}

// The server sends `HX-Trigger-After-Swap: closeModal` once a dialog’s form has saved.
document.body.addEventListener('closeModal', closeModal)

const FILTERS = ['coach', 'member', 'location', 'weapon']

// A week from 8am to 10pm, like the club's timetable.
const WEEK = {
  initialView: 'timeGridWeek',
  height: '100%',
  slotMinTime: '08:00',
  slotMaxTime: '22:00',
  expandRows: true,
  allDaySlot: false,
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

  // The Classes page's filters, shared by the calendar and the list through the URL.
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

  // The Classes calendar. Managers drag to move or resize classes, and drag across
  // an empty time to make one. Clicking an event opens its panel with htmx.
  Alpine.data('classCalendar', ({ events, editable, moveUrl, newUrl }) => ({
    init() {
      const calendar = new FullCalendar.Calendar(this.$el, {
        ...WEEK,
        headerToolbar: { start: 'prev,next today', center: 'title', end: 'timeGridWeek,timeGridDay' },
        events: eventsFrom(events, () => new URLSearchParams(window.location.search)),
        editable,
        selectable: editable,
        eventDrop: save,
        eventResize: save,
        select(info) {
          calendar.unselect()
          const query = new URLSearchParams({ start: info.start.toISOString(), end: info.end.toISOString() })
          htmx.ajax('GET', `${newUrl}?${query}`, { target: '#modal' })
        },
        eventClick(info) {
          htmx.ajax('GET', info.event.extendedProps.panel, { target: '#panel' })
        },
      })
      calendar.render()

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

      const refetch = () => calendar.refetchEvents()
      document.body.addEventListener('classesChanged', refetch)
      window.addEventListener('filters-changed', refetch)
    },
  }))

  // Private lessons: one coach's week. Grey times are busy. Dragging across a free
  // time opens the request form.
  Alpine.data('lessonCalendar', ({ events, newUrl }) => ({
    coach: '',

    init() {
      this.coach = this.$refs.coach.value
      const calendar = new FullCalendar.Calendar(this.$refs.calendar, {
        ...WEEK,
        headerToolbar: { start: 'prev,next today', center: 'title', end: '' },
        events: eventsFrom(events, () => new URLSearchParams({ coach: this.coach })),
        selectable: true,
        selectOverlap: false,
        selectAllow: (info) => info.start > new Date(),
        select: (info) => {
          calendar.unselect()
          const query = new URLSearchParams({
            coach: this.coach, start: info.start.toISOString(), end: info.end.toISOString(),
          })
          htmx.ajax('GET', `${newUrl}?${query}`, { target: '#modal' })
        },
      })
      calendar.render()
      this.$watch('coach', () => calendar.refetchEvents())
      document.body.addEventListener('lessonsChanged', () => calendar.refetchEvents())
    },
  }))
})
