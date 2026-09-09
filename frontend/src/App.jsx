import { useState, useEffect, useRef } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'
import { CartProvider, useCart } from './context/CartContext.jsx'
import LoginPage from './components/LoginPage.jsx'
import ProductList from './components/ProductList.jsx'
import LayawayView from './components/LayawayView.jsx'
import ProfilePage from './components/ProfilePage.jsx'
import ManagementPage from './components/ManagementPage.jsx'
import { formatPrice } from './utils.js'
import { CartIcon, LogoutIcon, UserIcon } from './components/icons.jsx'

const TABS = [
  { key: 'productos', label: 'Productos' },
  { key: 'apartados', label: 'Apartados' },
  { key: 'management', label: 'Administración' },
  { key: 'perfil', label: 'Perfil' },
]

const TAB_TITLES = {
  productos: 'Productos',
  apartados: 'Apartados',
  management: 'Administración',
  perfil: 'Perfil',
}

function CartPanel({ onClose, onVenta, onApartado }) {
  const { items, updateQty, removeItem, itemCount, total } = useCart()
  const panelRef = useRef(null)

  useEffect(() => {
    function handleKey(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  return (
    <>
      <div className="cart-backdrop" onClick={onClose} />
      <aside className="cart-panel" ref={panelRef}>
        <div className="cart-panel-header">
          <h3>Carrito ({itemCount})</h3>
          <button className="cart-close-btn" onClick={onClose} aria-label="Cerrar carrito">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="cart-panel-items">
          {items.length === 0 ? (
            <div className="cart-empty">El carrito esta vacio</div>
          ) : (
            items.map(item => (
              <div key={item.product_id} className="cart-item-row">
                {item.image_url ? (
                  <img className="cart-item-thumb" src={item.image_url} alt={item.name} />
                ) : (
                  <div className="cart-item-thumb-empty">—</div>
                )}
                <div className="cart-item-info">
                  <div className="cart-item-name">{item.name}</div>
                  <div className="cart-item-code">{item.code}</div>
                  <div className="cart-item-price">${formatPrice(item.price)}</div>
                </div>
                <div className="cart-item-controls">
                  <div className="cart-qty-group">
                    <button className="cart-qty-btn" onClick={() => updateQty(item.product_id, -1)}>−</button>
                    <span className="cart-qty">{item.quantity}</span>
                    <button className="cart-qty-btn" onClick={() => updateQty(item.product_id, 1)}>+</button>
                  </div>
                  <button className="cart-remove-btn" onClick={() => removeItem(item.product_id)} title="Quitar">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {items.length > 0 && (
          <div className="cart-panel-footer">
            <div className="cart-total-row">
              <span className="cart-total-label">Total</span>
              <span className="cart-total-amount">${formatPrice(total)}</span>
            </div>
            <div className="cart-panel-actions">
              <button className="btn btn-primary" style={{ fontSize: '1rem' }} onClick={onVenta}>Venta</button>
              <button className="btn btn-add" onClick={onApartado}>Apartado</button>
            </div>
          </div>
        )}
      </aside>
    </>
  )
}

function AppContent() {
  const { user, logout, can, loading } = useAuth()
  const { itemCount } = useCart()
  const [tab, setTab] = useState('productos')
  const [menuOpen, setMenuOpen] = useState(false)
  const headerRef = useRef(null)
  const [cartOpen, setCartOpen] = useState(false)
  const [createMode, setCreateMode] = useState(false)
  const [managementSubTab, setManagementSubTab] = useState(null)

  useEffect(() => {
    document.title = `${TAB_TITLES[tab]} — Toperwereros`
  }, [tab])

  useEffect(() => {
    if (cartOpen || menuOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [cartOpen, menuOpen])

  useEffect(() => {
    if (!menuOpen) return
    function handleClickOutside(e) {
      if (headerRef.current && !headerRef.current.contains(e.target)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [menuOpen])

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
    setCartOpen(false)
    setCreateMode(false)
    if (key !== 'management') setManagementSubTab(null)
  }

  function handleVenta() {
    setCartOpen(false)
    setManagementSubTab('ventas')
    setTab('management')
  }

  function handleApartado() {
    setCartOpen(false)
    setCreateMode(true)
    setTab('apartados')
  }

  const visibleTabs = TABS.filter(t => {
    if (t.key === 'management') return can('user.manage') || can('customer.create')
    return true
  })

  return (
    <>
      <header ref={headerRef}>
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
                    <UserIcon />
                  )
                ) : t.label}
              </button>
            ))}
            <button onClick={logout} title="Cerrar sesión" style={{ background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0.4rem 0.6rem' }}>
              <LogoutIcon />
            </button>
          </nav>
          {(can('sale.create') || can('apartado.create')) && (
            <button
              className="cart-nav-btn"
              onClick={() => setCartOpen(!cartOpen)}
              title="Carrito"
            >
              <CartIcon />
              {itemCount > 0 && <span className="cart-badge">{itemCount}</span>}
            </button>
          )}
        </div>
      </header>
      <main className="container">
        {tab === 'productos' && <ProductList />}
        {tab === 'apartados' && <LayawayView initialMode={createMode ? 'create' : undefined} />}
        {tab === 'management' && <ManagementPage defaultSubTab={managementSubTab} onSubTabHandled={() => setManagementSubTab(null)} />}
        {tab === 'perfil' && <ProfilePage />}
      </main>
      {cartOpen && (
        <CartPanel
          onClose={() => setCartOpen(false)}
          onVenta={handleVenta}
          onApartado={handleApartado}
        />
      )}
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <CartProvider>
        <AppContent />
      </CartProvider>
    </AuthProvider>
  )
}
