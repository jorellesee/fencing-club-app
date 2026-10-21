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
    throw new Error(`${method} /api/${path} failed (${response.status}): ${await response.text()}`)
  }
  return response.status === 204 ? null : response.json()
}
