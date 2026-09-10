import { useState, useEffect, useCallback } from 'react';
import { salesApi } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx';
import { useCart } from '../context/CartContext.jsx';
import { formatPrice } from '../utils.js';
import ConfirmDialog from './ConfirmDialog.jsx';
import ProductSearchBox from './ProductSearchBox.jsx';
import CartItemRow from './CartItemRow.jsx';

export default function SaleCart() {
  const { can } = useAuth();
  const { items: cart, addItem, clearCart, total: cartTotal } = useCart();
  const [mode, setMode] = useState('cart');
  const [saleResult, setSaleResult] = useState(null);
  const [error, setError] = useState('');
  const [sales, setSales] = useState([]);
  const [salesPage, setSalesPage] = useState(1);
  const [selectedSale, setSelectedSale] = useState(null);
  const [confirmCheckout, setConfirmCheckout] = useState(false);
  const [datePreset, setDatePreset] = useState('last30');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  async function handleCheckout() {
    if (cart.length === 0) return;
    setError('');
    try {
      const result = await salesApi.create({ items: cart.map(c => ({ product_id: c.product_id, quantity: c.quantity })) });
      setSaleResult(result);
      clearCart();
    } catch (e) {
      setError(e.message);
    }
  }

  function resetSale() {
    setSaleResult(null);
    setError('');
  }

  function getDateRange() {
    const today = new Date();
    const fmt = d => d.toISOString().slice(0, 10);
    switch (datePreset) {
      case 'today':
        return { startDate: fmt(today), endDate: fmt(today) };
      case 'week': {
        const d = new Date(today);
        d.setDate(d.getDate() - 6);
        return { startDate: fmt(d), endDate: fmt(today) };
      }
      case 'month': {
        const d = new Date(today.getFullYear(), today.getMonth(), 1);
        return { startDate: fmt(d), endDate: fmt(today) };
      }
      case 'last30': {
        const d = new Date(today);
        d.setDate(d.getDate() - 29);
        return { startDate: fmt(d), endDate: fmt(today) };
      }
      case 'custom':
        return { startDate: dateFrom || null, endDate: dateTo || null };
      default:
        return {};
    }
  }

  const loadSales = useCallback(async () => {
    try {
      const { startDate, endDate } = getDateRange();
      const res = await salesApi.list({ page: salesPage, perPage: 20, startDate, endDate });
      setSales(res);
    } catch {}
  }, [salesPage, datePreset, dateFrom, dateTo]);

  useEffect(() => {
    if (mode === 'history') loadSales();
  }, [mode, loadSales]);

  useEffect(() => {
    setSalesPage(1);
  }, [datePreset, dateFrom, dateTo]);

  if (saleResult) {
    return (
      <div className="sale-receipt">
        <div className="receipt-card">
          <h2>Venta #{saleResult.id}</h2>
          <p className="receipt-date">{new Date(saleResult.created_at + 'Z').toLocaleString('es-MX')}</p>
          <table className="receipt-items">
            <thead>
              <tr><th>Código</th><th>Producto</th><th>Cant</th><th>Precio</th><th>Subtotal</th></tr>
            </thead>
            <tbody>
              {saleResult.items.map(item => (
                <tr key={item.id}>
                  <td>{item.product_code}</td>
                  <td>{item.product_name}</td>
                  <td>{item.quantity}</td>
                  <td>${formatPrice(item.unit_price)}</td>
                  <td>${formatPrice(parseFloat(item.unit_price) * item.quantity)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="receipt-total">Total: ${formatPrice(saleResult.total)}</div>
            {saleResult.created_by_name && <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>Atendido por: {saleResult.created_by_name}</p>}
          <button className="btn btn-primary" onClick={resetSale}>Nueva Venta</button>
        </div>
      </div>
    );
  }

  return (
    <div className="sales-view">
      <div className="sales-tabs">
        <button className={mode === 'cart' ? 'active' : ''} onClick={() => { setMode('cart'); setSelectedSale(null); }}>Nueva Venta</button>
        <button className={mode === 'history' ? 'active' : ''} onClick={() => setMode('history')}>Historial</button>
      </div>

      {mode === 'cart' && (
        <div className="cart-mode">
          {can('sale.create') && (
            <ProductSearchBox placeholder="Buscar producto por nombre o código..." onSelect={addItem} />
          )}

          {cart.length === 0 && !error && (
            <p className="empty-state">Busca y agrega productos al carrito para iniciar una venta.</p>
          )}

          {cart.length > 0 && (
            <div className="cart-items">
              <div className="cart-items-scroll">
                {cart.map(c => (
                  <CartItemRow key={c.product_id} item={c} />
                ))}
              </div>
              <div className="cart-total-row">
                <span className="cart-total-label">Total</span>
                <span className="cart-total-amount">${formatPrice(cartTotal)}</span>
              </div>
              {can('sale.create') && (
              <button className="btn btn-primary btn-checkout" onClick={() => setConfirmCheckout(true)}>
                Cobrar ${formatPrice(cartTotal)}
              </button>
              )}
            </div>
          )}

          {confirmCheckout && can('sale.create') && (
            <ConfirmDialog
              title="Confirmar Venta"
              message={`¿Cobrar ${formatPrice(cartTotal)} por ${cart.length} artículo(s)?`}
              onConfirm={() => { setConfirmCheckout(false); handleCheckout(); }}
              onCancel={() => setConfirmCheckout(false)}
            />
          )}

          {error && <p className="error-text">{error}</p>}
        </div>
      )}

      {mode === 'history' && !selectedSale && (
        <div className="filter-bar" style={{ marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.4rem' }}>
          {[
            { key: 'today', label: 'Hoy' },
            { key: 'week', label: 'Esta semana' },
            { key: 'month', label: 'Este mes' },
            { key: 'last30', label: 'Últimos 30 días' },
            { key: 'all', label: 'Todo' },
            { key: 'custom', label: 'Personalizado' },
          ].map(p => (
            <button
              key={p.key}
              className={`btn ${datePreset === p.key ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.8rem', padding: '0.3rem 0.6rem' }}
              onClick={() => setDatePreset(p.key)}
            >
              {p.label}
            </button>
          ))}
          {datePreset === 'custom' && (
            <>
              <input
                type="date"
                value={dateFrom}
                onChange={e => setDateFrom(e.target.value)}
                style={{ padding: '0.3rem 0.4rem', border: '1px solid var(--border)', borderRadius: 4, fontSize: '0.8rem' }}
              />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>a</span>
              <input
                type="date"
                value={dateTo}
                onChange={e => setDateTo(e.target.value)}
                style={{ padding: '0.3rem 0.4rem', border: '1px solid var(--border)', borderRadius: 4, fontSize: '0.8rem' }}
              />
            </>
          )}
        </div>
      )}

      {mode === 'history' && (
        <div className="history-mode">
          {selectedSale ? (
            <div className="sale-detail">
              <button className="btn btn-secondary" onClick={() => setSelectedSale(null)}>← Volver</button>
              <div className="receipt-card">
                <h2>Venta #{selectedSale.id}</h2>
                <p className="receipt-date">{new Date(selectedSale.created_at + 'Z').toLocaleString('es-MX')}</p>
                <table className="receipt-items">
                  <thead>
                    <tr><th>Código</th><th>Producto</th><th>Cant</th><th>Precio</th><th>Subtotal</th></tr>
                  </thead>
                  <tbody>
                    {selectedSale.items.map(item => (
                      <tr key={item.id}>
                        <td>{item.product_code}</td>
                        <td>{item.product_name}</td>
                        <td>{item.quantity}</td>
                        <td>${formatPrice(item.unit_price)}</td>
                        <td>${formatPrice(parseFloat(item.unit_price) * item.quantity)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="receipt-total">Total: ${formatPrice(selectedSale.total)}</div>
                {selectedSale.created_by_name && <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Atendido por: {selectedSale.created_by_name}</p>}
              </div>
            </div>
          ) : (
            <>
              {sales.length === 0 ? (
                <p className="empty-state">
                  {datePreset !== 'all' ? 'No hay ventas en el rango seleccionado.' : 'No hay ventas registradas.'}
                </p>
              ) : (
                <div className="sale-list">
                  {sales.map(s => (
                    <div key={s.id} className="sale-list-item" onClick={() => setSelectedSale(s)}>
                      <span className="sale-list-id">#{s.id}</span>
                      <span className="sale-list-date">{new Date(s.created_at + 'Z').toLocaleString('es-MX')}</span>
                      <span className="sale-list-count">{s.items?.length || 0} artículos</span>
                      <span className="sale-list-total">${formatPrice(s.total)}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}