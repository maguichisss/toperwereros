import { useState, useEffect, useCallback, useRef } from 'react';
import { layawaysApi, customersApi, productsApi } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx';
import ConfirmDialog from './ConfirmDialog.jsx';
import { formatPrice } from '../utils.js';

const DAYS_OVERDUE = 21;

function daysElapsed(dateStr) {
  return Math.floor((Date.now() - new Date(dateStr + 'Z')) / 86400000);
}

export default function LayawayView() {
  const { can } = useAuth();
  const [mode, setMode] = useState('active');
  const [activeLayaways, setActiveLayaways] = useState([]);
  const [allLayaways, setAllLayaways] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedLayaway, setSelectedLayaway] = useState(null);

  const [error, setError] = useState('');
  const [confirmCancel, setConfirmCancel] = useState(null);
  const [confirmComplete, setConfirmComplete] = useState(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  const loadActive = useCallback(async () => {
    try {
      const res = await layawaysApi.list({ status: 'active', perPage: 100 });
      setActiveLayaways(res.layaways || []);
    } catch {}
  }, []);

  const loadAll = useCallback(async () => {
    try {
      const res = await layawaysApi.list({ perPage: 100 });
      setAllLayaways(res.layaways || []);
    } catch {}
  }, []);

  useEffect(() => {
    if (mode === 'active') loadActive();
    if (mode === 'all') loadAll();
  }, [mode, loadActive, loadAll]);

  function handleSelect(id) {
    setSelectedId(id);
    setSelectedLayaway(null);
    setMode('detail');
  }

  function handleBack() {
    setSelectedId(null);
    setSelectedLayaway(null);
    if (mode === 'detail') setMode('active');
  }

  async function executeCancel() {
    if (!confirmCancel) return;
    try {
      await layawaysApi.cancel(confirmCancel);
      setConfirmCancel(null);
      loadActive();
      if (selectedId === confirmCancel) handleBack();
    } catch (e) {
      setError(e.message);
    }
  }

  async function executeComplete() {
    if (!confirmComplete) return;
    try {
      await layawaysApi.complete(confirmComplete);
      setConfirmComplete(null);
      setSelectedId(null);
      setSelectedLayaway(null);
      setMode('active');
      loadActive();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleAddPayment(id, amount) {
    if (!amount || parseFloat(amount) <= 0) return;
    try {
      const updated = await layawaysApi.addPayment(id, parseFloat(amount));
      setSelectedLayaway(updated);
      setError('');
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    if (mode === 'detail' && selectedId && !selectedLayaway) {
      layawaysApi.get(selectedId).then(setSelectedLayaway).catch(() => {});
    }
  }, [mode, selectedId, selectedLayaway]);

  useEffect(() => {
    setPage(1);
  }, [search, mode]);

  function filterLayaways(list) {
    const q = search.trim().toLowerCase();
    if (!q) return list;
    const idMatch = q.match(/^id:\s*#?(\d+)$/);
    if (idMatch) {
      const targetId = parseInt(idMatch[1], 10);
      return list.filter(l => l.id === targetId);
    }
    return list.filter(l => l.customer_name?.toLowerCase().includes(q));
  }

  function paginate(list) {
    const start = (page - 1) * perPage;
    return list.slice(start, start + perPage);
  }

  const filteredActive = filterLayaways(activeLayaways);
  const filteredAll = filterLayaways(allLayaways);
  const pagedActive = paginate(filteredActive);
  const pagedAll = paginate(filteredAll);

  const activeTotalPages = Math.ceil(filteredActive.length / perPage);
  const allTotalPages = Math.ceil(filteredAll.length / perPage);
  const currentTotalPages = mode === 'active' ? activeTotalPages : allTotalPages;

  function pageNumbers(totalPages) {
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

  return (
    <div className="layaway-view">
      <div className="sales-tabs">
        <button className={mode === 'active' ? 'active' : ''} onClick={() => setMode('active')}>Apartados Activos</button>
        <button className={mode === 'all' ? 'active' : ''} onClick={() => setMode('all')}>Todos</button>
        {can('apartado.create') && (
          <button className={mode === 'create' ? 'active' : ''} onClick={() => { setMode('create'); setError(''); }}>Nuevo Apartado</button>
        )}
      </div>

      {(mode === 'active' || mode === 'all') && (
        <div className="filter-bar" style={{ marginBottom: '0.75rem' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 200, width: '100%' }}>
            <input
              className="search-input"
              placeholder="Buscar por nombre o #ID..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              autoComplete="off"
              autoCorrect="off"
              spellCheck="false"
              style={{ paddingRight: search ? '2rem' : undefined }}
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', fontSize: '1.1rem', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px', lineHeight: 1 }}
              >
                ✕
              </button>
            )}
          </div>
          <select
            value={perPage}
            onChange={e => { setPerPage(Number(e.target.value)); setPage(1); }}
            style={{ padding: '0.35rem 0.4rem', border: '1px solid #ccc', borderRadius: 4, fontSize: '0.85rem' }}
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
          </select>
        </div>
      )}

      {error && <p className="error-text">{error}</p>}

      {confirmCancel && (
        <ConfirmDialog
          title="Cancelar Apartado"
          message="¿Cancelar este apartado? Se restaurará el stock de los productos."
          onConfirm={executeCancel}
          onCancel={() => setConfirmCancel(null)}
        />
      )}

      {confirmComplete && (
        <ConfirmDialog
          title="Completar Apartado"
          message="¿Completar este apartado? Se creará una venta y se descontará del stock."
          onConfirm={executeComplete}
          onCancel={() => setConfirmComplete(null)}
        />
      )}

      {mode === 'active' && (
        <>
          <ActiveList
            layaways={pagedActive}
            onSelect={handleSelect}
            onCancel={setConfirmCancel}
            onRefresh={loadActive}
            isEmpty={activeLayaways.length === 0}
            isFilterNoResults={activeLayaways.length > 0 && filteredActive.length === 0}
          />
          {activeTotalPages > 1 && (
            <div className="pagination">
              <button className="btn btn-pagination" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>‹</button>
              {pageNumbers(activeTotalPages).map(n => (
                <button key={n} className={`btn btn-pagination${n === page ? ' active' : ''}`} onClick={() => setPage(n)}>{n}</button>
              ))}
              <button className="btn btn-pagination" disabled={page >= activeTotalPages} onClick={() => setPage(p => Math.min(activeTotalPages, p + 1))}>›</button>
            </div>
          )}
          {activeTotalPages > 1 && <p style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)', margin: '0.3rem 0 0' }}>Página {page} de {activeTotalPages}</p>}
        </>
      )}

      {mode === 'all' && (
        <>
          <AllList
            layaways={pagedAll}
            onSelect={handleSelect}
            onCancel={setConfirmCancel}
            onRefresh={loadAll}
            isEmpty={allLayaways.length === 0}
            isFilterNoResults={allLayaways.length > 0 && filteredAll.length === 0}
          />
          {allTotalPages > 1 && (
            <div className="pagination">
              <button className="btn btn-pagination" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>‹</button>
              {pageNumbers(allTotalPages).map(n => (
                <button key={n} className={`btn btn-pagination${n === page ? ' active' : ''}`} onClick={() => setPage(n)}>{n}</button>
              ))}
              <button className="btn btn-pagination" disabled={page >= allTotalPages} onClick={() => setPage(p => Math.min(allTotalPages, p + 1))}>›</button>
            </div>
          )}
          {allTotalPages > 1 && <p style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)', margin: '0.3rem 0 0' }}>Página {page} de {allTotalPages}</p>}
        </>
      )}

      {mode === 'create' && (
        <CreateView onBack={() => { setMode('active'); loadActive(); }} onCreated={() => { setMode('active'); loadActive(); }} />
      )}

      {mode === 'detail' && selectedLayaway && (
        <DetailView
          layaway={selectedLayaway}
          onBack={handleBack}
          onPayment={handleAddPayment}
          onCancel={setConfirmCancel}
          onComplete={setConfirmComplete}
          onUpdated={setSelectedLayaway}
        />
      )}
    </div>
  );
}

