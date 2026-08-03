import { useState, useEffect, useCallback, useRef } from 'react';
import { productsApi, categoriesApi } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx';
import ProductForm from './ProductForm.jsx';
import ProductCard from './ProductCard.jsx';
import Toast from './Toast.jsx';
import ConfirmDialog from './ConfirmDialog.jsx';
import Lightbox from './Lightbox.jsx';
import { formatPrice } from '../utils.js';

export default function ProductList() {
  const { can } = useAuth();
  const [products, setProducts] = useState([]);
  const [total, setTotal] = useState(0);
  const [categories, setCategories] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [search, setSearch] = useState('');
  const [toast, setToast] = useState(null);
  const [page, setPage] = useState(1);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [pendingSearch, setPendingSearch] = useState('');
  const [previewImage, setPreviewImage] = useState(null);
  const searchTimer = useRef(null);
  const [perPage, setPerPage] = useState(20);

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

  function requestDelete(id, name) {
    setConfirmDelete({ id, name });
  }

  function showToast(message, type) { setToast({ message, type }) }

  async function confirmDeleteProduct() {
    if (!confirmDelete) return;
    try {
      await productsApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      showToast('Producto eliminado', 'success');
      load();
    } catch (e) {
      showToast(e.message, 'error');
      setConfirmDelete(null);
    }
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
        formatPrice((p.stock ?? 1) * p.price),
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
    try {
      showToast('Generando PDF…', 'info')
      let url = '/api/catalog/pdf'
      if (pendingSearch) url += `?q=${encodeURIComponent(pendingSearch)}`
      const token = localStorage.getItem('store_token')
      const r = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      if (!r.ok) throw new Error('Error al generar PDF')
      const blob = await r.blob()
      const disposition = r.headers.get('Content-Disposition')
      let filename = 'catalogo.pdf'
      if (disposition) {
        const match = disposition.match(/filename=(.+)/)
        if (match) filename = match[1]
      }
      const blobUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(blobUrl)
      showToast('PDF descargado', 'success')
    } catch (err) {
      showToast(err.message || 'Error al generar PDF')
    }
  }

  return (
    <div>
      <div className="filter-bar">
        <div style={{ position: 'relative', flex: 1, minWidth: 200, width: '100%' }}>
          <input
            className="search-input"
            placeholder="Buscar por código, nombre, categoría, ubicación, precio o color"
            value={search}
            onChange={e => handleSearchChange(e.target.value)}
            autoComplete="off"
            autoCorrect="off"
            spellCheck="false"
            style={{ paddingRight: search ? '2rem' : undefined }}
          />
          {search && (
            <button
              onClick={() => { setSearch(''); setPendingSearch(''); setPage(1); }}
              style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', fontSize: '1.1rem', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px', lineHeight: 1 }}
            >
              ✕
            </button>
          )}
        </div>
        <div className="filter-actions">
          <select value={perPage} onChange={e => { setPerPage(Number(e.target.value)); setPage(1); }} style={{ padding: '0.35rem 0.4rem', border: '1px solid #ccc', borderRadius: 4, fontSize: '0.85rem' }}>
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
          {can('product.view') && (
            <>
              <button className="btn btn-secondary" onClick={downloadCSV}>CSV</button>
              <button className="btn btn-secondary" onClick={openPDF}>PDF</button>
            </>
          )}
        </div>
        {can('product.create') && (
        <button className="btn btn-add" onClick={() => setShowForm(true)}>
          + Añadir Producto
        </button>
        )}
      </div>

      {total > 0 && (
        <p style={{ marginBottom: '0.75rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Mostrando {products.length} de {total} resultado{total !== 1 ? 's' : ''}
          {totalPages > 1 && ` — Página ${page} de ${totalPages}`}
        </p>
      )}

      {products.length === 0 && (
        <div className="empty-state">
          <p>{total === 0 ? 'No hay productos aún. Haz clic en "Añadir Producto" para empezar.' : 'No se encontraron productos con los filtros actuales.'}</p>
        </div>
      )}

      <div className="product-grid">
        {products.map((p) => (
          <ProductCard key={p.id} product={p} onEdit={handleEdit} onDelete={(id) => requestDelete(id, p.name)} onShowImage={setPreviewImage} canEdit={can('product.edit')} />
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

      {previewImage && (
        <Lightbox imageUrl={previewImage} name="Producto" onClose={() => setPreviewImage(null)} />
      )}

      {confirmDelete && (
        <ConfirmDialog
          title="Eliminar Producto"
          message={`¿Estás seguro de eliminar "${confirmDelete.name}"? Esta acción no se puede deshacer.`}
          onConfirm={confirmDeleteProduct}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      <Toast message={toast?.message} type={toast?.type} onClose={() => setToast(null)} />

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
