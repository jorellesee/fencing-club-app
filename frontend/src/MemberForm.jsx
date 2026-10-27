import { useEffect, useState } from 'react'
import { api } from './api'
import { useMe } from './auth'
import { WEAPONS } from './format'
import FormErrors from './FormErrors'
import Modal from './Modal'

// What a member may change about themselves. The backend allows the same.
const OWN_FIELDS = ['name', 'phone', 'weapon']

// Adds a member, or edits `member` when one is given.
export default function MemberForm({ member, onSaved, onClose }) {
  const me = useMe()
  const isManager = me.role === 'manager'
  const editing = Boolean(member)
  const [form, setForm] = useState(() => ({
    name: member?.name ?? '',
    email: member?.email ?? '',
    phone: member?.phone ?? '',
    weapon: member?.weapon ?? '',
    primary_coach: member?.primary_coach ?? '',
    active: member?.active ?? true,
  }))
  const [coaches, setCoaches] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    if (isManager) api('coaches/').then(setCoaches)
  }, [isManager])

  function set(key) {
    return (event) => setForm({ ...form, [key]: event.target.value })
  }

  async function submit(event) {
    event.preventDefault()
    const all = { ...form, primary_coach: form.primary_coach === '' ? null : Number(form.primary_coach) }
    const body = isManager ? all : Object.fromEntries(OWN_FIELDS.map((key) => [key, all[key]]))
    try {
      onSaved(
        editing
          ? await api(`members/${member.id}/`, { method: 'PATCH', body })
          : await api('members/', { method: 'POST', body }),
      )
    } catch (err) {
      setError(err)
    }
  }

  return (
    <Modal title={editing ? 'Edit member' : 'New member'} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <label>
          Name
          <input value={form.name} onChange={set('name')} autoFocus required />
        </label>
        <div className="form-row">
          <label>
            Email
            <input type="email" value={form.email} onChange={set('email')} disabled={!isManager} />
            {!isManager && <span className="hint">It’s also your login, so ask a manager to change it.</span>}
          </label>
          <label>
            Phone
            <input type="tel" value={form.phone} onChange={set('phone')} />
          </label>
        </div>
        <div className="form-row">
          <label>
            Weapon
            <select value={form.weapon} onChange={set('weapon')}>
              <option value="">None</option>
              {Object.entries(WEAPONS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          {isManager && (
            <label>
              Primary coach
              <select value={form.primary_coach} onChange={set('primary_coach')}>
                <option value="">None</option>
                {coaches
                  .filter((coach) => coach.active || coach.id === member?.primary_coach)
                  .map((coach) => <option key={coach.id} value={coach.id}>{coach.name}</option>)}
              </select>
            </label>
          )}
        </div>
        {isManager && (
          <label className="checkbox">
            <input
              type="checkbox"
              checked={form.active}
              onChange={(e) => setForm({ ...form, active: e.target.checked })}
            />
            Active
          </label>
        )}
        <FormErrors error={error} />
        <div className="form-actions">
          <button type="button" className="button" onClick={onClose}>Cancel</button>
          <button className="button primary">{editing ? 'Save' : 'Add member'}</button>
        </div>
      </form>
    </Modal>
  )
}
