import { useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'

export default function LoginPage() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
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
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      background: 'var(--bg)',
    }}>
      <form onSubmit={handleSubmit} style={{
        background: 'var(--bg-card)',
        borderRadius: 8,
        padding: '2rem',
        width: '100%',
        maxWidth: 360,
        boxShadow: '0 2px 12px var(--shadow)',
      }}>
        <h1 style={{ fontSize: '1.4rem', textAlign: 'center', marginBottom: '1.5rem' }}>
          Iniciar Sesión
        </h1>
        <div className="form-group">
          <label>Usuario</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="off"
            autoCorrect="off"
            spellCheck="false"
            required
          />
        </div>
        <div className="form-group">
          <label>Contraseña</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="off"
            autoCorrect="off"
            spellCheck="false"
            required
          />
        </div>
        {error && <p className="error-text">{error}</p>}
        <button
          type="submit"
          className="btn btn-primary"
          disabled={busy}
          style={{ width: '100%', padding: '0.7rem', fontSize: '1rem', marginTop: '0.5rem' }}
        >
          {busy ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </div>
  )
}
