import { useState, useEffect, useCallback, useRef } from 'react';
import { layawaysApi, customersApi, productsApi } from '../api/client.js';

const DAYS_OVERDUE = 21;

function daysElapsed(dateStr) {
  return Math.floor((Date.now() - new Date(dateStr + 'Z')) / 86400000);
}

export default function LayawayView() {
  const [mode, setMode] = useState('active');
  const [activeLayaways, setActiveLayaways] = useState([]);
  const [allLayaways, setAllLayaways] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedLayaway, setSelectedLayaway] = useState(null);

  const [error, setError] = useState('');

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

  async function handleCancel(id) {
    if (!window.confirm('¿Cancelar este apartado? Se restaurará el stock.')) return;
    try {
      await layawaysApi.cancel(id);
      loadActive();
      if (selectedId === id) handleBack();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleComplete(id) {
    if (!window.confirm('¿Completar este apartado? Se creará una venta.')) return;
    try {
      await layawaysApi.complete(id);
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

  return (
    <div className="layaway-view">
      <div className="sales-tabs">
        <button className={mode === 'active' ? 'active' : ''} onClick={() => setMode('active')}>Apartados Activos</button>
        <button className={mode === 'all' ? 'active' : ''} onClick={() => setMode('all')}>Todos</button>
        <button className={mode === 'create' ? 'active' : ''} onClick={() => { setMode('create'); setError(''); }}>Nuevo Apartado</button>
      </div>

      {error && <p className="error-text">{error}</p>}

      {mode === 'active' && (
        <ActiveList
          layaways={activeLayaways}
          onSelect={handleSelect}
          onCancel={handleCancel}
          onRefresh={loadActive}
        />
      )}

      {mode === 'all' && (
        <AllList
          layaways={allLayaways}
          onSelect={handleSelect}
          onCancel={handleCancel}
          onRefresh={loadAll}
        />
      )}

      {mode === 'create' && (
        <CreateView onCreated={() => { setMode('active'); loadActive(); }} />
      )}

      {mode === 'detail' && selectedLayaway && (
        <DetailView
          layaway={selectedLayaway}
          onBack={handleBack}
          onPayment={handleAddPayment}
          onCancel={handleCancel}
          onComplete={handleComplete}
          onUpdated={setSelectedLayaway}
        />
      )}
    </div>
  );
}

function ActiveList({ layaways, onSelect, onCancel, onRefresh }) {
  useEffect(() => { onRefresh(); }, [onRefresh]);

  return (
    <div className="layaway-list">
      {layaways.length === 0 ? (
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
                <span className="layaway-customer">{l.customer_name}</span>
                <span className="layaway-items-count">{l.items?.length || 0} artículo(s)</span>
              </div>
              <div className="layaway-card-details">
                <span className="layaway-days">{days} día(s)</span>
                <span className="layaway-balance">${parseFloat(l.balance).toFixed(2)}</span>
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

function AllList({ layaways, onSelect, onCancel, onRefresh }) {
  useEffect(() => { onRefresh(); }, [onRefresh]);

  const statusLabel = { active: 'Activo', completed: 'Completado', cancelled: 'Cancelado' };
  const statusColor = { active: '#1a73e8', completed: '#43a047', cancelled: '#888' };

  return (
    <div className="layaway-list">
      {layaways.length === 0 ? (
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
                <span className="layaway-customer">{l.customer_name}</span>
                <span className="layaway-items-count">{l.items?.length || 0} artículo(s)</span>
              </div>
              <div className="layaway-card-details">
                <span style={{ color: statusColor[l.status], fontWeight: 600, fontSize: '0.8rem' }}>{statusLabel[l.status]}</span>
                <span className="layaway-days">{days} día(s)</span>
                <span className="layaway-balance">${parseFloat(l.balance).toFixed(2)}</span>
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

function CreateView({ onCreated }) {
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
      setProductResults(res.products);
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
        return prev.map(c => c.product_id === product.id ? { ...c, quantity: c.quantity + 1 } : c);
      }
      return [{ product_id: product.id, name: product.name, code: product.code, price: parseFloat(product.price), quantity: 1, stock: product.stock }, ...prev];
    });
    setProductSearch('');
    setProductResults([]);
    setShowProductResults(false);
  }

  function updateQty(productId, delta) {
    setCart(prev => prev.map(c => {
      if (c.product_id !== productId) return c;
      const newQty = c.quantity + delta;
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
                  <span className="result-name">{p.name}</span>
                  <span className="result-code">{p.code}</span>
                  <span className="result-price">${parseFloat(p.price).toFixed(2)}</span>
                  <span className="result-stock">Stock: {p.stock}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {cart.length > 0 && (
          <div className="cart-items">
            {cart.map(c => (
              <div key={c.product_id} className="cart-item">
                <div className="cart-item-info">
                  <span className="cart-item-name">{c.name}</span>
                  <span className="cart-item-code">{c.code}</span>
                </div>
                <div className="cart-item-controls">
                  <button className="btn-qty" onClick={() => updateQty(c.product_id, -1)} disabled={c.quantity <= 1}>−</button>
                  <span className="cart-qty">{c.quantity}</span>
                  <button className="btn-qty" onClick={() => updateQty(c.product_id, 1)}>+</button>
                  <span className="cart-item-price">${(c.price * c.quantity).toFixed(2)}</span>
                  <button className="btn-remove" onClick={() => removeFromCart(c.product_id)}>✕</button>
                </div>
              </div>
            ))}
            <div className="cart-total-row">
              <span className="cart-total-label">Total</span>
              <span className="cart-total-amount">${cartTotal.toFixed(2)}</span>
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
              Balance restante: <strong>${(cartTotal - parseFloat(deposit || 0)).toFixed(2)}</strong>
            </p>
            <button className="btn btn-primary btn-checkout" onClick={handleCreate}>
              Crear Apartado — Depósito ${parseFloat(deposit || 0).toFixed(2)}
            </button>
          </div>
        )}

        {cart.length === 0 && (
          <p className="empty-state">Busca productos para agregar al apartado.</p>
        )}
      </div>
    </div>
  );
}

function DetailView({ layaway, onBack, onPayment, onCancel, onComplete, onUpdated }) {
  const [paymentAmount, setPaymentAmount] = useState('');
  const [detailError, setDetailError] = useState('');

  const days = daysElapsed(layaway.created_at);
  const overdue = days > DAYS_OVERDUE;

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

  async function handleCancel() {
    if (!window.confirm('¿Cancelar este apartado? Se restaurará el stock.')) return;
    setDetailError('');
    try {
      await layawaysApi.cancel(layaway.id);
      onBack();
    } catch (e) {
      setDetailError(e.message);
    }
  }

  async function handleComplete() {
    if (!window.confirm('¿Completar este apartado? Se creará una venta.')) return;
    setDetailError('');
    try {
      const updated = await layawaysApi.complete(layaway.id);
      onUpdated(updated);
    } catch (e) {
      setDetailError(e.message);
    }
  }

  const isActive = layaway.status === 'active';

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
      </div>

      <div className="detail-section">
        <h3>Productos</h3>
        <table className="receipt-items">
          <thead>
            <tr><th>Producto</th><th>Código</th><th>Cant</th><th>Precio</th><th>Subtotal</th></tr>
          </thead>
          <tbody>
            {layaway.items.map(item => (
              <tr key={item.id}>
                <td>{item.product_name}</td>
                <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>{item.product_code}</td>
                <td style={{ textAlign: 'center' }}>{item.quantity}</td>
                <td style={{ textAlign: 'center' }}>${parseFloat(item.unit_price).toFixed(2)}</td>
                <td style={{ textAlign: 'right' }}>${(parseFloat(item.unit_price) * item.quantity).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="receipt-total" style={{ textAlign: 'right' }}>Total: ${parseFloat(layaway.total).toFixed(2)}</div>
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
                  <td style={{ textAlign: 'right' }}>${parseFloat(p.amount).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="layaway-balance-section">
          <span className="layaway-balance-label">Saldo pendiente:</span>
          <span className={`layaway-balance-amount ${isActive && parseFloat(layaway.balance) > 0 ? 'text-danger' : 'text-success'}`}>
            ${parseFloat(layaway.balance).toFixed(2)}
          </span>
        </div>
      </div>

      {layaway.sale_id && (
        <div className="detail-section">
          <p className="text-success">Completado — Venta #{layaway.sale_id} generada</p>
        </div>
      )}

      {isActive && (
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
