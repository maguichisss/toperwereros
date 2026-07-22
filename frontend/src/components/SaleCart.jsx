import { useState, useEffect, useCallback, useRef } from 'react';
import { salesApi, productsApi } from '../api/client.js';
import { formatPrice } from '../utils.js';

export default function SaleCart() {
  const [mode, setMode] = useState('cart');
  const [cart, setCart] = useState([]);
  const [search, setSearch] = useState('');
  const [results, setResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [saleResult, setSaleResult] = useState(null);
  const [error, setError] = useState('');
  const [sales, setSales] = useState([]);
  const [salesTotal, setSalesTotal] = useState(0);
  const [salesPage, setSalesPage] = useState(1);
  const [selectedSale, setSelectedSale] = useState(null);
  const searchTimer = useRef(null);
  const resultsRef = useRef(null);

  const searchProducts = useCallback(async (q) => {
    if (!q.trim()) { setResults([]); return; }
    try {
      const res = await productsApi.list({ q, perPage: 10 });
      setResults(res.products.filter(p => p.stock > 0));
      setShowResults(true);
    } catch {}
  }, []);

  function handleSearchChange(value) {
    setSearch(value);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => searchProducts(value), 300);
  }

  useEffect(() => {
    function handleClick(e) {
      if (resultsRef.current && !resultsRef.current.contains(e.target)) {
        setShowResults(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  function addToCart(product) {
    setCart(prev => {
      const existing = prev.find(c => c.product_id === product.id);
      if (existing) {
        if (existing.quantity >= existing.stock) return prev;
        return prev.map(c => c.product_id === product.id ? { ...c, quantity: c.quantity + 1 } : c);
      }
      return [...prev, { product_id: product.id, name: product.name, code: product.code, price: parseFloat(product.price), quantity: 1, stock: product.stock }];
    });
    setSearch('');
    setResults([]);
    setShowResults(false);
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

  async function handleCheckout() {
    if (cart.length === 0) return;
    setError('');
    try {
      const result = await salesApi.create({ items: cart.map(c => ({ product_id: c.product_id, quantity: c.quantity })) });
      setSaleResult(result);
      setCart([]);
    } catch (e) {
      setError(e.message);
    }
  }

  function resetSale() {
    setSaleResult(null);
    setError('');
  }

  const loadSales = useCallback(async () => {
    try {
      const res = await salesApi.list({ page: salesPage, perPage: 20 });
      setSales(res);
      setSalesTotal(res.total || res.length);
    } catch {}
  }, [salesPage]);

  useEffect(() => {
    if (mode === 'history') loadSales();
  }, [mode, loadSales]);

  if (saleResult) {
    return (
      <div className="sale-receipt">
        <div className="receipt-card">
          <h2>Venta #{saleResult.id}</h2>
          <p className="receipt-date">{new Date(saleResult.created_at + 'Z').toLocaleString('es-MX')}</p>
          <table className="receipt-items">
            <thead>
              <tr><th>Producto</th><th>Cant</th><th>Precio</th><th>Subtotal</th></tr>
            </thead>
            <tbody>
              {saleResult.items.map(item => (
                <tr key={item.id}>
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
          <div className="cart-search" ref={resultsRef}>
            <input
              className="search-input"
              placeholder="Buscar producto por nombre o código..."
              value={search}
              onChange={e => handleSearchChange(e.target.value)}
              onFocus={() => results.length > 0 && setShowResults(true)}
              autoComplete="off"
              autoCorrect="off"
              spellCheck="false"
            />
            {showResults && results.length > 0 && (
              <div className="search-results">
                {results.map(p => (
                  <div key={p.id} className="search-result-item" onClick={() => addToCart(p)}>
                    <span className="result-name">{p.name}</span>
                    <span className="result-code">{p.code}</span>
                    <span className="result-price">${formatPrice(p.price)}</span>
                    <span className="result-stock">Stock: {p.stock}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {cart.length === 0 && !error && (
            <p className="empty-state">Busca y agrega productos al carrito para iniciar una venta.</p>
          )}

          {cart.length > 0 && (
            <div className="cart-items">
              <div className="cart-items-scroll">
                {cart.map(c => (
                  <div key={c.product_id} className="cart-item">
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
              </div>
              <div className="cart-total-row">
                <span className="cart-total-label">Total</span>
                <span className="cart-total-amount">${formatPrice(cartTotal)}</span>
              </div>
              <button className="btn btn-primary btn-checkout" onClick={handleCheckout}>
                Cobrar ${formatPrice(cartTotal)}
              </button>
            </div>
          )}

          {error && <p className="error-text">{error}</p>}
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
                    <tr><th>Producto</th><th>Cant</th><th>Precio</th><th>Subtotal</th></tr>
                  </thead>
                  <tbody>
                    {selectedSale.items.map(item => (
                      <tr key={item.id}>
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
                <p className="empty-state">No hay ventas registradas.</p>
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
