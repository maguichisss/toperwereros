export default function StockBadge({ stock, quantity }) {
  if (stock === undefined) return null;
  return (
    <>
      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Stock: {stock}</span>
      {quantity >= stock && <span style={{ color: 'var(--danger)', fontSize: '0.75rem', fontWeight: 600 }}>Stock máximo</span>}
      {quantity < stock && quantity >= stock * 0.8 && <span style={{ color: 'var(--warning)', fontSize: '0.75rem', fontWeight: 600 }}>Poco stock</span>}
    </>
  );
}