import { memo, useRef, useState } from 'react';
import { formatPrice } from '../utils.js';
import { CartIcon, CheckIcon, EditIcon, TrashIcon } from './icons.jsx';

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
              <CheckIcon />
            ) : (
              <CartIcon size={14} strokeWidth={2.5} />
            )}
          </button>
        )}
        {canEdit && (
          <>
            <button className="card-action-btn card-action-edit" onClick={() => onEdit(product)} title="Editar">
              <EditIcon />
            </button>
            <button className="card-action-btn card-action-delete" onClick={() => onDelete(product.id)} title="Eliminar">
              <TrashIcon />
            </button>
          </>
        )}
      </div>
    </div>
  )
});

export default ProductCard;
