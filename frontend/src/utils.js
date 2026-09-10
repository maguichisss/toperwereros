export function formatPrice(amount) {
  if (amount == null || isNaN(amount)) return '0.00'
  return Number(amount).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function decodeJwtPayload(token) {
  try {
    const part = token.split('.')[1]
    const normalized = part.replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(normalized))
  } catch {
    return null
  }
}

export const DAYS_OVERDUE = 21;

export function daysElapsed(dateStr) {
  return Math.floor((Date.now() - new Date(dateStr + 'Z')) / 86400000);
}
