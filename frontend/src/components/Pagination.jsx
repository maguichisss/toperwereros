export default function Pagination({ page, totalPages, onChange }) {
  if (totalPages <= 1) return null;

  const pages = [];
  const maxVisible = 5;
  let start = Math.max(1, page - Math.floor(maxVisible / 2));
  let end = Math.min(totalPages, start + maxVisible - 1);
  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1);
  }
  for (let i = start; i <= end; i++) pages.push(i);

  return (
    <div className="pagination">
      <button type="button" className="btn btn--pagination" disabled={page <= 1} onClick={() => onChange(Math.max(1, page - 1))} aria-label="Página anterior">‹</button>
      {pages.map(n => (
        <button key={n} type="button" className={`btn btn--pagination${n === page ? ' is-active' : ''}`} onClick={() => onChange(n)} aria-label={`Página ${n}`} aria-current={n === page ? 'page' : undefined}>{n}</button>
      ))}
      <button type="button" className="btn btn--pagination" disabled={page >= totalPages} onClick={() => onChange(Math.min(totalPages, page + 1))} aria-label="Página siguiente">›</button>
    </div>
  );
}