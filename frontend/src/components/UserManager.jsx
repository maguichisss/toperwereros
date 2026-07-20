import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { usersApi, request } from '../api/client.js'

const ROLES = [
  { id: 4, name: 'admin' },
  { id: 5, name: 'employee' },
  { id: 6, name: 'viewer' },
]

export default function UserManager() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState([])
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [roleId, setRoleId] = useState(5)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    fetchUsers()
  }, [])

  async function fetchUsers() {
    try {
      const data = await request('/auth/users')
      setUsers(data)
    } catch {}
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setBusy(true)
    try {
      await usersApi.register({ username, password, email: email || null, role_id: roleId })
      setSuccess(`Usuario "${username}" creado`)
      setUsername('')
      setPassword('')
      setEmail('')
      setRoleId(5)
      fetchUsers()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ maxWidth: 600 }}>
      <form onSubmit={handleSubmit} style={{ background: '#fff', borderRadius: 8, padding: '1.5rem', boxShadow: '0 1px 4px rgba(0,0,0,0.1)', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>Nuevo Usuario</h2>
        <div className="form-row">
          <div className="form-group">
            <label>Usuario</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)}
              autoComplete="off" autoCorrect="off" spellCheck="false" required />
          </div>
          <div className="form-group">
            <label>Contraseña</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              autoComplete="off" autoCorrect="off" spellCheck="false" required />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              autoComplete="off" autoCorrect="off" spellCheck="false" />
          </div>
          <div className="form-group">
            <label>Rol</label>
            <select value={roleId} onChange={(e) => setRoleId(Number(e.target.value))}>
              {ROLES.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
        </div>
        {error && <p className="error-text">{error}</p>}
        {success && <p style={{ color: '#43a047', fontWeight: 600, marginTop: '0.5rem' }}>{success}</p>}
        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Creando...' : 'Crear Usuario'}
          </button>
        </div>
      </form>

      <h2 style={{ fontSize: '1.1rem', marginBottom: '0.75rem' }}>Usuarios existentes</h2>
      <div style={{ background: '#fff', borderRadius: 8, overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.1)' }}>
        {users.map((u) => (
          <div key={u.id} style={{ display: 'flex', alignItems: 'center', padding: '0.75rem', borderBottom: '1px solid #eee', gap: '0.5rem' }}>
            <span style={{ fontWeight: 600, flex: 1 }}>{u.username}</span>
            <span style={{ color: '#888', fontSize: '0.85rem' }}>{u.email || '—'}</span>
            <span className={`chip ${u.role_name === 'admin' ? 'chip-active' : ''}`} style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem' }}>
              {u.role_name}
            </span>
            {u.id === currentUser?.id && <span style={{ color: '#1a73e8', fontSize: '0.8rem' }}>(tú)</span>}
          </div>
        ))}
        {users.length === 0 && <p className="empty-state">Sin usuarios</p>}
      </div>
    </div>
  )
}
