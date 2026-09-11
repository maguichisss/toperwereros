import { useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'

export default function LoginPage() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(username.trim().toLowerCase(), password.trim())
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      <form onSubmit={handleSubmit} className="login-card">
        <h1 className="login-card__title">
          Iniciar Sesión
        </h1>
        <div className="form-group">
          <label htmlFor="login-username">Usuario</label>
          <input
            id="login-username"
            type="text"
            name="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoCorrect="off"
            spellCheck="false"
            required
          />
        </div>
        <div className="form-group password-wrap">
          <label htmlFor="login-password">Contraseña</label>
          <input
            id="login-password"
            type={showPassword ? 'text' : 'password'}
            name="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            autoCorrect="off"
            spellCheck="false"
            required
          />
          <button
            type="button"
            className="password-toggle"
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
          >
            {showPassword ? '🙈' : '👁'}
          </button>
        </div>
        {error && <p className="error-text">{error}</p>}
        <button
          type="submit"
          className="btn btn--primary login-card__submit"
          disabled={busy}
        >
          {busy ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </div>
  )
}