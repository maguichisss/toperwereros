import { memo, useRef, useState } from 'react';
import { formatPrice } from '../utils.js';

const ProductCard = memo(({ product, onEdit, onDelete, onShowImage, canEdit, onAddToCart }) => {
  const clickTimer = useRef(null)
  const [added, setAdded] = useState(false)

  function handleClick() {
    if (clickTimer.current) {
      clearTimeout(clickTimer.current)
      clickTimer.current = null
      onShowImage(product.image_url)
    } else {
      clickTimer.current = setTimeout(() => {
        clickTimer.current = null
        onEdit(product)
      }, 250)
    }
  }

  function handleAddToCart(e) {
    e.stopPropagation()
    if (added) return
    onAddToCart(product)
    setAdded(true)
    setTimeout(() => setAdded(false), 1000)
  }

  return (
    <div className="product-card">
      {product.image_url ? (
        <img
          className="card-image"
          src={product.image_url}
          alt={product.name}
          loading="lazy"
          onClick={handleClick}
        />
      ) : (
        <div className="no-image" onClick={() => onEdit(product)}>—</div>
      )}
      <div className="card-body">
        <h3>{product.name}</h3>
        <div className="product-code">{product.code}</div>
        <div className="price">${formatPrice(product.price)}</div>
        <div className="product-stock">Stock: {product.stock ?? 1}{product.ubicacion ? ` | ${product.ubicacion}` : ''}</div>
        {product.colors?.length > 0 && (
          <div className="color-indicators">
            {product.colors.map((c) => (
              <span
                key={c.id}
                className="color-dot"
                style={{ backgroundColor: c.hex }}
                title={c.name}
              />
            ))}
          </div>
        )}
      </div>
      <div className="card-actions">
        {(product.stock ?? 1) > 0 && onAddToCart && (
          <button
            className={`card-action-btn card-action-cart ${added ? 'added' : ''}`}
            onClick={handleAddToCart}
            title="Agregar al carrito"
          >
            {added ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="9" cy="21" r="1" />
                <circle cx="20" cy="21" r="1" />
                <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
              </svg>
            )}
          </button>
        )}
        {canEdit && (
          <>
            <button className="card-action-btn card-action-edit" onClick={() => onEdit(product)} title="Editar">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
                <path d="m15 5 4 4" />
              </svg>
            </button>
            <button className="card-action-btn card-action-delete" onClick={() => onDelete(product.id)} title="Eliminar">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 6h18" />
                <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                <line x1="10" y1="11" x2="10" y2="17" />
                <line x1="14" y1="11" x2="14" y2="17" />
              </svg>
            </button>
          </>
        )}
      </div>
    </div>
  )
});

export default ProductCard;
