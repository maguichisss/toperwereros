import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { categoriesApi, dashboardApi, apiErrorMessage } from '../api/client.js';
import { formatPrice } from '../utils.js';
import ChartCard, { categoryColors, chartPalette } from './ChartCard.jsx';

const DEFAULT_PRESET = '30d';
const DEFAULT_TOP = 5;
const MAX_TOP = 20;
const MAX_CATEGORY_SLICES = 6;
const GLOBAL_NOTE = 'Tienda completa';

const PRESETS = [
  { key: 'hoy', label: 'Hoy', dias: 1 },
  { key: '7d', label: '7 días', dias: 7 },
  { key: '30d', label: '30 días', dias: 30 },
  { key: 'mes', label: 'Este mes', dias: null },
];

const STORAGE_KEYS = {
  preset: 'dash.preset',
  top: 'dash.top',
  category: 'dash.category',
};

function readStorage(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch { /* storage unavailable */ }
}

function toISODate(date) {
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

function rangeForPreset(preset) {
  const today = new Date();
  const endDate = toISODate(today);
  if (preset === 'hoy') return { startDate: endDate, endDate };
  if (preset === 'mes') {
    return { startDate: toISODate(new Date(today.getFullYear(), today.getMonth(), 1)), endDate };
  }
  const dias = PRESETS.find(p => p.key === preset)?.dias ?? 30;
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate() - (dias - 1));
  return { startDate: toISODate(start), endDate };
}

function daysBetween(startDate, endDate) {
  if (!startDate || !endDate) return 30;
  const diff = Math.round(
    (new Date(`${endDate}T00:00:00`) - new Date(`${startDate}T00:00:00`)) / 86400000
  ) + 1;
  return diff > 0 ? diff : 1;
}

function formatDayLabel(iso) {
  const date = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString('es-MX', { day: '2-digit', month: 'short' });
}

function formatLongDate(iso) {
  const date = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString('es-MX', { day: 'numeric', month: 'long', year: 'numeric' });
}

function readStoredControls() {
  const storedPreset = readStorage(STORAGE_KEYS.preset);
  const preset = PRESETS.some(p => p.key === storedPreset) ? storedPreset : DEFAULT_PRESET;
  const storedTop = Number(readStorage(STORAGE_KEYS.top));
  const storedCategory = readStorage(STORAGE_KEYS.category);
  return {
    preset,
    ...rangeForPreset(preset),
    top: Number.isInteger(storedTop) && storedTop >= 1 && storedTop <= MAX_TOP ? storedTop : DEFAULT_TOP,
    category: storedCategory || '',
  };
}

function buildCategorySlices(rows) {
  const sorted = [...rows].sort((a, b) => Number(b.revenue) - Number(a.revenue));
  if (sorted.length <= MAX_CATEGORY_SLICES) return sorted;
  const tail = sorted.slice(MAX_CATEGORY_SLICES);
  const totals = tail.reduce(
    (acc, row) => ({
      revenue: acc.revenue + Number(row.revenue),
      units: acc.units + Number(row.units),
    }),
    { revenue: 0, units: 0 }
  );
  return [
    ...sorted.slice(0, MAX_CATEGORY_SLICES),
    { category: 'Otros', revenue: String(totals.revenue), units: totals.units },
  ];
}

