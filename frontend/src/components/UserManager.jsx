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
  const [roleId, setRoleId] = useState(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)

  const defaultRoleId = (rs) => {
    const def = rs.find((r) => r.name === 'employee') || rs[0]
    return def ? def.id : null
  }

  const [editUser, setEditUser] = useState(null)
  const [editForm, setEditForm] = useState({ username: '', email: '', role_id: null, password: '' })
  const [editError, setEditError] = useState('')
  const [editBusy, setEditBusy] = useState(false)

  const [confirmToggle, setConfirmToggle] = useState(null)

  useEffect(() => {
    fetchUsers()
    rolesApi.list().then((rs) => {
      setRoles(rs)
      setRoleId(defaultRoleId(rs))
    }).catch(() => {})
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
      setRoleId(defaultRoleId(roles))
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

  useEffect(() => {
    if (!editUser) return;
    const previouslyFocused = document.activeElement;
    document.getElementById('edit-user-username')?.focus();
    function handleKeyDown(e) {
      if (e.key === 'Escape') setEditUser(null);
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (previouslyFocused && typeof previouslyFocused.focus === 'function') previouslyFocused.focus();
    };
  }, [editUser]);

  return (
    <div className="user-manager">
      <form onSubmit={handleSubmit} className="user-form">
        <h2 className="user-form__title">Nuevo Usuario</h2>
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="new-user-username">Usuario</label>
            <input id="new-user-username" type="text" value={username} onChange={(e) => setUsername(e.target.value)}
              autoComplete="off" autoCorrect="off" spellCheck="false" required />
          </div>
          <div className="form-group">
            <label htmlFor="new-user-password">Contraseña</label>
            <input id="new-user-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password" autoCorrect="off" spellCheck="false" required />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="new-user-email">Email</label>
            <input id="new-user-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              autoComplete="email" autoCorrect="off" spellCheck="false" />
          </div>
          <div className="form-group">
            <label htmlFor="new-user-role">Rol</label>
            <select id="new-user-role" value={roleId} onChange={(e) => setRoleId(Number(e.target.value))} autoComplete="off">
              {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
        </div>
        {error && <p className="error-text">{error}</p>}
        {success && <p className="form-message--success">{success}</p>}
        <div className="form-actions">
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {busy ? 'Creando...' : 'Crear Usuario'}
          </button>
        </div>
      </form>

      <div className="user-list">
        <h2 className="user-list__title">Usuarios existentes</h2>
        {users.map((u) => (
          <div key={u.id} className={`user-row ${u.active ? '' : 'user-row--inactive'}`}>
            <span className={`user-row__name ${u.active ? '' : 'user-row__name--inactive'}`}>
              {u.username}
              {isSelf(u) && <span className="user-row__self">(tú)</span>}
            </span>
            {!u.active && <span className="user-row__disabled">desactivado</span>}
            <span className="user-row__email">{u.email || '—'}</span>
            <span className={`chip user-row__role ${u.role_name === 'admin' ? 'chip--active' : ''}`}>
              {u.role_name}
            </span>
            <button type="button" className="btn btn--secondary btn--small" onClick={() => openEdit(u)}>
              Editar
            </button>
            {!isSelf(u) && (
              <button
                type="button"
                className={`btn btn--small ${u.active ? 'btn--danger' : 'btn--primary'}`}
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
          <div className="modal modal--fixed" role="dialog" aria-modal="true" aria-labelledby="edit-user-title" onClick={e => e.stopPropagation()}>
            <h2 id="edit-user-title" className="user-form__title">Editar usuario</h2>
            <form onSubmit={handleEditSubmit}>
              <div className="form-group">
                <label htmlFor="edit-user-username">Usuario</label>
                <input id="edit-user-username" type="text" value={editForm.username} onChange={(e) => setEditForm({ ...editForm, username: e.target.value })}
                  autoComplete="off" autoCorrect="off" spellCheck="false" required />
              </div>
              <div className="form-group">
                <label htmlFor="edit-user-email">Email</label>
                <input id="edit-user-email" type="email" value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                  autoComplete="off" autoCorrect="off" spellCheck="false" />
              </div>
              {!isSelf(editUser) && (
                <div className="form-group">
                  <label htmlFor="edit-user-role">Rol</label>
                  <select id="edit-user-role" value={editForm.role_id} onChange={(e) => setEditForm({ ...editForm, role_id: Number(e.target.value) })} autoComplete="off">
                    {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </div>
              )}
              <div className="form-group">
                <label htmlFor="edit-user-password">Nueva contraseña (opcional)</label>
                <input id="edit-user-password" type="password" value={editForm.password} onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                  autoComplete="new-password" autoCorrect="off" spellCheck="false" placeholder="Dejar vacío para no cambiar" />
              </div>
              {editError && <p className="error-text">{editError}</p>}
              <div className="form-actions">
                <button type="button" className="btn btn--secondary" onClick={() => setEditUser(null)}>Cancelar</button>
                <button type="submit" className="btn btn--primary" disabled={editBusy}>
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