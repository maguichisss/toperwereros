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
  const [showPassword, setShowPassword] = useState(false)

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
    if (newPassword.length < 12) {
      setPasswordError('La contraseña debe tener al menos 12 caracteres')
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
    <div className="profile-page">
      <div className="profile-header">
        <button
          type="button"
          className="profile-avatar-btn"
          onClick={() => fileRef.current?.click()}
          aria-label="Cambiar foto de perfil"
        >
          {imageUrl ? (
            <img src={imageUrl} alt="" className="profile-avatar-img" />
          ) : (
            <span className="profile-avatar-placeholder">
              {uploading ? 'Subiendo...' : 'Click para foto'}
            </span>
          )}
        </button>
        <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="visually-hidden" onChange={handleFileSelect} />
        <div>
          <h2 className="profile-name">{user?.username}</h2>
          <span className="chip chip--active">{user?.role_name}</span>
        </div>
      </div>

      <div className="profile-card">
        <h3 className="profile-card__title">Información</h3>
        <div className="form-group">
          <label htmlFor="profile-email">Email</label>
          <input id="profile-email" type="email" name="email" value={email} onChange={(e) => setEmail(e.target.value)}
            autoComplete="email" autoCorrect="off" spellCheck="false" />
        </div>
        {profileError && <p className="error-text">{profileError}</p>}
        {profileSuccess && <p className="form-message--success">{profileSuccess}</p>}
        <div className="form-actions">
          <button type="button" className="btn btn--primary" onClick={handleSaveProfile} disabled={profileBusy}>
            {profileBusy ? 'Guardando...' : 'Guardar Cambios'}
          </button>
        </div>
      </div>

      <div className="profile-card">
        <h3 className="profile-card__title profile-card__title--with-action">
          Cambiar Contraseña
          <button
            type="button"
            className="password-toggle"
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? 'Ocultar contraseñas' : 'Mostrar contraseñas'}
          >
            {showPassword ? '🙈' : '👁'}
          </button>
        </h3>
        <form onSubmit={handleChangePassword}>
          <div className="form-group">
            <label htmlFor="profile-current-password">Contraseña actual</label>
            <input id="profile-current-password" type={showPassword ? 'text' : 'password'} name="current_password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password" autoCorrect="off" spellCheck="false" required />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="profile-new-password">Nueva contraseña</label>
              <input id="profile-new-password" type={showPassword ? 'text' : 'password'} name="new_password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password" autoCorrect="off" spellCheck="false" required minLength="12" />
            </div>
            <div className="form-group">
              <label htmlFor="profile-confirm-password">Confirmar</label>
              <input id="profile-confirm-password" type={showPassword ? 'text' : 'password'} name="confirm_password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password" autoCorrect="off" spellCheck="false" required />
            </div>
          </div>
          {passwordError && <p className="error-text">{passwordError}</p>}
          {passwordSuccess && <p className="form-message--success">{passwordSuccess}</p>}
          <div className="form-actions">
            <button type="submit" className="btn btn--primary" disabled={passwordBusy}>
              {passwordBusy ? 'Cambiando...' : 'Cambiar Contraseña'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}