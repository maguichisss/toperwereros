import { useState, useEffect, useCallback } from 'react';
import { productsApi, categoriesApi } from '../api/client.js';
import ProductForm from './ProductForm.jsx';

export default function ProductList() {
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
    if (window.history.state?.modal) window.history.back()
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
      String(p.price).includes(q) ||
      p.colors?.some(c => c.name.toLowerCase().includes(q))
    );
  });

  return (
    <div>
      <div className="filter-bar">
        <input
          className="search-input"
          placeholder="Buscar por código, nombre, precio o color"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <button className="btn btn-add" onClick={() => setShowForm(true)}>
          + Añadir Producto
        </button>
      </div>

      {filtered.length === 0 && (
        <div className="empty-state">
          <p>No hay productos aún. Haz clic en "Añadir Producto" para empezar.</p>
        </div>
      )}

      <div className="table-wrap">
        <table className="product-table">
          <thead>
            <tr>
              <th>Código</th>
              <th>Nombre</th>
              <th>Precio</th>
              <th>Stock</th>
              <th>Colores</th>
              <th></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr key={p.id}>
                <td className="td-code">{p.code}</td>
                <td className="td-name">{p.name}</td>
                <td className="td-price">${Number(p.price).toFixed(2)}</td>
                <td className="td-stock">{p.stock ?? 1}</td>
                <td className="td-colors">
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
                </td>
                <td className="td-thumb">
                  {p.image_url ? (
                    <img src={p.image_url} alt={p.name} onClick={() => handleEdit(p)} />
                  ) : (
                    <div className="no-thumb" onClick={() => handleEdit(p)}>—</div>
                  )}
                </td>
                <td className="td-actions">
                  <button className="btn btn-primary" onClick={() => handleEdit(p)}>Editar</button>
                  <button className="btn btn-danger" onClick={() => handleDelete(p.id)}>Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
}
