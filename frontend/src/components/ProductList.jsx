import { useState, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { productsApi, categoriesApi } from '../api/client.js';
import ProductForm from './ProductForm.jsx';

const ProductList = forwardRef(function ProductList(props, ref) {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [search, setSearch] = useState('');

  const load = useCallback(async () => {
    try {
      const [p, c] = await Promise.all([
        productsApi.list(),
        categoriesApi.list(),
      ]);
      setProducts(p);
      setCategories(c);
    } catch {}
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!showForm) return
    window.history.pushState({ modal: true }, '')
    const handler = () => handleClose()
    window.addEventListener('popstate', handler)
    return () => window.removeEventListener('popstate', handler)
  }, [showForm])

  async function handleDelete(id) {
    if (!confirm('¿Eliminar este producto?')) return;
    try {
      await productsApi.remove(id);
      load();
    } catch {}
  }

  function handleEdit(product) {
    setEditing(product);
    setShowForm(true);
  }

  function handleClose() {
    setShowForm(false);
    setEditing(null);
  }

  function handleSaved() {
    handleClose();
    load();
  }

  const filtered = products.filter(p => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      p.code.toLowerCase().includes(q) ||
      p.name.toLowerCase().includes(q) ||
      p.ubicacion?.toLowerCase().includes(q) ||
      String(p.price).includes(q) ||
      p.colors?.some(c => c.name.toLowerCase().includes(q))
    );
  });

  function downloadCSV() {
    const headers = ['codigo', 'nombre', 'precio', 'stock', 'ubicacion', 'total']
    const rows = filtered.map(p => [
      p.code,
      p.name,
      p.price,
      p.stock ?? 1,
      p.ubicacion || '',
      ((p.stock ?? 1) * p.price).toFixed(2),
    ])
    const csv = [headers.join(','), ...rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'productos.csv'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  useImperativeHandle(ref, () => ({ downloadCSV }), [filtered])

  return (
    <div>
      <div className="filter-bar">
        <input
          className="search-input"
          placeholder="Buscar por código, nombre, ubicación, precio o color"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <span className="total-count">{filtered.length} producto{filtered.length !== 1 ? 's' : ''}</span>
        <button className="btn btn-add" onClick={() => setShowForm(true)}>
          + Añadir Producto
        </button>
      </div>

      {filtered.length === 0 && (
        <div className="empty-state">
          <p>No hay productos aún. Haz clic en "Añadir Producto" para empezar.</p>
        </div>
      )}

      <div className="product-grid">
        {filtered.map((p) => (
          <div key={p.id} className="product-card">
            {p.image_url ? (
              <img className="card-image" src={`${p.image_url}?t=${p.updated_at}`} alt={p.name} onClick={() => handleEdit(p)} />
            ) : (
              <div className="no-image" onClick={() => handleEdit(p)}>—</div>
            )}
            <div className="card-body">
              <h3 onClick={() => handleEdit(p)}>{p.name}</h3>
              <div className="product-code">{p.code}</div>
              <div className="price">${Number(p.price).toFixed(2)}</div>
              <div className="product-stock">Stock: {p.stock ?? 1}{p.ubicacion ? ` | ${p.ubicacion}` : ''}</div>
              {p.colors?.length > 0 && (
                <div className="color-indicators">
                  {p.colors.map((c) => (
                    <span
                      key={c.id}
                      className="color-dot"
                      style={{ backgroundColor: c.hex }}
                      title={c.name}
                    />
                  ))}
                </div>
              )}
            </div>
            <div className="card-actions">
              <button className="btn btn-primary" onClick={() => handleEdit(p)}>Editar</button>
              <button className="btn btn-danger" onClick={() => handleDelete(p.id)}>Eliminar</button>
            </div>
          </div>
        ))}
      </div>

      {showForm && (
        <ProductForm
          product={editing}
          categories={categories}
          onSave={handleSaved}
          onCancel={handleClose}
        />
      )}
    </div>
  );
});

export default ProductList;
