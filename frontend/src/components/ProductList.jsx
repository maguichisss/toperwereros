import { useState, useEffect, useCallback } from 'react';
import { productsApi, categoriesApi, colorsApi } from '../api/client.js';
import ProductForm from './ProductForm.jsx';

export default function ProductList() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [colors, setColors] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [filters, setFilters] = useState({ code: '', name: '', price: '', stock: '', category: '' });
  const [colorQuery, setColorQuery] = useState('');
  const [selectedColor, setSelectedColor] = useState(null);
  const [showColorDropdown, setShowColorDropdown] = useState(false);

  const load = useCallback(async () => {
    try {
      const [p, c, cl] = await Promise.all([
        productsApi.list(),
        categoriesApi.list(),
        colorsApi.list(),
      ]);
      setProducts(p);
      setCategories(c);
      setColors(cl);
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

  function setFilter(field, value) {
    setFilters(prev => ({ ...prev, [field]: value }));
  }

  const filtered = products.filter(p => {
    if (filters.code && !p.code.toLowerCase().includes(filters.code.toLowerCase())) return false;
    if (filters.name && !p.name.toLowerCase().includes(filters.name.toLowerCase())) return false;
    if (filters.price && !String(p.price).includes(filters.price)) return false;
    if (filters.stock && !String(p.stock ?? 1).includes(filters.stock)) return false;
    if (filters.category && p.category && !p.category.name.toLowerCase().includes(filters.category.toLowerCase())) return false;
    if (selectedColor && !p.colors?.some(c => c.id === selectedColor.id)) return false;
    return true;
  });

  return (
    <div>
      <div className="filter-bar">
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
              <th>Categoría</th>
              <th>Colores</th>
              <th></th>
              <th></th>
            </tr>
            <tr className="filter-row">
              <th><input placeholder="Filtrar código" value={filters.code} onChange={e => setFilter('code', e.target.value)} /></th>
              <th><input placeholder="Filtrar nombre" value={filters.name} onChange={e => setFilter('name', e.target.value)} /></th>
              <th><input placeholder="Filtrar precio" value={filters.price} onChange={e => setFilter('price', e.target.value)} /></th>
              <th><input placeholder="Filtrar stock" value={filters.stock} onChange={e => setFilter('stock', e.target.value)} /></th>
              <th><input placeholder="Filtrar categoría" value={filters.category} onChange={e => setFilter('category', e.target.value)} /></th>
              <th className="th-color-filter">
                <input
                  placeholder="Filtrar color"
                  value={colorQuery}
                  onChange={e => { setColorQuery(e.target.value); setSelectedColor(null); setShowColorDropdown(true); }}
                  onFocus={() => setShowColorDropdown(true)}
                  onBlur={() => setTimeout(() => setShowColorDropdown(false), 150)}
                />
                {showColorDropdown && (
                  <div className="color-autocomplete">
                    {colors
                      .filter(c => c.name.toLowerCase().includes(colorQuery.toLowerCase()))
                      .map(c => (
                        <button key={c.id} type="button" className="color-option" onClick={() => {
                          setSelectedColor(c);
                          setColorQuery(c.name);
                          setShowColorDropdown(false);
                        }}>
                          <span className="color-dot" style={{ backgroundColor: c.hex }} />
                          {c.name}
                        </button>
                      ))}
                  </div>
                )}
              </th>
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
                <td className="td-cat">{p.category?.name}</td>
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
