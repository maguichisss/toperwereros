import { useState } from 'react';
import ProductList from './components/ProductList.jsx';
import CategoryManager from './components/CategoryManager.jsx';
import ColorManager from './components/ColorManager.jsx';

const TABS = [
  { key: 'productos', label: 'Productos' },
  { key: 'colors', label: 'Colores' },
  { key: 'categories', label: 'Categorías' },
];

export default function App() {
  const [tab, setTab] = useState('productos');
  const [menuOpen, setMenuOpen] = useState(false);

  function handleTabClick(key) {
    setTab(key);
    setMenuOpen(false);
  }

  return (
    <>
      <header>
        <div className="container">
          <h1 onClick={() => handleTabClick('productos')} style={{ cursor: 'pointer' }}>Catálogo de Productos</h1>
          <button
            className={`hamburger ${menuOpen ? 'open' : ''}`}
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Menú"
          >
            <span /><span /><span />
          </button>
          <nav className={menuOpen ? 'nav-open' : ''}>
            {TABS.map((t) => (
              <button
                key={t.key}
                className={tab === t.key ? 'active' : ''}
                onClick={() => handleTabClick(t.key)}
              >
                {t.label}
              </button>
            ))}
            <button onClick={() => { window.open('/api/catalog/pdf', '_blank'); setMenuOpen(false); }}>
              Catálogo PDF
            </button>
          </nav>
        </div>
      </header>
      <main className="container">
        {tab === 'productos' && <ProductList />}
        {tab === 'colors' && <ColorManager />}
        {tab === 'categories' && <CategoryManager />}
      </main>
    </>
  );
}
