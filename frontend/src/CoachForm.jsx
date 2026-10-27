import { useState } from 'react'
import { api } from './api'
import { WEAPONS } from './format'
import FormErrors from './FormErrors'
import Modal from './Modal'

// Adds a coach, or edits `coach` when one is given.
export default function CoachForm({ coach, onSaved, onClose }) {
  const editing = Boolean(coach)
  const [form, setForm] = useState(() => ({
    name: coach?.name ?? '',
    email: coach?.email ?? '',
    phone: coach?.phone ?? '',
    weapon: coach?.weapon ?? '',
    active: coach?.active ?? true,
  }))
  const [error, setError] = useState(null)

  function set(key) {
    return (event) => setForm({ ...form, [key]: event.target.value })
  }

  async function submit(event) {
    event.preventDefault()
    try {
      onSaved(
        editing
          ? await api(`coaches/${coach.id}/`, { method: 'PATCH', body: form })
          : await api('coaches/', { method: 'POST', body: form }),
      )
    } catch (err) {
      setError(err)
    }
  }

  return (
    <Modal title={editing ? 'Edit coach' : 'New coach'} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <label>
          Name
          <input value={form.name} onChange={set('name')} autoFocus required />
        </label>
        <div className="form-row">
          <label>
            Email
            <input type="email" value={form.email} onChange={set('email')} />
          </label>
          <label>
            Phone
            <input type="tel" value={form.phone} onChange={set('phone')} />
          </label>
        </div>
        <label>
          Weapon
          <select value={form.weapon} onChange={set('weapon')}>
            <option value="">None</option>
            {Object.entries(WEAPONS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={form.active}
            onChange={(e) => setForm({ ...form, active: e.target.checked })}
          />
          Active
        </label>
        <FormErrors error={error} />
        <div className="form-actions">
          <button type="button" className="button" onClick={onClose}>Cancel</button>
          <button className="button primary">{editing ? 'Save' : 'Add coach'}</button>
        </div>
      </form>
    </Modal>
  )
}
