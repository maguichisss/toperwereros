import { useState, useRef } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { authApi } from '../api/client.js'

export default function ProfilePage() {
  const { user, refreshUser } = useAuth()
  const fileRef = useRef(null)

  const [email, setEmail] = useState(user?.email || '')
  const [imageUrl, setImageUrl] = useState(user?.image_url || '')
  const [uploading, setUploading] = useState(false)

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [profileError, setProfileError] = useState('')
  const [profileSuccess, setProfileSuccess] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')

  const [profileBusy, setProfileBusy] = useState(false)
  const [passwordBusy, setPasswordBusy] = useState(false)

  async function handleFileSelect(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setProfileError('')
    try {
      const res = await authApi.uploadAvatar(file)
      setImageUrl(res.image_url)
    } catch (err) {
      setProfileError(err.message)
    } finally {
      setUploading(false)
    }
  }

  async function handleSaveProfile() {
    setProfileError('')
    setProfileSuccess('')
    setProfileBusy(true)
    try {
      await authApi.updateProfile({ email: email || null, image_url: imageUrl || null })
      await refreshUser()
      setProfileSuccess('Perfil actualizado')
    } catch (err) {
      setProfileError(err.message)
    } finally {
      setProfileBusy(false)
    }
  }

  async function handleChangePassword(e) {
    e.preventDefault()
    setPasswordError('')
    setPasswordSuccess('')
    if (newPassword !== confirmPassword) {
      setPasswordError('Las contraseñas no coinciden')
      return
    }
    if (newPassword.length < 4) {
      setPasswordError('La contraseña debe tener al menos 4 caracteres')
      return
    }
    setPasswordBusy(true)
    try {
      await authApi.changePassword({ current_password: currentPassword, new_password: newPassword })
      setPasswordSuccess('Contraseña actualizada')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setPasswordError(err.message)
    } finally {
      setPasswordBusy(false)
    }
  }

  return (
    <div style={{ maxWidth: 500 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', marginBottom: '1.5rem' }}>
        <div
          onClick={() => fileRef.current?.click()}
          style={{
            width: 120,
            height: 120,
            borderRadius: '50%',
            overflow: 'hidden',
            background: 'var(--border-light)',
            cursor: 'pointer',
            flexShrink: 0,
            position: 'relative',
            border: '3px solid var(--border-dark)',
          }}
        >
          {imageUrl ? (
            <img src={imageUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          ) : (
            <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-light)', fontSize: '0.8rem', textAlign: 'center', padding: '0.5rem' }}>
              {uploading ? 'Subiendo...' : 'Click para foto'}
            </div>
          )}
        </div>
        <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" style={{ display: 'none' }} onChange={handleFileSelect} />
        <div>
          <h2 style={{ fontSize: '1.3rem', marginBottom: '0.25rem' }}>{user?.username}</h2>
          <span className="chip chip-active" style={{ fontSize: '0.8rem' }}>{user?.role_name}</span>
        </div>
      </div>

      <div className="profile-card">
        <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Información</h3>
        <div className="form-group">
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
            autoComplete="off" autoCorrect="off" spellCheck="false" />
        </div>
        {profileError && <p className="error-text">{profileError}</p>}
        {profileSuccess && <p style={{ color: 'var(--success)', fontWeight: 600, marginTop: '0.5rem' }}>{profileSuccess}</p>}
        <div className="form-actions">
          <button className="btn btn-primary" onClick={handleSaveProfile} disabled={profileBusy}>
            {profileBusy ? 'Guardando...' : 'Guardar Cambios'}
          </button>
        </div>
      </div>

      <div className="profile-card">
        <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Cambiar Contraseña</h3>
        <form onSubmit={handleChangePassword}>
          <div className="form-group">
            <label>Contraseña actual</label>
            <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="off" autoCorrect="off" spellCheck="false" required />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Nueva contraseña</label>
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="off" autoCorrect="off" spellCheck="false" required />
            </div>
            <div className="form-group">
              <label>Confirmar</label>
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="off" autoCorrect="off" spellCheck="false" required />
            </div>
          </div>
          {passwordError && <p className="error-text">{passwordError}</p>}
          {passwordSuccess && <p style={{ color: 'var(--success)', fontWeight: 600, marginTop: '0.5rem' }}>{passwordSuccess}</p>}
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={passwordBusy}>
              {passwordBusy ? 'Cambiando...' : 'Cambiar Contraseña'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
