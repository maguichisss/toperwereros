import { useState, useEffect, useRef, useCallback } from 'react';
import { layawaysApi, customersApi } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx';
import { useCart } from '../context/CartContext.jsx';
import ConfirmDialog from './ConfirmDialog.jsx';
import ProductSearchBox from './ProductSearchBox.jsx';
import CartItemRow from './CartItemRow.jsx';
import { formatPrice } from '../utils.js';

export default function LayawayCreateView({ onBack, onCreated }) {
  const { can } = useAuth();
  const { items: cart, addItem, clearCart, total: cartTotal } = useCart();
  const [step, setStep] = useState('customer');
  const [error, setError] = useState('');

  const [customerSearch, setCustomerSearch] = useState('');
  const [customerResults, setCustomerResults] = useState([]);
  const [showCustomerResults, setShowCustomerResults] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [newCustomer, setNewCustomer] = useState({ name: '', phone: '', email: '' });

  const [deposit, setDeposit] = useState('');
  const [notes, setNotes] = useState('');
  const [confirmCreate, setConfirmCreate] = useState(false);

  const customerTimer = useRef(null);
  const customerResultsRef = useRef(null);

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

  useEffect(() => {
    function handleClick(e) {
      if (customerResultsRef.current && !customerResultsRef.current.contains(e.target)) {
        setShowCustomerResults(false);
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
      clearCart();
      onCreated();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="layaway-create">
      <button type="button" className="btn btn--secondary btn--back" onClick={onBack}>← Volver</button>
      {error && <p className="error-text">{error}</p>}

      <div className="customer-section">
        <h3>Cliente</h3>
        {selectedCustomer ? (
          <div className="customer-selected">
            <span><strong>{selectedCustomer.name}</strong>{selectedCustomer.phone ? ` — ${selectedCustomer.phone}` : ''}</span>
            <button type="button" className="btn btn--secondary" onClick={clearCustomer}>Cambiar</button>
          </div>
        ) : (
          <div ref={customerResultsRef} className="cart-search customer-search">
            <input
              type="search"
              enterKeyHint="search"
              className="search-input"
              placeholder="Buscar cliente por nombre o teléfono..."
              aria-label="Buscar cliente por nombre o teléfono"
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
                  <button key={c.id} type="button" className="customer-result-item" onClick={() => selectCustomer(c)} aria-label={`${c.name} ${c.phone || ''}`}>
                    <span className="customer-result-item__name">{c.name}</span>
                    <span className="customer-result-item__phone">{c.phone || ''}</span>
                  </button>
                ))}
              </div>
            )}
            <button type="button" className="btn btn--secondary customer-toggle" onClick={() => setShowNewForm(!showNewForm)}>
              {showNewForm ? 'Cancelar' : '+ Cliente Nuevo'}
            </button>
            {showNewForm && (
              <div className="customer-new-form">
                <input
                  type="text"
                  aria-label="Nombre del cliente"
                  placeholder="Nombre *"
                  autoComplete="name"
                  autoCorrect="off"
                  spellCheck="false"
                  value={newCustomer.name}
                  onChange={e => setNewCustomer({ ...newCustomer, name: e.target.value })}
                />
                <input
                  type="tel"
                  inputMode="tel"
                  aria-label="Teléfono del cliente"
                  placeholder="Teléfono"
                  autoComplete="tel"
                  autoCorrect="off"
                  spellCheck="false"
                  value={newCustomer.phone}
                  onChange={e => setNewCustomer({ ...newCustomer, phone: e.target.value })}
                />
                <input
                  type="email"
                  aria-label="Email del cliente"
                  placeholder="Email"
                  autoComplete="email"
                  autoCorrect="off"
                  spellCheck="false"
                  value={newCustomer.email}
                  onChange={e => setNewCustomer({ ...newCustomer, email: e.target.value })}
                />
              </div>
            )}
          </div>
        )}
      </div>

      <div className="products-section">
        <h3>Productos</h3>
        {can('apartado.create') && (
          <ProductSearchBox placeholder="Buscar producto por nombre o código..." onSelect={addItem} />
        )}

        {cart.length > 0 && (
          <div className="cart-items">
            {cart.map(c => (
              <CartItemRow key={c.product_id} item={c} />
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
              <label htmlFor="layaway-deposit">Depósito</label>
              <input
                id="layaway-deposit"
                type="number"
                inputMode="decimal"
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
              <label htmlFor="layaway-notes">Notas</label>
              <textarea
                id="layaway-notes"
                className="notes-textarea"
                placeholder="Notas opcionales del apartado..."
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={3}
                autoComplete="off"
                autoCorrect="off"
                spellCheck="false"
              />
            </div>
            <button type="button" className="btn btn--primary btn--checkout" onClick={() => setConfirmCreate(true)}>
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