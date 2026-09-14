import { useCart } from '../context/CartContext.jsx';
import StockBadge from './StockBadge.jsx';
import { formatPrice } from '../utils.js';

export default function CartItemRow({ item }) {
  const { updateQty, removeItem } = useCart();

  return (
    <div className="cart-item">
      {item.image_url ? (
        <img className="cart-item__thumb" src={item.image_url} alt={item.name} loading="lazy" decoding="async" />
      ) : (
        <span className="cart-item__thumb cart-item__thumb--empty" />
      )}
      <div className="cart-item__info">
        <span className="cart-item__name">{item.name}</span>
        <span className="cart-item__code">{item.code}</span>
        <StockBadge stock={item.stock} quantity={item.quantity} />
      </div>
      <div className="cart-item__controls">
        <button type="button" className="cart-item__qty-btn" onClick={() => updateQty(item.product_id, -1)} disabled={item.quantity <= 1} aria-label={`Disminuir cantidad de ${item.name}`}>−</button>
        <span className="cart-item__qty">{item.quantity}</span>
        <button type="button" className="cart-item__qty-btn" onClick={() => updateQty(item.product_id, 1)} disabled={item.quantity >= item.stock} aria-label={`Aumentar cantidad de ${item.name}`}>+</button>
        <span className="cart-item__price">${formatPrice(item.price * item.quantity)}</span>
        <button type="button" className="cart-item__remove-btn" onClick={() => removeItem(item.product_id)} aria-label={`Quitar ${item.name}`}>✕</button>
      </div>
    </div>
  );
}