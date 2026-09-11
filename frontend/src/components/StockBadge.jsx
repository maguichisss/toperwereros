export default function StockBadge({ stock, quantity }) {
  if (stock === undefined) return null;
  return (
    <>
      <span className="stock-badge">Stock: {stock}</span>
      {quantity >= stock && <span className="stock-badge--max">Stock máximo</span>}
      {quantity < stock && quantity >= stock * 0.8 && <span className="stock-badge--low">Poco stock</span>}
    </>
  );
}