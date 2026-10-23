function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[2]) : ''
}

export async function api(path, { method = 'GET', body } = {}) {
  const response = await fetch(`/api/${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) {
    const text = await response.text()
    const error = new Error(`${method} /api/${path} failed (${response.status}): ${text}`)
    // Validation errors come back as JSON, e.g. { "name": ["This field is required."] }.
    try {
      error.data = JSON.parse(text)
    } catch {
      error.data = null
    }
    throw error
  }
  return response.status === 204 ? null : response.json()
}
