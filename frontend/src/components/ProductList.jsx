import { useState, useEffect, useCallback, useRef } from 'react';
import { productsApi, categoriesApi } from '../api/client.js';
import ProductForm from './ProductForm.jsx';
import ProductCard from './ProductCard.jsx';

export default function ProductList() {
  const [products, setProducts] = useState([]);
  const [total, setTotal] = useState(0);
  const [categories, setCategories] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pendingSearch, setPendingSearch] = useState('');
  const searchTimer = useRef(null);
  const perPage = 20;

  const load = useCallback(async () => {
    try {
      const params = { page, perPage };
      if (pendingSearch) params.q = pendingSearch;
      const [res, c] = await Promise.all([
        productsApi.list(params),
        categoriesApi.list(),
      ]);
      setProducts(res.products);
      setTotal(res.total);
      setCategories(c);
    } catch {}
  }, [page, perPage, pendingSearch]);

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

  function handleSearchChange(value) {
    setSearch(value);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      setPendingSearch(value);
      setPage(1);
    }, 300);
  }

  useEffect(() => {
    return () => clearTimeout(searchTimer.current);
  }, []);

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

  const totalPages = Math.ceil(total / perPage);

  function pageNumbers() {
    const pages = [];
    const maxVisible = 5;
    let start = Math.max(1, page - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let i = start; i <= end; i++) pages.push(i);
    return pages;
  }

  async function downloadCSV() {
    try {
      const res = await productsApi.listAll({ q: pendingSearch });
      const all = res.products;
      const headers = ['codigo', 'nombre', 'precio', 'stock', 'ubicacion', 'total']
      const rows = all.map(p => [
        p.code, p.name, p.price, p.stock ?? 1, p.ubicacion || '',
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
    } catch {}
  }

  async function openPDF() {
    if (pendingSearch) {
      const res = await productsApi.listAll({ q: pendingSearch });
      const ids = res.products.map(p => p.id);
      if (ids.length) {
        window.open(`/api/catalog/pdf?ids=${ids.join(',')}`, '_blank');
        return;
      }
    }
    window.open('/api/catalog/pdf', '_blank');
  }

  return (
    <div>
      <div className="filter-bar">
        <input
          className="search-input"
          placeholder="Buscar por código, nombre, categoría, ubicación, precio o color"
          value={search}
          onChange={e => handleSearchChange(e.target.value)}
        />
        <div className="filter-actions">
          <span className="total-count">{total} producto{total !== 1 ? 's' : ''}</span>
          <button className="btn btn-secondary" onClick={downloadCSV}>CSV</button>
          <button className="btn btn-secondary" onClick={openPDF}>PDF</button>
        </div>
        <button className="btn btn-add" onClick={() => setShowForm(true)}>
          + Añadir Producto
        </button>
      </div>

      {products.length === 0 && (
        <div className="empty-state">
          <p>No hay productos aún. Haz clic en "Añadir Producto" para empezar.</p>
        </div>
      )}

      <div className="product-grid">
        {products.map((p) => (
          <ProductCard key={p.id} product={p} onEdit={handleEdit} onDelete={handleDelete} />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button
            className="btn btn-pagination"
            disabled={page <= 1}
            onClick={() => setPage(p => Math.max(1, p - 1))}
          >
            ‹
          </button>
          {pageNumbers().map(n => (
            <button
              key={n}
              className={`btn btn-pagination${n === page ? ' active' : ''}`}
              onClick={() => setPage(n)}
            >
              {n}
            </button>
          ))}
          <button
            className="btn btn-pagination"
            disabled={page >= totalPages}
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
          >
            ›
          </button>
        </div>
      )}

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
