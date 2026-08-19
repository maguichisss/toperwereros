import { memo, useRef } from 'react';
import { formatPrice } from '../utils.js';

const ProductCard = memo(({ product, onEdit, onDelete, onShowImage, canEdit }) => {
  const clickTimer = useRef(null)

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
        {canEdit && (
          <>
            <button className="btn btn-primary" onClick={() => onEdit(product)}>Editar</button>
            <button className="btn btn-danger" onClick={() => onDelete(product.id)}>Eliminar</button>
          </>
        )}
      </div>
    </div>
  )
});

export default ProductCard;
