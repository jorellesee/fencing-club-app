import { useEffect, useState } from 'react'
import { api } from './api'
import { toDateInput, toTimeInput } from './format'
import FormErrors from './FormErrors'
import Modal from './Modal'

// Without a chosen time, suggest an hour-long class starting at the next full hour.
function defaultTimes() {
  const start = new Date()
  start.setHours(start.getHours() + 1, 0, 0, 0)
  return { start, end: new Date(start.getTime() + 60 * 60 * 1000) }
}

export default function ClassForm({ start, end, onSaved, onClose }) {
  const times = start ? { start, end } : defaultTimes()
  const [form, setForm] = useState({
    name: '',
    date: toDateInput(times.start),
    startTime: toTimeInput(times.start),
    endTime: toTimeInput(times.end),
    coach: '',
    location: '',
    capacity: '',
    notes: '',
  })
  const [coaches, setCoaches] = useState([])
  const [locations, setLocations] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    api('classes/coaches/').then(setCoaches)
    api('classes/locations/').then(setLocations)
  }, [])

  function set(key) {
    return (event) => setForm({ ...form, [key]: event.target.value })
  }

  async function submit(event) {
    event.preventDefault()
    try {
      const saved = await api('classes/', {
        method: 'POST',
        body: {
          name: form.name,
          start: new Date(`${form.date}T${form.startTime}`).toISOString(),
          end: new Date(`${form.date}T${form.endTime}`).toISOString(),
          coach: form.coach,
          location: form.location,
          capacity: form.capacity === '' ? null : Number(form.capacity),
          notes: form.notes,
        },
      })
      onSaved(saved)
    } catch (err) {
      setError(err)
    }
  }

  return (
    <Modal title="New class" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <label>
          Name
          <input value={form.name} onChange={set('name')} autoFocus required />
        </label>
        <div className="form-row">
          <label>
            Date
            <input type="date" value={form.date} onChange={set('date')} required />
          </label>
          <label>
            Start
            <input type="time" value={form.startTime} onChange={set('startTime')} required />
          </label>
          <label>
            End
            <input type="time" value={form.endTime} onChange={set('endTime')} required />
          </label>
        </div>
        <div className="form-row">
          <label>
            Coach
            <input value={form.coach} onChange={set('coach')} list="coach-options" />
          </label>
          <label>
            Location
            <input value={form.location} onChange={set('location')} list="location-options" />
          </label>
          <label>
            Capacity
            <input type="number" min="1" value={form.capacity} onChange={set('capacity')} />
          </label>
        </div>
        <datalist id="coach-options">
          {coaches.map((name) => <option key={name} value={name} />)}
        </datalist>
        <datalist id="location-options">
          {locations.map((name) => <option key={name} value={name} />)}
        </datalist>
        <label>
          Notes
          <textarea value={form.notes} onChange={set('notes')} />
        </label>
        <FormErrors error={error} />
        <div className="form-actions">
          <button type="button" className="button" onClick={onClose}>Cancel</button>
          <button className="button primary">Create class</button>
        </div>
      </form>
    </Modal>
  )
}
