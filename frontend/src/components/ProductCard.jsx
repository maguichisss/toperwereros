import { memo } from 'react';

const ProductCard = memo(({ product, onEdit, onDelete }) => (
  <div className="product-card">
    {product.image_url ? (
      <img
        className="card-image"
        src={`${product.image_url}?t=${product.updated_at}`}
        alt={product.name}
        onClick={() => onEdit(product)}
        loading="lazy"
      />
    ) : (
      <div className="no-image" onClick={() => onEdit(product)}>—</div>
    )}
    <div className="card-body">
      <h3 onClick={() => onEdit(product)}>{product.name}</h3>
      <div className="product-code">{product.code}</div>
      <div className="price">${Number(product.price).toFixed(2)}</div>
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
      <button className="btn btn-primary" onClick={() => onEdit(product)}>Editar</button>
      <button className="btn btn-danger" onClick={() => onDelete(product.id)}>Eliminar</button>
    </div>
  </div>
));

export default ProductCard;