function ActiveList({ layaways, onSelect, onCancel, onRefresh, isEmpty, isFilterNoResults }) {
  return (
    <div className="layaway-list">
      {isFilterNoResults ? (
        <p className="empty-state">No se encontraron apartados.</p>
      ) : isEmpty ? (
        <p className="empty-state">No hay apartados activos.</p>
      ) : (
        layaways.map(l => {
          const days = daysElapsed(l.created_at);
          const overdue = days > DAYS_OVERDUE;
          return (
            <div
              key={l.id}
              className={`layaway-card ${overdue ? 'layaway-overdue' : ''}`}
              onClick={() => onSelect(l.id)}
            >
              <div className="layaway-card-main">
                <span className="layaway-customer">#{l.id} {l.customer_name}</span>
                <span className="layaway-items-count">{l.items?.length || 0} artículo(s)</span>
              </div>
              <div className="layaway-card-details">
                <span className="layaway-days">{days} día(s)</span>
                <span className="layaway-balance">${formatPrice(l.balance)}</span>
              </div>
              <button
                className="btn btn-danger layaway-cancel-btn"
                onClick={e => { e.stopPropagation(); onCancel(l.id); }}
              >
                Cancelar
              </button>
            </div>
          );
        })
      )}
    </div>
  );
}

function AllList({ layaways, onSelect, onCancel, onRefresh, isEmpty, isFilterNoResults }) {
  const statusLabel = { active: 'Activo', completed: 'Completado', cancelled: 'Cancelado' };
  const statusColor = { active: 'var(--primary)', completed: 'var(--success)', cancelled: 'var(--text-muted)' };

  return (
    <div className="layaway-list">
      {isFilterNoResults ? (
        <p className="empty-state">No se encontraron apartados.</p>
      ) : isEmpty ? (
        <p className="empty-state">No hay apartados registrados.</p>
      ) : (
        layaways.map(l => {
          const days = daysElapsed(l.created_at);
          const overdue = days > DAYS_OVERDUE && l.status === 'active';
          return (
            <div
              key={l.id}
              className={`layaway-card ${overdue ? 'layaway-overdue' : ''}`}
              onClick={() => onSelect(l.id)}
            >
              <div className="layaway-card-main">
                <span className="layaway-customer">#{l.id} {l.customer_name}</span>
                <span className="layaway-items-count">{l.items?.length || 0} artículo(s)</span>
              </div>
              <div className="layaway-card-details">
                <span style={{ color: statusColor[l.status], fontWeight: 600, fontSize: '0.7rem' }}>{statusLabel[l.status]}</span>
                <span className="layaway-days">{days} día(s)</span>
                <span className="layaway-balance">${formatPrice(l.balance)}</span>
              </div>
              {l.status === 'active' && (
                <button
                  className="btn btn-danger layaway-cancel-btn"
                  onClick={e => { e.stopPropagation(); onCancel(l.id); }}
                >
                  Cancelar
                </button>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}

function CreateView({ onBack, onCreated }) {
  const { can } = useAuth();
  const [step, setStep] = useState('customer');
  const [error, setError] = useState('');

  const [customerSearch, setCustomerSearch] = useState('');
  const [customerResults, setCustomerResults] = useState([]);
  const [showCustomerResults, setShowCustomerResults] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [newCustomer, setNewCustomer] = useState({ name: '', phone: '', email: '' });

  const [cart, setCart] = useState([]);
  const [productSearch, setProductSearch] = useState('');
  const [productResults, setProductResults] = useState([]);
  const [showProductResults, setShowProductResults] = useState(false);
  const [deposit, setDeposit] = useState('');
  const [notes, setNotes] = useState('');
  const [confirmCreate, setConfirmCreate] = useState(false);

  const customerTimer = useRef(null);
  const productTimer = useRef(null);
  const customerResultsRef = useRef(null);
  const productResultsRef = useRef(null);

  const searchCustomers = useCallback(async (q) => {
    if (!q.trim()) { setCustomerResults([]); return; }
    try {
      const res = await customersApi.list(q);
      setCustomerResults(res);
      setShowCustomerResults(true);
    } catch {}
  }, []);

  function handleCustomerSearchChange(value) {
    setCustomerSearch(value);
    clearTimeout(customerTimer.current);
    customerTimer.current = setTimeout(() => searchCustomers(value), 300);
  }

  const searchProducts = useCallback(async (q) => {
    if (!q.trim()) { setProductResults([]); return; }
    try {
      const res = await productsApi.list({ q, perPage: 10 });
      setProductResults(res.products.filter(p => p.stock > 0));
      setShowProductResults(true);
    } catch {}
  }, []);

  function handleProductSearchChange(value) {
    setProductSearch(value);
    clearTimeout(productTimer.current);
    productTimer.current = setTimeout(() => searchProducts(value), 300);
  }

  useEffect(() => {
    function handleClick(e) {
      if (customerResultsRef.current && !customerResultsRef.current.contains(e.target)) {
        setShowCustomerResults(false);
      }
      if (productResultsRef.current && !productResultsRef.current.contains(e.target)) {
        setShowProductResults(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  function selectCustomer(c) {
    setSelectedCustomer(c);
    setCustomerSearch('');
    setShowCustomerResults(false);
    setShowNewForm(false);
  }

  function clearCustomer() {
    setSelectedCustomer(null);
    setShowNewForm(false);
    setNewCustomer({ name: '', phone: '', email: '' });
  }

  function addToCart(product) {
    setCart(prev => {
      const existing = prev.find(c => c.product_id === product.id);
      if (existing) {
        if (existing.quantity >= existing.stock) return prev;
        return prev.map(c => c.product_id === product.id ? { ...c, quantity: c.quantity + 1 } : c);
      }
      return [{ product_id: product.id, name: product.name, code: product.code, image_url: product.image_url, price: parseFloat(product.price), quantity: 1, stock: product.stock }, ...prev];
    });
    setProductSearch('');
    setProductResults([]);
    setShowProductResults(false);
  }

  function updateQty(productId, delta) {
    setCart(prev => prev.map(c => {
      if (c.product_id !== productId) return c;
      const newQty = delta > 0 && c.quantity >= c.stock ? c.quantity : c.quantity + delta;
      if (newQty <= 0) return null;
      return { ...c, quantity: newQty };
    }).filter(Boolean));
  }

  function removeFromCart(productId) {
    setCart(prev => prev.filter(c => c.product_id !== productId));
  }

  const cartTotal = cart.reduce((sum, c) => sum + c.price * c.quantity, 0);

  async function handleCreate() {
    setError('');
    const custId = selectedCustomer?.id;
    const custData = showNewForm && newCustomer.name.trim() ? {
      name: newCustomer.name.trim(),
      phone: newCustomer.phone.trim() || null,
      email: newCustomer.email.trim() || null,
    } : null;

    if (!custId && !custData) {
      setError('Seleccione un cliente o cree uno nuevo');
      return;
    }
    if (cart.length === 0) {
      setError('Agregue al menos un producto');
      return;
    }
    if (!deposit || parseFloat(deposit) <= 0) {
      setError('El depósito debe ser mayor a cero');
      return;
    }
    if (parseFloat(deposit) > cartTotal) {
      setError('El depósito no puede exceder el total');
      return;
    }

    const body = {
      deposit: parseFloat(deposit),
      items: cart.map(c => ({ product_id: c.product_id, quantity: c.quantity })),
    };
    if (notes.trim()) body.notes = notes.trim();
    if (custId) {
      body.customer_id = custId;
    } else {
      body.customer = custData;
    }

    try {
      await layawaysApi.create(body);
      onCreated();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="layaway-create">
      <button className="btn btn-secondary" onClick={onBack} style={{ marginBottom: '0.75rem' }}>← Volver</button>
      {error && <p className="error-text">{error}</p>}

      <div className="customer-section">
        <h3>Cliente</h3>
        {selectedCustomer ? (
          <div className="customer-selected">
            <span><strong>{selectedCustomer.name}</strong>{selectedCustomer.phone ? ` — ${selectedCustomer.phone}` : ''}</span>
            <button className="btn btn-secondary" onClick={clearCustomer}>Cambiar</button>
          </div>
        ) : (
          <div ref={customerResultsRef} className="cart-search">
            <input
              className="search-input"
              placeholder="Buscar cliente por nombre o teléfono..."
              value={customerSearch}
              onChange={e => handleCustomerSearchChange(e.target.value)}
              onFocus={() => customerResults.length > 0 && setShowCustomerResults(true)}
              autoComplete="off"
              autoCorrect="off"
              spellCheck="false"
            />
            {showCustomerResults && customerResults.length > 0 && (
              <div className="customer-search-results">
                {customerResults.map(c => (
                  <div key={c.id} className="customer-result-item" onClick={() => selectCustomer(c)}>
                    <span className="result-name">{c.name}</span>
                    <span className="result-code">{c.phone || ''}</span>
                  </div>
                ))}
              </div>
            )}
            <button className="btn btn-secondary" style={{ marginTop: '0.5rem' }} onClick={() => setShowNewForm(!showNewForm)}>
              {showNewForm ? 'Cancelar' : '+ Cliente Nuevo'}
            </button>
            {showNewForm && (
              <div className="customer-new-form">
                <input
                  placeholder="Nombre *"
                  value={newCustomer.name}
                  onChange={e => setNewCustomer({ ...newCustomer, name: e.target.value })}
                  autoComplete="off"
                  autoCorrect="off"
                  spellCheck="false"
                />
                <input
                  placeholder="Teléfono"
                  value={newCustomer.phone}
                  onChange={e => setNewCustomer({ ...newCustomer, phone: e.target.value })}
                  autoComplete="off"
                  autoCorrect="off"
                  spellCheck="false"
                />
                <input
                  placeholder="Email"
                  value={newCustomer.email}
                  onChange={e => setNewCustomer({ ...newCustomer, email: e.target.value })}
                  autoComplete="off"
                  autoCorrect="off"
                  spellCheck="false"
                />
              </div>
            )}
          </div>
        )}
      </div>

      <div className="products-section">
        <h3>Productos</h3>
        {can('apartado.create') && (
        <>
        <div ref={productResultsRef} className="cart-search">
          <input
            className="search-input"
            placeholder="Buscar producto por nombre o código..."
            value={productSearch}
            onChange={e => handleProductSearchChange(e.target.value)}
            onFocus={() => productResults.length > 0 && setShowProductResults(true)}
            autoComplete="off"
            autoCorrect="off"
            spellCheck="false"
          />
          {showProductResults && productResults.length > 0 && (
            <div className="search-results">
              {productResults.map(p => (
                <div key={p.id} className="search-result-item" onClick={() => addToCart(p)}>
                  {p.image_url ? (
                    <img className="result-thumb" src={p.image_url} alt="" />
                  ) : (
                    <div className="result-thumb result-thumb-empty" />
                  )}
                  <span className="result-name">{p.name}</span>
                  <span className="result-code">{p.code}</span>
                  {p.ubicacion && <span className="result-ubicacion">{p.ubicacion}</span>}
                  <span className="result-price">${formatPrice(p.price)}</span>
                  <span className="result-stock">Stock: {p.stock}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        </>
        )}

        {cart.length > 0 && (
          <div className="cart-items">
            {cart.map(c => (
              <div key={c.product_id} className="cart-item">
                {c.image_url ? (
                  <img className="cart-item-thumb" src={c.image_url} alt="" />
                ) : (
                  <div className="cart-item-thumb cart-item-thumb-empty" />
                )}
                <div className="cart-item-info">
                  <span className="cart-item-name">{c.name}</span>
                  <span className="cart-item-code">{c.code}</span>
                  {c.stock !== undefined && <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Stock: {c.stock}</span>}
                  {c.stock !== undefined && c.quantity >= c.stock && <span style={{ color: 'var(--danger)', fontSize: '0.75rem', fontWeight: 600 }}>Stock máximo</span>}
                  {c.stock !== undefined && c.quantity < c.stock && c.quantity >= c.stock * 0.8 && <span style={{ color: 'var(--warning)', fontSize: '0.75rem', fontWeight: 600 }}>Poco stock</span>}
                </div>
                <div className="cart-item-controls">
                  <button className="btn-qty" onClick={() => updateQty(c.product_id, -1)} disabled={c.quantity <= 1}>−</button>
                  <span className="cart-qty">{c.quantity}</span>
                  <button className="btn-qty" onClick={() => updateQty(c.product_id, 1)} disabled={c.quantity >= c.stock}>+</button>
                    <span className="cart-item-price">${formatPrice(c.price * c.quantity)}</span>
                  <button className="btn-remove" onClick={() => removeFromCart(c.product_id)}>✕</button>
                </div>
              </div>
            ))}
            <div className="cart-total-row">
              <span className="cart-total-label">Total</span>
              <span className="cart-total-amount">${formatPrice(cartTotal)}</span>
            </div>
          </div>
        )}

        {cart.length > 0 && (
          <div className="layaway-deposit-section">
            <div className="form-group">
              <label>Depósito</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                max={cartTotal}
                placeholder="Monto del depósito"
                value={deposit}
                onChange={e => setDeposit(e.target.value)}
                autoComplete="off"
                autoCorrect="off"
                spellCheck="false"
              />
            </div>
            <p className="layaway-balance-preview">
              Balance restante: <strong>${formatPrice(cartTotal - parseFloat(deposit || 0))}</strong>
            </p>
            <div className="form-group">
              <label>Notas</label>
              <textarea
                className="notes-textarea"
                placeholder="Notas opcionales del apartado..."
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={3}
                autoComplete="off"
                autoCorrect="off"
              />
            </div>
            <button className="btn btn-primary btn-checkout" onClick={() => setConfirmCreate(true)}>
              Crear Apartado — Depósito ${formatPrice(deposit || 0)}
            </button>
          </div>
        )}

        {confirmCreate && (
          <ConfirmDialog
            title="Crear Apartado"
            message={`¿Crear apartado para ${selectedCustomer?.name || newCustomer.name.trim()} con ${cart.length} artículo(s) y depósito de ${formatPrice(deposit)}?`}
            onConfirm={() => { setConfirmCreate(false); handleCreate(); }}
            onCancel={() => setConfirmCreate(false)}
          />
        )}

        {cart.length === 0 && (
          <p className="empty-state">Busca productos para agregar al apartado.</p>
        )}
      </div>
    </div>
  );
}

function DetailView({ layaway, onBack, onPayment, onCancel, onComplete, onUpdated }) {
  const { can } = useAuth();
  const [paymentAmount, setPaymentAmount] = useState('');
  const [detailError, setDetailError] = useState('');
  const [productSearch, setProductSearch] = useState('');
  const [productResults, setProductResults] = useState([]);
  const [showProductResults, setShowProductResults] = useState(false);
  const [editingItemId, setEditingItemId] = useState(null);
  const [editingQty, setEditingQty] = useState('');
  const [notesDraft, setNotesDraft] = useState('');
  const productTimer = useRef(null);
  const productResultsRef = useRef(null);

  const days = daysElapsed(layaway.created_at);
  const overdue = days > DAYS_OVERDUE;
  const isActive = layaway.status === 'active';

  useEffect(() => {
    setNotesDraft(layaway.notes || '');
  }, [layaway.notes]);

  const refreshLayaway = useCallback(async () => {
    try {
      const updated = await layawaysApi.get(layaway.id);
      onUpdated(updated);
    } catch {}
  }, [layaway.id, onUpdated]);

  async function handleAddPayment() {
    if (!paymentAmount || parseFloat(paymentAmount) <= 0) return;
    setDetailError('');
    try {
      const updated = await layawaysApi.addPayment(layaway.id, parseFloat(paymentAmount));
      onUpdated(updated);
      setPaymentAmount('');
    } catch (e) {
      setDetailError(e.message);
    }
  }

  async function handleChangeQty(item, delta) {
    const newQty = item.quantity + delta;
    if (newQty < 1) return;
    setDetailError('');
    try {
      const updated = await layawaysApi.updateItem(layaway.id, item.id, newQty);
      onUpdated(updated);
    } catch (e) {
      setDetailError(e.message);
    }
  }

  async function handleRemoveItem(item) {
    setDetailError('');
    try {
      const updated = await layawaysApi.removeItem(layaway.id, item.id);
      onUpdated(updated);
    } catch (e) {
      setDetailError(e.message);
    }
  }

  async function handleSaveQty(item) {
    const qty = parseInt(editingQty, 10);
    setEditingItemId(null);
    if (isNaN(qty) || qty < 1 || qty === item.quantity) return;
    setDetailError('');
    try {
      const updated = await layawaysApi.updateItem(layaway.id, item.id, qty);
      onUpdated(updated);
    } catch (e) {
      setDetailError(e.message);
    }
  }

  async function handleSaveNotes() {
    const value = notesDraft.trim();
    if (value === (layaway.notes || '').trim()) return;
    setDetailError('');
    try {
      const updated = await layawaysApi.update(layaway.id, { notes: value || null });
      onUpdated(updated);
    } catch (e) {
      setDetailError(e.message);
    }
  }

  const searchProducts = useCallback(async (q) => {
    if (!q.trim()) { setProductResults([]); return; }
    try {
      const res = await productsApi.list({ q, perPage: 10 });
      const existingIds = new Set(layaway.items.map(i => i.product_id));
      setProductResults(res.products.filter(p => p.stock > 0 && !existingIds.has(p.id)));
      setShowProductResults(true);
    } catch {}
  }, [layaway.items]);

  function handleProductSearchChange(value) {
    setProductSearch(value);
    clearTimeout(productTimer.current);
    productTimer.current = setTimeout(() => searchProducts(value), 300);
  }

  async function handleAddProduct(product) {
    setDetailError('');
    try {
      const updated = await layawaysApi.addItem(layaway.id, product.id, 1);
      onUpdated(updated);
      setProductSearch('');
      setProductResults([]);
      setShowProductResults(false);
    } catch (e) {
      setDetailError(e.message);
    }
  }

  useEffect(() => {
    function handleClick(e) {
      if (productResultsRef.current && !productResultsRef.current.contains(e.target)) {
        setShowProductResults(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  function handleCancel() {
    setDetailError('');
    onCancel(layaway.id);
  }

  function handleComplete() {
    setDetailError('');
    onComplete(layaway.id);
  }

  return (
    <div className="layaway-detail">
      <button className="btn btn-secondary" onClick={onBack}>← Volver</button>

      {detailError && <p className="error-text">{detailError}</p>}

      <div className={`detail-section ${overdue && isActive ? 'layaway-overdue' : ''}`}>
        <h3>Cliente</h3>
        <p><strong>{layaway.customer_name}</strong></p>
        <p className="layaway-days">
          {days} día(s) desde creación
          {overdue && isActive && <span className="overdue-warning"> — VENCIDO</span>}
        </p>
        {layaway.created_by_name && <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>Registrado por: {layaway.created_by_name}</p>}
      </div>

      <div className="detail-section">
        <h3>Productos</h3>
        <table className="receipt-items">
          <thead>
            <tr>
              <th>Producto</th>
              <th>Código</th>
              <th>Cant</th>
              <th>Precio</th>
              <th>Subtotal</th>
              {isActive && <th style={{ width: '40px' }}></th>}
            </tr>
          </thead>
          <tbody>
            {layaway.items.map(item => (
              <tr key={item.id}>
                <td>{item.product_name}</td>
                <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{item.product_code}</td>
                <td style={{ textAlign: 'center' }}>
                  {editingItemId === item.id ? (
                    <input
                      type="number"
                      min="1"
                      value={editingQty}
                      onChange={e => setEditingQty(e.target.value)}
                      onBlur={() => handleSaveQty(item)}
                      onKeyDown={e => { if (e.key === 'Enter') handleSaveQty(item); if (e.key === 'Escape') setEditingItemId(null); }}
                      autoFocus
                      style={{ width: '50px', textAlign: 'center' }}
                    />
                  ) : isActive ? (
                    <span className="qty-controls">
                      <button className="qty-btn" onClick={() => handleChangeQty(item, -1)} disabled={item.quantity <= 1}>−</button>
                      <span
                        className="qty-value layaway-editable"
                        onClick={() => { setEditingItemId(item.id); setEditingQty(String(item.quantity)); }}
                        title="Clic para editar cantidad"
                      >
                        {item.quantity}
                      </span>
                      <button className="qty-btn" onClick={() => handleChangeQty(item, 1)}>+</button>
                    </span>
                  ) : (
                    item.quantity
                  )}
                </td>
                <td style={{ textAlign: 'center' }}>${formatPrice(item.unit_price)}</td>
                <td style={{ textAlign: 'right' }}>${formatPrice(parseFloat(item.unit_price) * item.quantity)}</td>
                {isActive && (
                  <td style={{ textAlign: 'center' }}>
                    <button className="edit-icon layaway-remove-item" onClick={() => handleRemoveItem(item)} title="Quitar producto">✕</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        <div className="receipt-total" style={{ textAlign: 'right' }}>Total: ${formatPrice(layaway.total)}</div>

        {isActive && can('apartado.edit') && (
          <div className="cart-search" ref={productResultsRef}>
            <input
              className="search-input"
              placeholder="Agregar producto..."
              value={productSearch}
              onChange={e => handleProductSearchChange(e.target.value)}
              onFocus={() => productResults.length > 0 && setShowProductResults(true)}
              autoComplete="off"
              autoCorrect="off"
              spellCheck="false"
            />
            {showProductResults && productResults.length > 0 && (
              <div className="search-results">
                {productResults.map(p => (
                  <div key={p.id} className="search-result-item" onClick={() => handleAddProduct(p)}>
                    {p.image_url ? (
                      <img className="result-thumb" src={p.image_url} alt="" />
                    ) : (
                      <div className="result-thumb result-thumb-empty" />
                    )}
                    <span className="result-name">{p.name}</span>
                    <span className="result-code">{p.code}</span>
                    {p.ubicacion && <span className="result-ubicacion">{p.ubicacion}</span>}
                    <span className="result-price">${formatPrice(p.price)}</span>
                    <span className="result-stock">Stock: {p.stock}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="detail-section">
        <h3>Notas</h3>
        <textarea
          className="notes-textarea"
          value={notesDraft}
          onChange={e => setNotesDraft(e.target.value)}
          rows={3}
          disabled={!isActive}
          autoComplete="off"
          autoCorrect="off"
        />
        {isActive && can('apartado.edit') && (
          <div className="layaway-notes-actions">
            <button className="btn btn-primary" onClick={handleSaveNotes}>Actualizar notas</button>
          </div>
        )}
      </div>

      <div className="detail-section">
        <h3>Abonos</h3>
        {layaway.payments.length === 0 ? (
          <p className="empty-state">Sin abonos registrados.</p>
        ) : (
          <table className="receipt-items">
            <thead>
              <tr><th>Fecha</th><th>Monto</th></tr>
            </thead>
            <tbody>
              {layaway.payments.map(p => (
                <tr key={p.id}>
                  <td>{new Date(p.created_at + 'Z').toLocaleString('es-MX')}</td>
                  <td style={{ textAlign: 'right' }}>${formatPrice(p.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="layaway-balance-section">
          <span className="layaway-balance-label">Saldo pendiente:</span>
          <span className={`layaway-balance-amount ${isActive && parseFloat(layaway.balance) > 0 ? 'text-danger' : 'text-success'}`}>
            ${formatPrice(layaway.balance)}
          </span>
        </div>
      </div>

      {layaway.sale_id && (
        <div className="detail-section">
          <p className="text-success">Completado — Venta #{layaway.sale_id} generada</p>
        </div>
      )}

      {isActive && can('apartado.edit') && (
        <div className="detail-section">
          <h3>Agregar Abono</h3>
          <div className="payment-form">
            <input
              type="number"
              step="0.01"
              min="0.01"
              placeholder="Monto"
              value={paymentAmount}
              onChange={e => setPaymentAmount(e.target.value)}
              autoComplete="off"
              autoCorrect="off"
              spellCheck="false"
            />
            <button className="btn btn-primary" onClick={handleAddPayment} disabled={!paymentAmount || parseFloat(paymentAmount) <= 0}>
              Abonar
            </button>
          </div>
          <div className="layaway-actions-detail">
            <button className="btn btn-primary" onClick={handleComplete}>
              Completar Apartado
            </button>
            <button className="btn btn-danger" onClick={handleCancel}>
              Cancelar Apartado
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
