import { useState, useEffect, useRef, useCallback } from 'react';
import { productsApi, categoriesApi, colorsApi } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx';
import ProductFilters from './ProductFilters.jsx';
import ProductCard from './ProductCard.jsx';
import Pagination from './Pagination.jsx';
import Lightbox from './Lightbox.jsx';

const PREVIEW_PAGE_SIZE = 60;

const THEMES = [
  ['classic', 'Clásico'],
  ['nocturno', 'Nocturno'],
  ['kraft', 'Kraft'],
  ['elegante', 'Elegante'],
  ['marino', 'Marino'],
  ['sol', 'Sol'],
  ['cyber', 'Cyber'],
  ['vino', 'Vino'],
  ['rosa', 'Rosa'],
  ['arcoiris', 'Arcoíris'],
  ['nebulosa', 'Nebulosa'],
  ['triangulos', 'Triángulos'],
  ['olas', 'Olas'],
  ['mandala', 'Mándala'],
  ['aurora', 'Aurora'],
  ['confeti', 'Confeti'],
  ['galaxia', 'Galaxia'],
  ['marco', 'Marco'],
  ['flores', 'Flores'],
];

const DATE_PRESETS = [
  { key: 'today', label: 'Hoy' },
  { key: 'week', label: 'Esta semana' },
  { key: 'month', label: 'Este mes' },
  { key: 'last30', label: 'Últimos 30 días' },
  { key: 'all', label: 'Todo' },
  { key: 'custom', label: 'Personalizado' },
];

function presetDateRange(key) {
  const today = new Date();
  const fmt = (d) => d.toISOString().slice(0, 10);
  switch (key) {
    case 'today':
      return { 'created_at__gte': fmt(today), 'created_at__lte': fmt(today) };
    case 'week': {
      const d = new Date(today);
      d.setDate(d.getDate() - 6);
      return { 'created_at__gte': fmt(d), 'created_at__lte': fmt(today) };
    }
    case 'month':
      return { 'created_at__gte': fmt(new Date(today.getFullYear(), today.getMonth(), 1)), 'created_at__lte': fmt(today) };
    case 'last30': {
      const d = new Date(today);
      d.setDate(d.getDate() - 29);
      return { 'created_at__gte': fmt(d), 'created_at__lte': fmt(today) };
    }
    default:
      return {};
  }
}

