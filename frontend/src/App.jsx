import { useState } from 'react';
import ProductList from './components/ProductList.jsx';
import CategoryManager from './components/CategoryManager.jsx';
import ColorManager from './components/ColorManager.jsx';

const TABS = [
  { key: 'products', label: 'Productos' },
  { key: 'colors', label: 'Colores' },
  { key: 'categories', label: 'Categorías' },
];

export default function App() {
  const [tab, setTab] = useState('products');

  return (
    <>
      <header>
        <div className="container">
          <h1>Catálogo de Productos</h1>
          <nav>
            {TABS.map((t) => (
              <button
                key={t.key}
                className={tab === t.key ? 'active' : ''}
                onClick={() => setTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="container">
        {tab === 'products' && <ProductList />}
        {tab === 'colors' && <ColorManager />}
        {tab === 'categories' && <CategoryManager />}
      </main>
    </>
  );
}
