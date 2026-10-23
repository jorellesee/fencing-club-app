// Shows the API's validation errors, or the raw message if it wasn't one.
export default function FormErrors({ error }) {
  if (!error) return null
  if (!error.data) return <p className="error">{error.message}</p>
  return (
    <div className="error">
      {Object.entries(error.data).map(([field, messages]) => (
        <div key={field}>
          {field !== 'non_field_errors' && field !== 'detail' && <strong>{field}: </strong>}
          {[].concat(messages).join(' ')}
        </div>
      ))}
    </div>
  )
}
