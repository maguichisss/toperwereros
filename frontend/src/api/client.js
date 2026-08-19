const API_BASE = '/api'

function getToken() {
  return localStorage.getItem('store_token')
}

export async function request(url, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const res = await fetch(`${API_BASE}${url}`, {
    headers,
    ...options,
  })
  if (res.status === 204) return null
  if (res.status === 401) {
    localStorage.removeItem('store_token')
    window.location.reload()
    return
  }
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
  list: ({ categoryIds, q, page, perPage } = {}) => {
    const params = new URLSearchParams()
    if (categoryIds?.length) params.set('category_ids', categoryIds.join(','))
    if (q) params.set('q', q)
    if (page) params.set('page', page)
    if (perPage) params.set('per_page', perPage)
    const qs = params.toString()
    return request(`/products${qs ? '?' + qs : ''}`)
  },
  listAll: ({ categoryIds, q } = {}) => {
    const params = new URLSearchParams()
    if (categoryIds?.length) params.set('category_ids', categoryIds.join(','))
    if (q) params.set('q', q)
    params.set('export', 'true')
    return request(`/products?${params.toString()}`)
  },
  get: (id) => request(`/products/${id}`),
  create: (data) => request('/products', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id) => request(`/products/${id}`, { method: 'DELETE' }),
}

export const uploadApi = {
  upload: async (file) => {
    const form = new FormData()
    form.append('image', file)
    const headers = {}
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${API_BASE}/upload`, { method: 'POST', headers, body: form })
    if (res.status === 204) return null
    const data = await res.json()
    if (!res.ok) {
      const msg = Array.isArray(data.detail) ? data.detail.map(e => e.msg).join('; ') : (data.detail || 'Upload failed')
      throw new Error(msg)
    }
    return data
  },
}

export const colorsApi = {
  list: () => request('/colors'),
  create: (data) => request('/colors', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/colors/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id) => request(`/colors/${id}`, { method: 'DELETE' }),
}

export const salesApi = {
  create: (data) => request('/sales', { method: 'POST', body: JSON.stringify(data) }),
  list: ({ page, perPage, startDate, endDate } = {}) => {
    const params = new URLSearchParams()
    if (page) params.set('page', page)
    if (perPage) params.set('per_page', perPage)
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)
    const qs = params.toString()
    return request(`/sales${qs ? '?' + qs : ''}`)
  },
  get: (id) => request(`/sales/${id}`),
}

export const customersApi = {
  list: (q) => request(`/customers${q ? '?q=' + encodeURIComponent(q) : ''}`),
  create: (data) => request('/customers', { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => request(`/customers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  get: (id) => request(`/customers/${id}`),
  remove: (id) => request(`/customers/${id}`, { method: 'DELETE' }),
}

export const usersApi = {
  register: (data) => request('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  list: () => request('/auth/users'),
  update: (id, data) => request(`/auth/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  toggleActive: (id, active) => request(`/auth/users/${id}/active`, { method: 'PATCH', body: JSON.stringify({ active }) }),
}

export const rolesApi = {
  list: () => request('/auth/roles'),
  create: (name) => request('/auth/roles', { method: 'POST', body: JSON.stringify({ name }) }),
}

export const authApi = {
  changePassword: (data) => request('/auth/change-password', { method: 'POST', body: JSON.stringify(data) }),
  updateProfile: (data) => request('/auth/profile', { method: 'PATCH', body: JSON.stringify(data) }),
  uploadAvatar: async (file) => {
    const form = new FormData()
    form.append('image', file)
    const headers = {}
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${API_BASE}/auth/avatar`, { method: 'POST', headers, body: form })
    if (res.status === 204) return null
    const data = await res.json()
    if (!res.ok) {
      const msg = Array.isArray(data.detail) ? data.detail.map(e => e.msg).join('; ') : (data.detail || 'Upload failed')
      throw new Error(msg)
    }
    return data
  },
}

export const layawaysApi = {
  create: (data) => request('/layaways', { method: 'POST', body: JSON.stringify(data) }),
  list: ({ status, customerId, page, perPage } = {}) => {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (customerId) params.set('customer_id', customerId)
    if (page) params.set('page', page)
    if (perPage) params.set('per_page', perPage)
    return request(`/layaways?${params.toString()}`)
  },
  get: (id) => request(`/layaways/${id}`),
  update: (id, data) => request(`/layaways/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  addPayment: (id, amount) => request(`/layaways/${id}/payments`, { method: 'POST', body: JSON.stringify({ amount }) }),
  cancel: (id) => request(`/layaways/${id}/cancel`, { method: 'PATCH' }),
  complete: (id) => request(`/layaways/${id}/complete`, { method: 'PATCH' }),
  addItem: (id, productId, quantity = 1) => request(`/layaways/${id}/items`, { method: 'POST', body: JSON.stringify({ productId, quantity }) }),
  removeItem: (id, itemId) => request(`/layaways/${id}/items/${itemId}`, { method: 'DELETE' }),
  updateItem: (id, itemId, quantity) => request(`/layaways/${id}/items/${itemId}`, { method: 'PUT', body: JSON.stringify({ quantity }) }),
}
