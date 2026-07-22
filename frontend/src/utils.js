export function formatPrice(amount) {
  if (amount == null || isNaN(amount)) return '0.00'
  return Number(amount).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