function KpiCard({ title, value, stats, note }) {
  return (
    <section className="dash-kpi">
      <h3 className="dash-kpi__title">
        {title}
        {note && <span className="dash-badge">{note}</span>}
      </h3>
      <p className="dash-kpi__value">{value}</p>
      <dl className="dash-kpi__stats">
        {stats.map(stat => (
          <div key={stat.label} className="dash-kpi__stat">
            <dt>{stat.label}</dt>
            <dd>{stat.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export default function Dashboard() {
  const stored = useMemo(readStoredControls, []);
  const [preset, setPreset] = useState(stored.preset);
  const [startDate, setStartDate] = useState(stored.startDate);
  const [endDate, setEndDate] = useState(stored.endDate);
  const [top, setTop] = useState(stored.top);
  const [category, setCategory] = useState(stored.category);
  const [rankBy, setRankBy] = useState('units');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [categories, setCategories] = useState([]);

  const dias = daysBetween(startDate, endDate);
  const palette = useMemo(() => chartPalette(), []);
  const requestId = useRef(0);

  const load = useCallback(async () => {
    const id = ++requestId.current;
    setLoading(true);
    try {
      const res = await dashboardApi.summary({
        startDate,
        endDate,
        dias,
        top,
        category: category || undefined,
      });
      if (id !== requestId.current) return;
      setData(res);
      setError(null);
    } catch (e) {
      if (id !== requestId.current) return;
      setData(null);
      setError(apiErrorMessage(e?.detail ?? e?.message, 'No se pudo cargar el panel'));
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [startDate, endDate, dias, top, category]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    let active = true;
    categoriesApi
      .list()
      .then(res => {
        if (!active) return;
        const list = res?.categories || [];
        setCategories(list);
        setCategory(prev => (prev && !list.some(c => c.name === prev) ? '' : prev));
      })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  useEffect(() => { writeStorage(STORAGE_KEYS.preset, preset); }, [preset]);
  useEffect(() => { writeStorage(STORAGE_KEYS.top, String(top)); }, [top]);
  useEffect(() => { writeStorage(STORAGE_KEYS.category, category); }, [category]);

  function handlePresetClick(key) {
    const range = rangeForPreset(key);
    setPreset(key);
    setStartDate(range.startDate);
    setEndDate(range.endDate);
  }

  function handleDateChange(field, value) {
    const next = { startDate, endDate, [field]: value };
    if (!next.startDate || !next.endDate) {
      const range = rangeForPreset(DEFAULT_PRESET);
      setStartDate(range.startDate);
      setEndDate(range.endDate);
      setPreset(DEFAULT_PRESET);
      return;
    }
    if (field === 'startDate') setStartDate(value);
    else setEndDate(value);
    setPreset('custom');
  }

  function handleTopChange(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed === 0) return setTop(DEFAULT_TOP);
    setTop(Math.min(MAX_TOP, Math.max(1, Math.round(parsed))));
  }

  const params = data?.params;
  const periodStart = params?.start_date || startDate;
  const periodEnd = params?.end_date || endDate;
  const periodLabel = `Del ${formatLongDate(periodStart)} al ${formatLongDate(periodEnd)}`;
  const isFiltered = Boolean(category);
  const globalNote = isFiltered ? GLOBAL_NOTE : null;

  const daily = data?.daily || [];
  const dailyData = useMemo(() => ({
    labels: daily.map(d => formatDayLabel(d.date)),
    datasets: [
      {
        label: 'Ingresos',
        data: daily.map(d => Number(d.revenue)),
        backgroundColor: palette.primary,
        borderRadius: 4,
        maxBarThickness: 26,
      },
    ],
  }), [daily, palette.primary]);

  const dailyOptions = useMemo(() => ({
    plugins: {
      tooltip: {
        callbacks: {
          title: items => daily[items[0]?.dataIndex]?.date || '',
          label: item => ` $${formatPrice(item.parsed.y)}`,
        },
      },
    },
  }), [daily]);

  const topProducts = rankBy === 'revenue' ? data?.top_products_by_revenue || [] : data?.top_products || [];
  const topData = useMemo(() => ({
    labels: topProducts.map(p => p.name),
    datasets: [
      {
        label: rankBy === 'revenue' ? 'Ingresos' : 'Unidades',
        data: topProducts.map(p => (rankBy === 'revenue' ? Number(p.revenue) : Number(p.units))),
        backgroundColor: palette.primary,
        borderRadius: 4,
        maxBarThickness: 22,
      },
    ],
  }), [topProducts, rankBy, palette.primary]);

  const topOptions = useMemo(() => ({
    plugins: {
      tooltip: {
        callbacks: {
          title: items => topProducts[items[0]?.dataIndex]?.code || '',
          label: item => (rankBy === 'revenue'
            ? ` $${formatPrice(item.parsed.x)}`
            : ` ${item.parsed.x} unidades`),
        },
      },
    },
  }), [topProducts, rankBy]);

  const slices = useMemo(() => buildCategorySlices(data?.category_breakdown || []), [data]);
  const sliceColors = useMemo(() => categoryColors(slices.length), [slices]);
  const sliceTotal = useMemo(
    () => slices.reduce((acc, row) => acc + Number(row.revenue), 0),
    [slices]
  );

  const categoryData = useMemo(() => ({
    labels: slices.map(row => row.category),
    datasets: [
      {
        label: 'Ingresos',
        data: slices.map(row => Number(row.revenue)),
        backgroundColor: sliceColors,
        borderColor: palette.card,
        borderWidth: 2,
      },
    ],
  }), [slices, sliceColors, palette.card]);

  const categoryOptions = useMemo(() => ({
    plugins: {
      tooltip: {
        callbacks: {
          label: item => ` $${formatPrice(item.parsed)}`,
        },
      },
    },
  }), []);

  const rankToggle = (
    <div className="dash-toggle" role="group" aria-label="Ordenar el top de productos por">
      <button
        type="button"
        className={`btn btn--small ${rankBy === 'units' ? 'btn--active' : 'btn--secondary'}`}
        aria-pressed={rankBy === 'units'}
        onClick={() => setRankBy('units')}
      >
        Unidades
      </button>
      <button
        type="button"
        className={`btn btn--small ${rankBy === 'revenue' ? 'btn--active' : 'btn--secondary'}`}
        aria-pressed={rankBy === 'revenue'}
        onClick={() => setRankBy('revenue')}
      >
        Ingresos
      </button>
    </div>
  );

  return (
    <div className="dash" aria-busy={loading}>
      <div className="dash-controls">
        <div className="dash-presets" role="group" aria-label="Periodo predefinido">
          {PRESETS.map(p => (
            <button
              key={p.key}
              type="button"
              className={`chip ${preset === p.key ? 'chip--active' : ''}`}
              aria-pressed={preset === p.key}
              onClick={() => handlePresetClick(p.key)}
            >
              {p.label}
            </button>
          ))}
          {preset === 'custom' && (
            <button type="button" className="chip chip--active" aria-pressed="true" disabled>
              Personalizado
            </button>
          )}
        </div>
        <label className="filter-item">
          <span>Desde</span>
          <input
            type="date"
            className="input-sm"
            value={startDate}
            max={endDate || undefined}
            onChange={e => handleDateChange('startDate', e.target.value)}
          />
        </label>
        <label className="filter-item">
          <span>Hasta</span>
          <input
            type="date"
            className="input-sm"
            value={endDate}
            min={startDate || undefined}
            onChange={e => handleDateChange('endDate', e.target.value)}
          />
        </label>
        <label className="filter-item">
          <span>Top</span>
          <input
            type="number"
            className="input-sm dash-input-top"
            min="1"
            max={MAX_TOP}
            value={top}
            onChange={e => handleTopChange(e.target.value)}
          />
        </label>
        <label className="filter-item">
          <span>Categoría</span>
          <select
            className="input-sm"
            value={category}
            onChange={e => setCategory(e.target.value)}
          >
            <option value="">Todas</option>
            {categories.map(c => (
              <option key={c.id} value={c.name}>{c.name}</option>
            ))}
          </select>
        </label>
        <p className="dash-period">{periodLabel}</p>
      </div>

      {error && <p className="error-text">{error}</p>}

      {loading && !data && <p className="page-loading">Cargando…</p>}

      {!loading && !data && !error && (
        <div className="empty-state">
          <p>No hay datos del panel disponibles.</p>
        </div>
      )}

      {data && (
        <>
          <div className="dash-kpi-grid">
            <KpiCard
              title="Ventas"
              value={`$${formatPrice(data.sales.revenue)}`}
              stats={[
                { label: 'Ventas', value: data.sales.sales_count },
                { label: 'Ticket promedio', value: `$${formatPrice(data.sales.avg_ticket)}` },
                { label: 'Unidades vendidas', value: data.sales.units_sold },
              ]}
            />
            <KpiCard
              title="Apartados"
              note={globalNote}
              value={`${data.layaways.active_count} activo${data.layaways.active_count === 1 ? '' : 's'}`}
              stats={[
                { label: 'Saldo por cobrar', value: `$${formatPrice(data.layaways.outstanding_balance)}` },
                { label: 'Depósitos del periodo', value: `$${formatPrice(data.layaways.deposits)}` },
                { label: 'Nuevos apartados', value: data.layaways.new_count },
              ]}
            />
            <KpiCard
              title="Clientes"
              note={globalNote}
              value={`${data.customers.total} cliente${data.customers.total === 1 ? '' : 's'}`}
              stats={[
                { label: 'Nuevos en el periodo', value: data.customers.new_count },
                { label: 'Con apartado activo', value: data.customers.with_active_layaway },
              ]}
            />
            <KpiCard
              title="Inventario"
              value={`${data.inventory.sku_count} SKU${data.inventory.sku_count === 1 ? '' : 's'}`}
              stats={[
                { label: 'Unidades', value: data.inventory.units },
                { label: 'Agotados', value: data.inventory.out_of_stock },
                { label: 'Stock bajo', value: data.inventory.low_stock },
                { label: 'Valor a precio de venta', value: `$${formatPrice(data.inventory.catalog_value)}` },
              ]}
            />
          </div>

          <div className="dash-charts">
            <ChartCard
              title="Ingresos por día"
              value={`$${formatPrice(data.sales.revenue)} en ${daily.length} día${daily.length === 1 ? '' : 's'}`}
              type="bar"
              data={dailyData}
              options={dailyOptions}
              empty={daily.length === 0}
              emptyText="Sin ventas en el periodo seleccionado"
              ariaLabel={`Ingresos por día del ${formatLongDate(periodStart)} al ${formatLongDate(periodEnd)}`}
              className="dash-charts__full"
            />

            <ChartCard
              title="Top productos"
              value={topProducts.length > 0 ? `Top ${topProducts.length} por ${rankBy === 'revenue' ? 'ingresos' : 'unidades'}` : null}
              type="horizontalBar"
              data={topData}
              options={topOptions}
              empty={topProducts.length === 0}
              emptyText="Sin productos vendidos en el periodo"
              ariaLabel={`Top ${topProducts.length} productos por ${rankBy === 'revenue' ? 'ingresos' : 'unidades'}`}
              actions={rankToggle}
            />
            {topProducts.length > 0 && (
              <ol className="dash-ranking">
                <li className="dash-ranking__row dash-ranking__row--head">
                  <span className="dash-ranking__name">Producto</span>
                  <span>{rankBy === 'revenue' ? 'Ingresos' : 'Unidades'}</span>
                </li>
                {topProducts.map((p, i) => (
                  <li key={p.product_id} className="dash-ranking__row">
                    <span className="dash-ranking__pos">{i + 1}</span>
                    <span className="dash-ranking__name">
                      {p.name}
                      <span className="dash-ranking__code">{p.code}</span>
                    </span>
                    <span className="dash-ranking__value">
                      {rankBy === 'revenue' ? `$${formatPrice(p.revenue)}` : p.units}
                    </span>
                  </li>
                ))}
              </ol>
            )}

            <ChartCard
              title="Reparto por categoría"
              note={globalNote}
              value={sliceTotal > 0 ? `$${formatPrice(sliceTotal)} en ${slices.length} categoría${slices.length === 1 ? '' : 's'}` : null}
              type="doughnut"
              data={categoryData}
              options={categoryOptions}
              empty={slices.length === 0}
              emptyText="Sin ventas por categoría en el periodo"
              ariaLabel="Reparto de ingresos por categoría"
              height={220}
            />
            {slices.length > 0 && (
              <ul className="dash-legend">
                {slices.map((row, i) => (
                  <li key={row.category} className="dash-legend__row">
                    <span className="dash-legend__dot" style={{ backgroundColor: sliceColors[i] }} aria-hidden="true" />
                    <span className="dash-legend__name">{row.category}</span>
                    <span className="dash-legend__value">
                      ${formatPrice(row.revenue)}
                      {sliceTotal > 0 && ` · ${Math.round((Number(row.revenue) / sliceTotal) * 100)}%`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}
