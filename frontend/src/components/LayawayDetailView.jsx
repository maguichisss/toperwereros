import { useState, useEffect } from 'react';
import { layawaysApi } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx';
import Toast from './Toast.jsx';
import useToast from '../hooks/useToast.js';
import { WhatsAppIcon } from './icons.jsx';
import ProductSearchBox from './ProductSearchBox.jsx';
import { formatPrice, DAYS_OVERDUE, daysElapsed } from '../utils.js';

export default function LayawayDetailView({ layaway, onBack, onCancel, onComplete, onUpdated }) {
  const { can } = useAuth();
  const [paymentAmount, setPaymentAmount] = useState('');
  const [detailError, setDetailError] = useState('');
  const [editingItemId, setEditingItemId] = useState(null);
  const [editingQty, setEditingQty] = useState('');
  const [notesDraft, setNotesDraft] = useState('');
  const { toast, notify, clear } = useToast();

  const days = daysElapsed(layaway.created_at);
  const overdue = days > DAYS_OVERDUE;
  const isActive = layaway.status === 'active';

  const phoneDigits = (layaway.customer_phone || '').replace(/\D/g, '');
  const waNumber = phoneDigits.length === 10 ? `52${phoneDigits}` : phoneDigits;
  const dueDate = new Date(layaway.created_at + 'Z');
  dueDate.setDate(dueDate.getDate() + DAYS_OVERDUE);
  const dueLabel = dueDate
    .toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' })
    .replace(/,\s*/g, ' ');
  const itemsList = (layaway.items || [])
    .map(i => `${i.product_name} - ${i.quantity} - $${formatPrice(parseFloat(i.unit_price) * i.quantity)}`)
    .join('\n');
  const waCreated = encodeURIComponent([
    `Estimada ${layaway.customer_name},`,
    `confirmamos su apartado con folio #${layaway.id}`,
    `con vigencia hasta el ${dueLabel}.`,
    '',
    itemsList,
    layaway.notes ? `(${layaway.notes})` : null,
    `Abono: $${formatPrice(layaway.deposit)}`,
    `TOTAL: $${formatPrice(layaway.total)}`,
    '',
    '¡Gracias!'
  ].filter(Boolean).join('\n'));
  const waReminder = encodeURIComponent(
    `Hola ${layaway.customer_name}, su apartado con folio ${layaway.id} tiene un saldo pendiente de $${formatPrice(layaway.balance)} y esta proximo a vencer el ${dueLabel}. ¡Gracias!`
  );

  useEffect(() => {
    setNotesDraft(layaway.notes || '');
  }, [layaway.notes]);

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
      notify('Notas actualizadas', 'success');
    } catch (e) {
      setDetailError(e.message);
    }
  }

  async function handleAddProduct(product) {
    setDetailError('');
    try {
      const updated = await layawaysApi.addItem(layaway.id, product.id, 1);
      onUpdated(updated);
    } catch (e) {
      setDetailError(e.message);
    }
  }

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
        <h3>Cliente: {layaway.customer_name}</h3>
        <p className="layaway-days">
          Apartado: #{layaway.id} registrado por {layaway.created_by_name || '—'} el {new Date(layaway.created_at + 'Z').toLocaleDateString('es-MX')} - {days} día(s)
          {overdue && isActive && <span className="overdue-warning"> — VENCIDO</span>}
        </p>
        {phoneDigits && (
          <div style={{ display: 'flex', gap: '1rem', marginTop: '0.4rem' }}>
            <a
              href={`https://wa.me/${waNumber}?text=${waCreated}`}
              target="_blank"
              rel="noopener noreferrer"
              className="wa-link"
            >
              <WhatsAppIcon size={16} />
              Confirmación
            </a>
            <a
              href={`https://wa.me/${waNumber}?text=${waReminder}`}
              target="_blank"
              rel="noopener noreferrer"
              className="wa-link"
            >
              <WhatsAppIcon size={16} />
              Recordatorio
            </a>
          </div>
        )}
      </div>

      <div className="detail-section">
        <h3>Productos</h3>
        <div style={{ overflowX: 'auto' }}>
          <table className="receipt-items sticky-table">
            <thead>
              <tr>
                <th>Producto</th>
                <th>Código</th>
                <th>Cant</th>
                <th>Precio</th>
                <th>Subtotal</th>
                {isActive && (
                  <th className="sticky-col" style={{ width: '40px', textAlign: 'center' }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M3 6h18" />
                      <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                      <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                      <line x1="10" y1="11" x2="10" y2="17" />
                      <line x1="14" y1="11" x2="14" y2="17" />
                    </svg>
                  </th>
                )}
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
                    <td className="sticky-col" style={{ textAlign: 'center' }}>
                      <button className="edit-icon layaway-remove-item" onClick={() => handleRemoveItem(item)} title="Quitar producto">✕</button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="receipt-total" style={{ textAlign: 'right' }}>Total: ${formatPrice(layaway.total)}</div>

        {isActive && can('apartado.edit') && (
          <ProductSearchBox
            placeholder="Agregar producto..."
            excludeIds={layaway.items.map(i => i.product_id)}
            onSelect={handleAddProduct}
          />
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
            <button className="btn btn-success" onClick={handleComplete}>
              Completar Apartado
            </button>
            <button className="btn btn-danger" onClick={handleCancel}>
              Cancelar Apartado
            </button>
          </div>
        </div>
      )}
      <Toast message={toast?.message} type={toast?.type} onClose={clear} />
    </div>
  );
}