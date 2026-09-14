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
      <div className="cart-drawer-backdrop" onClick={onClose} aria-hidden="true" />
      <aside className="cart-drawer" ref={panelRef} role="dialog" aria-modal="true" aria-labelledby="cart-drawer-title">
        <div className="cart-drawer__header">
          <h3 id="cart-drawer-title">Carrito ({itemCount})</h3>
          <button type="button" className="cart-drawer__close" onClick={onClose} aria-label="Cerrar carrito">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="cart-drawer__items">
          {items.length === 0 ? (
            <div className="cart-drawer__empty">El carrito esta vacio</div>
          ) : (
            items.map(item => (
              <div key={item.product_id} className="cart-drawer__item">
                {item.image_url ? (
                  <img className="cart-drawer__thumb" src={item.image_url} alt={item.name} loading="lazy" decoding="async" />
                ) : (
                  <div className="cart-drawer__thumb cart-drawer__thumb--empty">—</div>
                )}
                <div className="cart-drawer__info">
                  <div className="cart-drawer__name">{item.name}</div>
                  <div className="cart-drawer__code">{item.code}</div>
                  <div className="cart-drawer__price">${formatPrice(item.price)}</div>
                </div>
                <div className="cart-drawer__controls">
                  <div className="cart-drawer__qty">
                    <button type="button" className="cart-drawer__qty-btn" onClick={() => updateQty(item.product_id, -1)}>−</button>
                    <span className="cart-drawer__qty-value">{item.quantity}</span>
                    <button type="button" className="cart-drawer__qty-btn" onClick={() => updateQty(item.product_id, 1)}>+</button>
                  </div>
                  <button type="button" className="cart-drawer__remove" onClick={() => removeItem(item.product_id)} title="Quitar">
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
          <div className="cart-drawer__footer">
            <div className="cart-drawer__total-row">
              <span className="cart-drawer__total-label">Total</span>
              <span className="cart-drawer__total-amount">${formatPrice(total)}</span>
            </div>
            <div className="cart-drawer__actions">
              <button type="button" className="btn btn--primary" onClick={onVenta}>Venta</button>
              <button type="button" className="btn btn--add" onClick={onApartado}>Apartado</button>
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
      <div className="app-loading">
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
          <h1>
            <button type="button" className="brand-btn" onClick={() => handleTabClick('productos')}>
              Toperwereros
            </button>
          </h1>
          <button
            type="button"
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
                type="button"
                className={`${tab === t.key ? 'active' : ''} ${t.key === 'perfil' ? 'nav-icon-btn' : ''}`}
                onClick={() => handleTabClick(t.key)}
                title={t.key === 'perfil' ? 'Perfil' : undefined}
              >
                {t.key === 'perfil' ? (
                  user.image_url ? (
                    <img src={user.image_url} alt="Perfil" className="nav-avatar" />
                  ) : (
                    <UserIcon />
                  )
                ) : t.label}
              </button>
            ))}
            <button type="button" className="nav-icon-btn" onClick={logout} title="Cerrar sesión" aria-label="Cerrar sesión">
              <LogoutIcon />
            </button>
          </nav>
          {(can('sale.create') || can('apartado.create')) && (
            <button
              type="button"
              className="cart-nav-btn"
              onClick={() => setCartOpen(!cartOpen)}
              title="Carrito"
              aria-label="Abrir carrito"
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