export default function CatalogExportPage() {
  const { can } = useAuth();
  const [filters, setFilters] = useState({});
  const [categories, setCategories] = useState([]);
  const [colors, setColors] = useState([]);
  const [theme, setTheme] = useState('classic');
  const [datePreset, setDatePreset] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [date, setDate] = useState({});
  const [products, setProducts] = useState([]);
  const [total, setTotal] = useState(null);
  const [page, setPage] = useState(1);
  const [previewImage, setPreviewImage] = useState(null);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [searchName, setSearchName] = useState('');
  const [searchCode, setSearchCode] = useState('');
  const [pendingSearch, setPendingSearch] = useState({ name: '', code: '' });
  const loadTimer = useRef(null);
  const searchTimer = useRef(null);

  useEffect(() => () => clearTimeout(searchTimer.current), []);

  useEffect(() => {
    Promise.all([
      categoriesApi.list(),
      can('color.view') ? colorsApi.list() : Promise.resolve([]),
    ])
      .then(([c, col]) => { setCategories(c); setColors(col); })
      .catch(() => {});
  }, [can]);

  const queryFilters = {
    ...filters,
    ...date,
    ...(pendingSearch.name.trim() ? { name__contains: pendingSearch.name.trim() } : {}),
    ...(pendingSearch.code.trim() ? { code__contains: pendingSearch.code.trim() } : {}),
  };

  const hasActiveFilters = datePreset !== 'all' || Object.keys(filters).length > 0 ||
    pendingSearch.name.trim() !== '' || pendingSearch.code.trim() !== '';

  useEffect(() => {
    clearTimeout(loadTimer.current);
    loadTimer.current = setTimeout(async () => {
      try {
        const res = await productsApi.list({ page, perPage: PREVIEW_PAGE_SIZE, filters: queryFilters });
        setProducts(res.products);
        setTotal(res.total);
      } catch {
        setProducts([]);
        setTotal(null);
      }
    }, 300);
    return () => clearTimeout(loadTimer.current);
  }, [filters, date, page, pendingSearch]);

  const onDatePreset = useCallback((key) => {
    setDatePreset(key);
    setPage(1);
    if (key === 'custom') {
      setDateFrom('');
      setDateTo('');
      setDate({});
    } else {
      setDate(presetDateRange(key));
    }
  }, []);

  const onCustomDate = useCallback((from, to) => {
    setDateFrom(from);
    setDateTo(to);
    setPage(1);
    setDate({
      ...(from ? { 'created_at__gte': from } : {}),
      ...(to ? { 'created_at__lte': to } : {}),
    });
  }, []);

  const onFiltersChange = useCallback((next) => {
    setPage(1);
    setFilters(next);
  }, []);

  function handleSearchChange(kind, value) {
    if (kind === 'name') setSearchName(value);
    else setSearchCode(value);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      setPendingSearch((prev) => ({ ...prev, [kind]: value.trim() }));
      setPage(1);
    }, 300);
  }

  const handleClear = useCallback(() => {
    setSearchName('');
    setSearchCode('');
    setPendingSearch({ name: '', code: '' });
    setPage(1);
    setFilters({});
    setDatePreset('all');
    setDateFrom('');
    setDateTo('');
    setDate({});
  }, []);

  async function download(format) {
    if (busy) return;
    setBusy(true);
    setMsg('Generando…');
    try {
      const params = new URLSearchParams({ ...queryFilters, format, theme })
      const token = localStorage.getItem('store_token');
      const r = await fetch(`/api/catalog/pdf?${params.toString()}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!r.ok) throw new Error('Error al generar el catálogo');
      const blob = await r.blob();
      const disposition = r.headers.get('Content-Disposition');
      let filename = format === 'csv' ? 'catalogo.csv' : 'catalogo.pdf';
      if (disposition) {
        const match = disposition.match(/filename=(.+)/);
        if (match) filename = match[1];
      }
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
      setMsg(`Catálogo ${format.toUpperCase()} descargado (${total ?? '?'} producto${total === 1 ? '' : 's'})`);
    } catch (e) {
      setMsg(e.message || 'Error al generar el catálogo');
    } finally {
      setBusy(false);
    }
  }

  const totalPages = total != null ? Math.ceil(total / PREVIEW_PAGE_SIZE) : 0;

  const openPreview = useCallback((p) => setPreviewImage(p.image_url), []);

  return (
    <div>
      <div className="filter-bar filter-bar--catalog">
        <div className="filter-bar__search filter-bar__search--multi">
          <input type="search" enterKeyHint="search" className="search-input" placeholder="Buscar por nombre…" aria-label="Buscar por nombre" value={searchName} onChange={e => handleSearchChange('name', e.target.value)} autoComplete="off" autoCorrect="off" spellCheck="false" />
          <input type="search" enterKeyHint="search" className="search-input" placeholder="Buscar por código…" aria-label="Buscar por código" value={searchCode} onChange={e => handleSearchChange('code', e.target.value)} autoComplete="off" autoCorrect="off" spellCheck="false" />
        </div>

        {can('product.view') && (
          <ProductFilters categories={categories} colors={colors} filters={filters} onChange={onFiltersChange} bare sections={['price', 'stock', 'location']} />
        )}
      </div>

      {can('product.view') && (
<div className="filter-bar filter-bar--catalog filter-bar--grow">
          <ProductFilters categories={categories} colors={colors} filters={filters} onChange={onFiltersChange} multi bare sections={['category', 'color']} />
        </div>
      )}

      <div className="filter-bar filter-bar--catalog">
        {DATE_PRESETS.map(p => (
          <button key={p.key} type="button"
            className={`btn btn--small btn--${datePreset === p.key ? 'primary' : 'secondary'}`}
            onClick={() => onDatePreset(p.key)}>
            {p.label}
          </button>
        ))}
        {datePreset === 'custom' && (
          <>
            <input type="date" inputMode="numeric" className="input-sm" value={dateFrom}
              onChange={e => onCustomDate(e.target.value, dateTo)} autoComplete="off" />
            <span className="filter-bar__sep">a</span>
            <input type="date" className="input-sm" value={dateTo}
              onChange={e => onCustomDate(dateFrom, e.target.value)} autoComplete="off" />
          </>
        )}

        <div className="filter-actions">
          <select value={theme} onChange={e => setTheme(e.target.value)} className="input-sm" aria-label="Tema del catálogo" autoComplete="off">
            {THEMES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
          {hasActiveFilters && (
            <button type="button" className="btn btn--secondary" onClick={handleClear}>Limpiar</button>
          )}
          <button type="button" className="btn btn--secondary" disabled={busy} onClick={() => download('pdf')}>PDF</button>
          <button type="button" className="btn btn--secondary" disabled={busy} onClick={() => download('csv')}>CSV</button>
        </div>
      </div>

      {msg ? (
        <p className="filter-bar__count">{msg}</p>
      ) : total != null ? (
        <p className="filter-bar__count">
          {total} producto{total === 1 ? '' : 's'} a exportar
          {totalPages > 1 && ` — Página ${page} de ${totalPages}`}
        </p>
      ) : null}

      {products.length === 0 && total === 0 && (
        <div className="empty-state">
          <p>No hay productos con los filtros actuales.</p>
        </div>
      )}

      <div className="product-grid">
        {products.map((p) => (
          <ProductCard key={p.id} product={p} onEdit={openPreview} onShowImage={openPreview} showActions={false} />
        ))}
      </div>

      <Pagination page={page} totalPages={totalPages} onChange={setPage} />

      {previewImage && (
        <Lightbox imageUrl={previewImage} name="Producto" onClose={() => setPreviewImage(null)} />
      )}
    </div>
  );
}