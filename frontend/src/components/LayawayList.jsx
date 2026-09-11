import { formatPrice, DAYS_OVERDUE, daysElapsed } from '../utils.js';

const statusLabel = { active: 'Activo', completed: 'Completado', cancelled: 'Cancelado' };

export default function LayawayList({ layaways, variant, onSelect, onCancel, isEmpty, isFilterNoResults }) {
  const isAll = variant === 'all';
  const emptyText = isAll ? 'No hay apartados registrados.' : 'No hay apartados activos.';

  return (
    <div className="layaway-list">
      {isFilterNoResults ? (
        <p className="empty-state">No se encontraron apartados.</p>
      ) : isEmpty ? (
        <p className="empty-state">{emptyText}</p>
      ) : (
        layaways.map(l => {
          const days = daysElapsed(l.created_at);
          const overdue = days > DAYS_OVERDUE && (!isAll || l.status === 'active');
          return (
            <div
              key={l.id}
              className={`layaway-card ${overdue ? 'layaway-card--overdue' : ''}`}
            >
              <button
                type="button"
                className="layaway-card__select"
                onClick={() => onSelect(l.id)}
                aria-label={`Ver apartado ${l.id} de ${l.customer_name}, saldo ${formatPrice(l.balance)}`}
              >
                <div className="layaway-card__main">
                  <span className="layaway-card__customer">#{l.id} {l.customer_name}</span>
                  <span className="layaway-card__count">{l.items?.length || 0} artículo(s)</span>
                </div>
                <div className="layaway-card__details">
                  {isAll && <span className={`layaway-status layaway-status--${l.status}`}>{statusLabel[l.status]}</span>}
                  <span className="layaway-card__days">{days} día(s)</span>
                  <span className="layaway-card__balance">${formatPrice(l.balance)}</span>
                </div>
              </button>
              {(!isAll || l.status === 'active') && (
                <button
                  type="button"
                  className="btn btn--danger layaway-card__cancel-btn"
                  onClick={() => onCancel(l.id)}
                  aria-label={`Cancelar apartado ${l.id}`}
                >
                  Cancelar
                </button>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}