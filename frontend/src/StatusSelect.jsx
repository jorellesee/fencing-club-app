const STATUSES = ['enrolled', 'present', 'absent', 'excused']

export default function StatusSelect({ value, onChange, readOnly }) {
  if (readOnly) return <span className={`tag status-${value}`}>{value}</span>
  return (
    <select
      className={`tag tag-select status-${value}`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {STATUSES.map((status) => (
        <option key={status} value={status}>{status}</option>
      ))}
    </select>
  )
}
