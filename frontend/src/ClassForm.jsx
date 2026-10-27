import { useEffect, useState } from 'react'
import { api } from './api'
import { generateName } from './classes'
import { CLASS_WEAPONS, toDateInput, toTimeInput } from './format'
import FormErrors from './FormErrors'
import Modal from './Modal'

// Without a chosen time, suggest an hour-long class starting at the next full hour.
function defaultTimes() {
  const start = new Date()
  start.setHours(start.getHours() + 1, 0, 0, 0)
  return { start, end: new Date(start.getTime() + 60 * 60 * 1000) }
}

function initialForm(fencingClass, start, end) {
  if (fencingClass) {
    return {
      name: fencingClass.name,
      date: toDateInput(new Date(fencingClass.start)),
      startTime: toTimeInput(new Date(fencingClass.start)),
      endTime: toTimeInput(new Date(fencingClass.end)),
      coach: fencingClass.coach ?? '',
      location: fencingClass.location,
      weapon: fencingClass.weapon,
      capacity: fencingClass.capacity ?? '',
      notes: fencingClass.notes,
    }
  }
  const times = start ? { start, end } : defaultTimes()
  return {
    name: '',
    date: toDateInput(times.start),
    startTime: toTimeInput(times.start),
    endTime: toTimeInput(times.end),
    coach: '',
    location: '',
    weapon: '',
    capacity: '',
    notes: '',
  }
}

// Creates a class, or edits `fencingClass` when one is given.
export default function ClassForm({ fencingClass, start, end, onSaved, onClose }) {
  const editing = Boolean(fencingClass)
  const [form, setForm] = useState(() => initialForm(fencingClass, start, end))
  const [applyToFollowing, setApplyToFollowing] = useState(false)
  const [coaches, setCoaches] = useState([])
  const [locations, setLocations] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    api('coaches/').then(setCoaches)
    api('classes/locations/').then(setLocations)
  }, [])

  function set(key) {
    return (event) => setForm({ ...form, [key]: event.target.value })
  }

  async function submit(event) {
    event.preventDefault()
    const shared = {
      name: form.name,
      coach: form.coach === '' ? null : Number(form.coach),
      location: form.location,
      weapon: form.weapon,
      capacity: form.capacity === '' ? null : Number(form.capacity),
    }
    const body = {
      ...shared,
      start: new Date(`${form.date}T${form.startTime}`).toISOString(),
      end: new Date(`${form.date}T${form.endTime}`).toISOString(),
      notes: form.notes,
    }
    try {
      const saved = editing
        ? await api(`classes/${fencingClass.id}/`, { method: 'PATCH', body })
        : await api('classes/', { method: 'POST', body })
      if (applyToFollowing) {
        await api(`classes/${saved.id}/update-following/`, { method: 'POST', body: shared })
      }
      onSaved(saved)
    } catch (err) {
      setError(err)
    }
  }

  return (
    <Modal title={editing ? 'Edit class' : 'New class'} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <label>
          Name
          <div className="input-with-button">
            <input value={form.name} onChange={set('name')} autoFocus required />
            <button
              type="button"
              className="button"
              title="Name it from the day, weapon and location"
              onClick={() => setForm({ ...form, name: generateName(form) })}
            >
              Generate
            </button>
          </div>
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
            Weapon
            <select value={form.weapon} onChange={set('weapon')}>
              <option value="">None</option>
              {Object.entries(CLASS_WEAPONS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <label>
            Location
            <input value={form.location} onChange={set('location')} list="location-options" />
          </label>
        </div>
        <div className="form-row">
          <label>
            Coach
            <select value={form.coach} onChange={set('coach')}>
              <option value="">None</option>
              {coaches
                .filter((coach) => coach.active || coach.id === fencingClass?.coach)
                .map((coach) => <option key={coach.id} value={coach.id}>{coach.name}</option>)}
            </select>
          </label>
          <label>
            Capacity
            <input type="number" min="1" value={form.capacity} onChange={set('capacity')} />
          </label>
        </div>
        <datalist id="location-options">
          {locations.map((name) => <option key={name} value={name} />)}
        </datalist>
        <label>
          Notes
          <textarea value={form.notes} onChange={set('notes')} />
        </label>
        {fencingClass?.series && (
          <label className="checkbox">
            <input
              type="checkbox"
              checked={applyToFollowing}
              onChange={(e) => setApplyToFollowing(e.target.checked)}
            />
            Also change the name, weapon, location, coach and capacity of all following classes in this weekly series
          </label>
        )}
        <FormErrors error={error} />
        <div className="form-actions">
          <button type="button" className="button" onClick={onClose}>Cancel</button>
          <button className="button primary">{editing ? 'Save' : 'Create class'}</button>
        </div>
      </form>
    </Modal>
  )
}
