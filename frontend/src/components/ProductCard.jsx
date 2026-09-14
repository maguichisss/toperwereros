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
        <button
          type="button"
          className="product-card__image-btn"
          onClick={handleClick}
          aria-label={`Ver ${product.name}`}
        >
          <img
            className="product-card__image"
            src={product.image_url}
            alt={product.name}
            loading="lazy"
            decoding="async"
          />
        </button>
      ) : (
        <button
          type="button"
          className="product-card__no-image"
          onClick={() => onEdit(product)}
          aria-label={`Editar ${product.name}`}
        >
          —
        </button>
      )}
      <div className="product-card__body">
        <h3>{product.name}</h3>
        <div className="product-card__code">{product.code}</div>
        <div className="product-card__price">${formatPrice(product.price)}</div>
        <div className="product-card__stock">Stock: {product.stock ?? 1}{product.ubicacion ? ` | ${product.ubicacion}` : ''}</div>
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
      <div className="product-card__actions">
        {(product.stock ?? 1) > 0 && onAddToCart && (
          <button
            type="button"
            className={`product-card__action-btn product-card__action-btn--cart ${added ? 'is-added' : ''}`}
            onClick={handleAddToCart}
            title="Agregar al carrito"
            aria-label={`Agregar ${product.name} al carrito`}
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
            <button type="button" className="product-card__action-btn product-card__action-btn--edit" onClick={() => onEdit(product)} title="Editar" aria-label={`Editar ${product.name}`}>
              <EditIcon />
            </button>
            <button type="button" className="product-card__action-btn product-card__action-btn--delete" onClick={() => onDelete(product.id)} title="Eliminar" aria-label={`Eliminar ${product.name}`}>
              <TrashIcon />
            </button>
          </>
        )}
      </div>
    </div>
  )
});

export default ProductCard;