# Replace product table with responsive card grid

## ProductList.jsx
Replace `<div className="table-wrap"><table>...</table></div>` (lines 90-139) with:

```jsx
<div className="product-grid">
  {filtered.map((p) => (
    <div key={p.id} className="product-card">
      {p.image_url ? (
        <img className="card-image" src={p.image_url} alt={p.name} onClick={() => handleEdit(p)} />
      ) : (
        <div className="no-image" onClick={() => handleEdit(p)}>—</div>
      )}
      <div className="card-body">
        <h3 onClick={() => handleEdit(p)}>{p.name}</h3>
        <div className="product-code">{p.code}</div>
        <div className="price">${Number(p.price).toFixed(2)}</div>
        <div className="product-stock">Stock: {p.stock ?? 1}</div>
        {p.colors?.length > 0 && (
          <div className="color-indicators">
            {p.colors.map((c) => (
              <span key={c.id} className="color-dot" style={{ backgroundColor: c.hex }} title={c.name} />
            ))}
          </div>
        )}
      </div>
      <div className="card-actions">
        <button className="btn btn-primary" onClick={() => handleEdit(p)}>Editar</button>
        <button className="btn btn-danger" onClick={() => handleDelete(p.id)}>Eliminar</button>
      </div>
    </div>
  ))}
</div>
```

## index.css
### Add after `@keyframes toast-in { ... }` (end of file):

```css
.product-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.product-card {
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

@media (max-width: 768px) {
  .product-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
  }
}
```

### Remove these unused rules:
- `.table-wrap` (line 70)
- `.product-table`, `.product-table th`, `.product-table td`, `.product-table tr:last-child td` (lines 74-101)
- `.td-thumb img`, `.no-thumb` (lines 104-124)
- `.td-code`, `.td-name`, `.td-price`, `.td-stock`, `.td-cat`, `.td-colors`, `.td-actions`, `.td-actions .btn` (lines 126-165)
- `.card-body .category-badge` (line 203) — unused remnant
