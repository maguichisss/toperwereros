import { useState, useRef, useEffect } from 'react'
import { contrastColor } from './ColorSwatches.jsx'

export default function ProductFilters({
  categories = [],
  colors = [],
  filters = {},
  onChange,
  multi = false,
  bare = false,
  sections = ['category', 'color', 'price', 'stock', 'location'],
}) {
  const [ubicacion, setUbicacion] = useState(filters['ubicacion__contains'] ?? '')
  const timer = useRef(null)

  useEffect(() => () => clearTimeout(timer.current), [])

  useEffect(() => {
    if (!filters['ubicacion__contains']) setUbicacion('')
  }, [filters['ubicacion__contains']])

  const val = (key) => filters[key] ?? (multi ? [] : '')

  function update(next) {
    const clean = Object.fromEntries(
      Object.entries(next).filter(([, v]) =>
        v !== undefined &&
        v !== null &&
        v !== '' &&
        !(Array.isArray(v) && v.length === 0)
      )
    )
    onChange(clean)
  }

  function toggleIn(key, name) {
    const current = Array.isArray(filters[key]) ? filters[key] : []
    update({
      ...filters,
      [key]: current.includes(name) ? current.filter(n => n !== name) : [...current, name],
    })
  }

  function toggleCategory(id) {
    const selectedNames = (val('category__in') || [])
      .map(name => categories.find(c => c.name === name)?.id)
      .filter(Boolean)
    const ids = selectedNames.includes(id)
      ? selectedNames.filter(n => n !== id)
      : [...selectedNames, id]
    update({
      ...filters,
      'category__in': ids.map(nid => categories.find(c => c.id === nid)?.name).filter(Boolean),
    })
  }

  function handleUbicacion(v) {
    setUbicacion(v)
    clearTimeout(timer.current)
    timer.current = setTimeout(
      () => update({ ...filters, 'ubicacion__contains': v.trim() || undefined }),
      300
    )
  }

  const categoryChips = (
    <div className="category-chips">
      {categories.map(c => {
        const isSelected = (val('category__in') || []).includes(c.name)
        return (
          <button
            key={c.id}
            type="button"
            className={`chip ${isSelected ? 'chip--active' : ''}`}
            aria-pressed={isSelected}
            onClick={() => toggleCategory(c.id)}
          >
            {c.name}
          </button>
        )
      })}
    </div>
  )

  const colorSwatches = (key, items) => (
    <div className="color-swatches">
      {items.map(c => {
        const isSelected = val(key).includes(c.name)
        return (
          <button
            key={c.id}
            type="button"
            className={`swatch ${isSelected ? 'is-selected' : ''}`}
            style={{ backgroundColor: c.hex, color: contrastColor(c.hex) }}
            title={c.name}
            data-name={c.name}
            aria-label={c.name}
            aria-pressed={isSelected}
            onClick={() => toggleIn(key, c.name)}
          />
        )
      })}
    </div>
  )

  const inner = (
    <>
      {sections.includes('category') && (
        <label className="filter-item"><span>{multi ? 'Categorías' : 'Categoría'}</span>
          {multi ? categoryChips : (
            <select className="input-sm" value={val('category__eq')} onChange={e => update({ ...filters, 'category__eq': e.target.value || undefined })}>
              <option value="">Todas</option>
              {categories.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
            </select>
          )}
        </label>
      )}
      {sections.includes('color') && (
        <label className="filter-item"><span>{multi ? 'Colores' : 'Color'}</span>
          {multi ? colorSwatches('color__in', colors) : (
            <select className="input-sm" value={val('color__eq')} onChange={e => update({ ...filters, 'color__eq': e.target.value || undefined })}>
              <option value="">Todos</option>
              {colors.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
            </select>
          )}
        </label>
      )}
      {sections.includes('price') && (
        <>
          <label className="filter-item"><span>Precio mín.</span>
            <input type="number" min="0" step="0.01" className="input-sm" value={val('price__gte')}
              onChange={e => update({ ...filters, 'price__gte': e.target.value || undefined })} />
          </label>
          <label className="filter-item"><span>Precio máx.</span>
            <input type="number" min="0" step="0.01" className="input-sm" value={val('price__lte')}
              onChange={e => update({ ...filters, 'price__lte': e.target.value || undefined })} />
          </label>
        </>
      )}
      {sections.includes('stock') && (
        <label className="filter-item"><span>Stock mín.</span>
          <input type="number" min="0" step="1" className="input-sm" value={val('stock__gte')}
            onChange={e => update({ ...filters, 'stock__gte': e.target.value || undefined })} />
        </label>
      )}
      {sections.includes('location') && (
        <label className="filter-item"><span>Ubicación</span>
          <input type="search" className="input-sm" placeholder="Bodega…" value={ubicacion}
            onChange={e => handleUbicacion(e.target.value)} autoComplete="off" />
        </label>
      )}
    </>
  )

  return bare ? inner : (
    <div className="filter-bar filter-bar--compact" role="group" aria-label="Filtros de producto">
      {inner}
    </div>
  )
}