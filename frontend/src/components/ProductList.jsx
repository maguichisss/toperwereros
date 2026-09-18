import { useState, useEffect, useCallback, useRef } from 'react';
import { productsApi, categoriesApi } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx';
import { useCart } from '../context/CartContext.jsx';
import ProductForm from './ProductForm.jsx';
import ProductCard from './ProductCard.jsx';
import Pagination from './Pagination.jsx';
import Toast from './Toast.jsx';
import useToast from '../hooks/useToast.js';
import ConfirmDialog from './ConfirmDialog.jsx';
import Lightbox from './Lightbox.jsx';

export default function ProductList() {
  const { can } = useAuth();
  const { addItem } = useCart();
  const [products, setProducts] = useState([]);
  const [total, setTotal] = useState(0);
  const [categories, setCategories] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [search, setSearch] = useState('');
  const { toast, notify, clear } = useToast();
  const [page, setPage] = useState(1);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [pendingSearch, setPendingSearch] = useState('');
  const [previewImage, setPreviewImage] = useState(null);
  const searchTimer = useRef(null);
  const [perPage, setPerPage] = useState(20);

  const load = useCallback(async () => {
    try {
      const [res, c] = await Promise.all([
        productsApi.list({ page, perPage, q: pendingSearch || undefined }),
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
      setPendingSearch(value.trim());
      setPage(1);
    }, 300);
  }

  function requestDelete(id, name) {
    setConfirmDelete({ id, name });
  }

  async function confirmDeleteProduct() {
    if (!confirmDelete) return;
    try {
      await productsApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      notify('Producto eliminado', 'success');
      load();
    } catch (e) {
      notify(e.message, 'error');
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

  return (
    <div>
      <div className="filter-bar">
        <div className="filter-bar__search">
          <input
            type="search"
            enterKeyHint="search"
            className="search-input"
            placeholder="Buscar por código, nombre, categoría, ubicación, precio o color"
            aria-label="Buscar productos"
            value={search}
            onChange={e => handleSearchChange(e.target.value)}
            autoComplete="off"
            autoCorrect="off"
            spellCheck="false"
          />
        </div>
        <div className="filter-actions">
          <select value={perPage} onChange={e => { setPerPage(Number(e.target.value)); setPage(1); }} className="input-sm" autoComplete="off">
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
        {can('product.create') && (
        <button type="button" className="btn btn-add" onClick={() => setShowForm(true)}>
          + Añadir Producto
        </button>
        )}
      </div>

      {total > 0 && (
        <p className="filter-bar__count">
          Mostrando {products.length} de {total} resultado{total !== 1 ? 's' : ''}
          {totalPages > 1 && ` — Página ${page} de ${totalPages}`}
        </p>
      )}

      {products.length === 0 && (
        <div className="empty-state">
          <p>{total === 0 ? 'No hay productos aún. Haz clic en "Añadir Producto" para empezar.' : 'No se encontraron productos con la búsqueda actual.'}</p>
        </div>
      )}

      <div className="product-grid">
        {products.map((p) => (
          <ProductCard key={p.id} product={p} onEdit={handleEdit} onDelete={(id) => requestDelete(id, p.name)} onShowImage={setPreviewImage} canEdit={can('product.edit')} onAddToCart={(product) => {
            if (!addItem(product)) {
              notify('No puedes agregar más productos', 'error')
            }
          }} />
        ))}
      </div>

      <Pagination page={page} totalPages={totalPages} onChange={setPage} />

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

      <Toast message={toast?.message} type={toast?.type} onClose={clear} />

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
