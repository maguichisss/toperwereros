const API_BASE = '/api'

async function request(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (res.status === 204) return null
  const data = await res.json()
  if (!res.ok) {
    const msg = Array.isArray(data.detail) ? data.detail.map(e => e.msg).join('; ') : (data.detail || 'Request failed')
    throw new Error(msg)
  }
  return data
}

export const categoriesApi = {
  list: () => request('/categories'),
  create: (name) => request('/categories', { method: 'POST', body: JSON.stringify({ name }) }),
  update: (id, data) => request(`/categories/${id}`, { method: 'PUT', body: JSON.stringify(typeof data === 'string' ? { name: data } : data) }),
  remove: (id) => request(`/categories/${id}`, { method: 'DELETE' }),
}

export const productsApi = {
  list: (categoryIds) => request(categoryIds?.length ? `/products?category_ids=${categoryIds.join(',')}` : '/products'),
  get: (id) => request(`/products/${id}`),
  create: (data) => request('/products', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id) => request(`/products/${id}`, { method: 'DELETE' }),
}

export const uploadApi = {
  upload: (file) => {
    const form = new FormData()
    form.append('image', file)
    return fetch(`${API_BASE}/upload`, { method: 'POST', body: form }).then((r) => r.json())
  },
}

export const colorsApi = {
  list: () => request('/colors'),
  create: (data) => request('/colors', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/colors/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id) => request(`/colors/${id}`, { method: 'DELETE' }),
}
