import { useCart } from '../context/CartContext.jsx';
import StockBadge from './StockBadge.jsx';
import { formatPrice } from '../utils.js';

export default function CartItemRow({ item }) {
  const { updateQty, removeItem } = useCart();

  return (
    <div className="cart-item">
      {item.image_url ? (
        <img className="cart-item-thumb" src={item.image_url} alt="" />
      ) : (
        <div className="cart-item-thumb cart-item-thumb-empty" />
      )}
      <div className="cart-item-info">
        <span className="cart-item-name">{item.name}</span>
        <span className="cart-item-code">{item.code}</span>
        <StockBadge stock={item.stock} quantity={item.quantity} />
      </div>
      <div className="cart-item-controls">
        <button className="btn-qty" onClick={() => updateQty(item.product_id, -1)} disabled={item.quantity <= 1}>−</button>
        <span className="cart-qty">{item.quantity}</span>
        <button className="btn-qty" onClick={() => updateQty(item.product_id, 1)} disabled={item.quantity >= item.stock}>+</button>
        <span className="cart-item-price">${formatPrice(item.price * item.quantity)}</span>
        <button className="btn-remove" onClick={() => removeItem(item.product_id)}>✕</button>
      </div>
    </div>
  );
}