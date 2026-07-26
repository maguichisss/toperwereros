import { useState, useEffect } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'
import LoginPage from './components/LoginPage.jsx'
import ProductList from './components/ProductList.jsx'
import SaleCart from './components/SaleCart.jsx'
import LayawayView from './components/LayawayView.jsx'
import ProfilePage from './components/ProfilePage.jsx'
import ManagementPage from './components/ManagementPage.jsx'

const TABS = [
  { key: 'productos', label: 'Productos' },
  { key: 'ventas', label: 'Ventas' },
  { key: 'apartados', label: 'Apartados' },
  { key: 'management', label: 'Administración' },
  { key: 'perfil', label: 'Perfil' },
]

const TAB_TITLES = {
  productos: 'Productos',
  ventas: 'Ventas',
  apartados: 'Apartados',
  management: 'Administración',
  perfil: 'Perfil',
}

function AppContent() {
  const { user, logout, can, loading } = useAuth()
  const [tab, setTab] = useState('productos')
  const [menuOpen, setMenuOpen] = useState(false)
  useEffect(() => {
    document.title = `${TAB_TITLES[tab]} — Toperwereros`
  }, [tab])

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: 'var(--text-muted)' }}>
        <p>Cargando...</p>
      </div>
    )
  }

  if (!user) {
    return <LoginPage />
  }

  function handleTabClick(key) {
    setTab(key)
    setMenuOpen(false)
  }

  const visibleTabs = TABS.filter(t => {
    if (t.key === 'management') return can('user.manage') || can('customer.create')
    return true
  })

  return (
    <>
      <header>
        <div className="container">
          <h1 onClick={() => handleTabClick('productos')} style={{ cursor: 'pointer' }}>Toperwereros</h1>
          <button
            className={`hamburger ${menuOpen ? 'open' : ''}`}
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Menú"
          >
            <span /><span /><span />
          </button>
          <nav className={menuOpen ? 'nav-open' : ''}>
            {visibleTabs.map((t) => (
              <button
                key={t.key}
                className={tab === t.key ? 'active' : ''}
                onClick={() => handleTabClick(t.key)}
                title={t.key === 'perfil' ? 'Perfil' : undefined}
                style={t.key === 'perfil' ? { display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0.4rem 0.6rem', background: 'rgba(255,255,255,0.1)' } : undefined}
              >
                {t.key === 'perfil' ? (
                  user.image_url ? (
                    <img src={user.image_url} alt="" style={{ width: 36, height: 36, borderRadius: '50%', objectFit: 'cover' }} />
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                  )
                ) : t.label}
              </button>
            ))}
              <button onClick={logout} title="Cerrar sesión" style={{ background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0.4rem 0.6rem' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </button>
          </nav>
        </div>
      </header>
      <main className="container">
        {tab === 'productos' && <ProductList />}
        {tab === 'ventas' && <SaleCart />}
        {tab === 'apartados' && <LayawayView />}
        {tab === 'management' && <ManagementPage />}
        {tab === 'perfil' && <ProfilePage />}
      </main>
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
