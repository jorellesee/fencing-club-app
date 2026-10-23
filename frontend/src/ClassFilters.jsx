import { useEffect, useState } from 'react'
import { api } from './api'
import { NO_FILTERS } from './classes'

export default function ClassFilters({ filters, onChange }) {
  const [coaches, setCoaches] = useState([])
  const [members, setMembers] = useState([])
  const [locations, setLocations] = useState([])

  useEffect(() => {
    api('classes/coaches/').then(setCoaches)
    api('members/').then(setMembers)
    api('classes/locations/').then(setLocations)
  }, [])

  function set(key, value) {
    onChange({ ...filters, [key]: value })
  }

  const active = Object.values(filters).some(Boolean)

  return (
    <div className="filters">
      <select className="filter" value={filters.coach} onChange={(e) => set('coach', e.target.value)}>
        <option value="">All coaches</option>
        {coaches.map((name) => (
          <option key={name} value={name}>{name}</option>
        ))}
      </select>
      <select className="filter" value={filters.member} onChange={(e) => set('member', e.target.value)}>
        <option value="">All members</option>
        {members.map((m) => (
          <option key={m.id} value={m.id}>{m.name}</option>
        ))}
      </select>
      <select className="filter" value={filters.location} onChange={(e) => set('location', e.target.value)}>
        <option value="">All locations</option>
        {locations.map((name) => (
          <option key={name} value={name}>{name}</option>
        ))}
      </select>
      {active && (
        <button className="button" onClick={() => onChange(NO_FILTERS)}>Clear</button>
      )}
    </div>
  )
}
