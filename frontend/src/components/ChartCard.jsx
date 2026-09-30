import { useEffect, useRef } from 'react';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

const CHART_TYPES = {
  bar: 'bar',
  horizontalBar: 'bar',
  doughnut: 'doughnut',
};

const CATEGORY_COLOR_VARS = [
  '--primary',
  '--success',
  '--warning',
  '--danger',
  '--primary-dark',
  '--success-hover',
  '--text-secondary',
  '--text-muted',
  '--text-light',
  '--border-dark',
];

const COLOR_FALLBACKS = {
  '--primary': '#1a73e8',
  '--success': '#43a047',
  '--warning': '#ff9800',
  '--danger': '#e53935',
  '--primary-dark': '#1976d2',
  '--success-hover': '#388e3c',
  '--text-secondary': '#555',
  '--text-muted': '#888',
  '--text-light': '#aaa',
  '--border-dark': '#ddd',
};

function cssVar(name) {
  if (typeof window === 'undefined') return COLOR_FALLBACKS[name] || '#1a73e8';
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || COLOR_FALLBACKS[name] || '#1a73e8';
}

export function chartPalette() {
  return {
    primary: cssVar('--primary'),
    success: cssVar('--success'),
    warning: cssVar('--warning'),
    danger: cssVar('--danger'),
    text: cssVar('--text-secondary'),
    muted: cssVar('--text-muted'),
    grid: cssVar('--border-light'),
    card: cssVar('--bg-card'),
  };
}

export function categoryColors(count) {
  return Array.from(
    { length: Math.max(0, count) },
    (_, i) => cssVar(CATEGORY_COLOR_VARS[i % CATEGORY_COLOR_VARS.length])
  );
}

function defaultOptions(type, palette) {
  const common = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: palette.card,
        titleColor: palette.text,
        bodyColor: palette.text,
        borderColor: palette.grid,
        borderWidth: 1,
        padding: 10,
        cornerRadius: 4,
      },
    },
  };

  if (type === 'doughnut') {
    return {
      ...common,
      cutout: '62%',
      plugins: {
        ...common.plugins,
        legend: {
          display: true,
          position: 'bottom',
          labels: {
            color: palette.text,
            boxWidth: 8,
            padding: 10,
            font: { size: 11 },
            usePointStyle: true,
            pointStyle: 'circle',
          },
        },
      },
    };
  }

  const vertical = type !== 'horizontalBar';
  return {
    ...common,
    indexAxis: vertical ? 'x' : 'y',
    scales: {
      x: {
        grid: { display: !vertical, color: palette.grid, drawBorder: false },
        border: { color: palette.grid },
        ticks: { color: palette.text, maxTicksLimit: 8, maxRotation: 0, autoSkip: true },
      },
      y: {
        beginAtZero: true,
        grid: { display: vertical, color: palette.grid, drawBorder: false },
        border: { color: palette.grid },
        ticks: {
          color: palette.text,
          maxTicksLimit: 6,
          callback: value => (String(value).length > 26 ? `${String(value).slice(0, 25)}…` : value),
        },
      },
    },
  };
}

function mergeOptions(base, extra) {
  if (!extra) return base;
  return {
    ...base,
    ...extra,
    plugins: {
      ...base.plugins,
      ...(extra.plugins || {}),
      legend: { ...base.plugins.legend, ...(extra.plugins?.legend || {}) },
      tooltip: { ...base.plugins.tooltip, ...(extra.plugins?.tooltip || {}) },
    },
    scales: extra.scales || base.scales,
  };
}

export default function ChartCard({
  title,
  value,
  type = 'bar',
  data,
  options,
  ariaLabel,
  empty = false,
  emptyText = 'Sin datos para el periodo seleccionado',
  note,
  actions,
  className,
  height = 260,
}) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);
  const chartType = CHART_TYPES[type] || 'bar';

  useEffect(() => {
    if (empty) return undefined;
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const chart = new Chart(canvas, {
      type: chartType,
      data: data || { labels: [], datasets: [] },
      options: mergeOptions(defaultOptions(type, chartPalette()), options),
    });
    chartRef.current = chart;
    return () => {
      chart.destroy();
      chartRef.current = null;
    };
  }, [type, chartType, empty]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.data = data || { labels: [], datasets: [] };
    chart.options = mergeOptions(defaultOptions(type, chartPalette()), options);
    chart.update();
  }, [data, options, type]);

  return (
    <section className={`dash-card ${className || ''}`}>
      <header className="dash-card__header">
        <div>
          <h3 className="dash-card__title">{title}</h3>
          {note && <p className="dash-card__note">{note}</p>}
        </div>
        {actions}
      </header>
      {value && <p className="dash-card__value">{value}</p>}
      {empty ? (
        <div className="empty-state dash-card__empty">
          <p>{emptyText}</p>
        </div>
      ) : (
        <div className="dash-card__canvas" style={{ height: `${height}px` }}>
          <canvas ref={canvasRef} role="img" aria-label={ariaLabel || title} />
        </div>
      )}
    </section>
  );
}
