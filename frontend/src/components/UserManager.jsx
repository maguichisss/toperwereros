import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { usersApi, rolesApi } from '../api/client.js'
import ConfirmDialog from './ConfirmDialog.jsx'

export default function UserManager() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [roleId, setRoleId] = useState(5)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)

  const [editUser, setEditUser] = useState(null)
  const [editForm, setEditForm] = useState({ username: '', email: '', role_id: 5, password: '' })
  const [editError, setEditError] = useState('')
  const [editBusy, setEditBusy] = useState(false)

  const [confirmToggle, setConfirmToggle] = useState(null)

  useEffect(() => {
    fetchUsers()
    rolesApi.list().then(setRoles).catch(() => {})
  }, [])

  async function fetchUsers() {
    try {
      const data = await usersApi.list()
      setUsers(data)
    } catch {}
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setBusy(true)
    try {
      await usersApi.register({ username: username.trim().toLowerCase(), password, email: email || null, role_id: roleId })
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

  function openEdit(u) {
    setEditUser(u)
    setEditForm({ username: u.username, email: u.email || '', role_id: u.role_id, password: '' })
    setEditError('')
  }

  async function handleEditSubmit(e) {
    e.preventDefault()
    setEditError('')
    setEditBusy(true)
    try {
      const payload = {
        username: editForm.username.trim().toLowerCase(),
        email: editForm.email || null,
        role_id: editForm.role_id,
      }
      if (editForm.password) payload.password = editForm.password
      await usersApi.update(editUser.id, payload)
      setEditUser(null)
      fetchUsers()
    } catch (err) {
      setEditError(err.message)
    } finally {
      setEditBusy(false)
    }
  }

  async function handleToggleActive() {
    if (!confirmToggle) return
    try {
      await usersApi.toggleActive(confirmToggle.id, !confirmToggle.active)
      setConfirmToggle(null)
      fetchUsers()
    } catch (err) {
      setError(err.message)
      setConfirmToggle(null)
    }
  }

  const isSelf = (u) => u.id === currentUser?.id

  return (
    <div style={{ maxWidth: 600 }}>
      <form onSubmit={handleSubmit} style={{ background: 'var(--bg-card)', borderRadius: 8, padding: '1.5rem', boxShadow: '0 1px 4px var(--shadow)', marginBottom: '1.5rem' }}>
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
              {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
        </div>
        {error && <p className="error-text">{error}</p>}
        {success && <p style={{ color: 'var(--success)', fontWeight: 600, marginTop: '0.5rem' }}>{success}</p>}
        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Creando...' : 'Crear Usuario'}
          </button>
        </div>
      </form>

      <h2 style={{ fontSize: '1.1rem', marginBottom: '0.75rem' }}>Usuarios existentes</h2>
      <div style={{ background: 'var(--bg-card)', borderRadius: 8, overflow: 'hidden', boxShadow: '0 1px 4px var(--shadow)' }}>
        {users.map((u) => (
          <div key={u.id} style={{ display: 'flex', alignItems: 'center', padding: '0.6rem 0.75rem', borderBottom: '1px solid #eee', gap: '0.5rem', opacity: u.active ? 1 : 0.55 }}>
            <span style={{ fontWeight: 600, flex: 1, textDecoration: u.active ? 'none' : 'line-through' }}>
              {u.username}
              {isSelf(u) && <span style={{ color: 'var(--primary)', fontSize: '0.8rem', marginLeft: '0.3rem' }}>(tú)</span>}
            </span>
            {!u.active && <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem', fontStyle: 'italic' }}>desactivado</span>}
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{u.email || '—'}</span>
            <span className={`chip ${u.role_name === 'admin' ? 'chip-active' : ''}`} style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem' }}>
              {u.role_name}
            </span>
            <button className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }} onClick={() => openEdit(u)}>
              Editar
            </button>
            {!isSelf(u) && (
              <button
                className={`btn ${u.active ? 'btn-danger' : 'btn-primary'}`}
                style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                onClick={() => setConfirmToggle(u)}
              >
                {u.active ? 'Desactivar' : 'Activar'}
              </button>
            )}
          </div>
        ))}
        {users.length === 0 && <p className="empty-state">Sin usuarios</p>}
      </div>

      {editUser && (
        <div className="modal-overlay" onClick={() => setEditUser(null)}>
          <div className="modal" role="dialog" onClick={e => e.stopPropagation()} style={{ maxWidth: 450 }}>
            <h2 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>Editar usuario</h2>
            <form onSubmit={handleEditSubmit}>
              <div className="form-group" style={{ marginBottom: '0.75rem' }}>
                <label>Usuario</label>
                <input type="text" value={editForm.username} onChange={(e) => setEditForm({ ...editForm, username: e.target.value })}
                  autoComplete="off" autoCorrect="off" spellCheck="false" required />
              </div>
              <div className="form-group" style={{ marginBottom: '0.75rem' }}>
                <label>Email</label>
                <input type="email" value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                  autoComplete="off" autoCorrect="off" spellCheck="false" />
              </div>
              {!isSelf(editUser) && (
                <div className="form-group" style={{ marginBottom: '0.75rem' }}>
                  <label>Rol</label>
                  <select value={editForm.role_id} onChange={(e) => setEditForm({ ...editForm, role_id: Number(e.target.value) })}>
                    {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </div>
              )}
              <div className="form-group" style={{ marginBottom: '0.75rem' }}>
                <label>Nueva contraseña (opcional)</label>
                <input type="password" value={editForm.password} onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                  autoComplete="off" autoCorrect="off" spellCheck="false" placeholder="Dejar vacío para no cambiar" />
              </div>
              {editError && <p className="error-text">{editError}</p>}
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setEditUser(null)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={editBusy}>
                  {editBusy ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {confirmToggle && (
        <ConfirmDialog
          title={confirmToggle.active ? 'Desactivar usuario' : 'Activar usuario'}
          message={confirmToggle.active
            ? `¿Desactivar al usuario "${confirmToggle.username}"? No podrá iniciar sesión.`
            : `¿Activar al usuario "${confirmToggle.username}"?`}
          onConfirm={handleToggleActive}
          onCancel={() => setConfirmToggle(null)}
        />
      )}
    </div>
  )
}
