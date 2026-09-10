import { formatPrice, DAYS_OVERDUE, daysElapsed } from '../utils.js';

const statusLabel = { active: 'Activo', completed: 'Completado', cancelled: 'Cancelado' };
const statusColor = { active: 'var(--primary)', completed: 'var(--success)', cancelled: 'var(--text-muted)' };

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
              className={`layaway-card ${overdue ? 'layaway-overdue' : ''}`}
              onClick={() => onSelect(l.id)}
            >
              <div className="layaway-card-main">
                <span className="layaway-customer">#{l.id} {l.customer_name}</span>
                <span className="layaway-items-count">{l.items?.length || 0} artículo(s)</span>
              </div>
              <div className="layaway-card-details">
                {isAll && <span style={{ color: statusColor[l.status], fontWeight: 600, fontSize: '0.7rem' }}>{statusLabel[l.status]}</span>}
                <span className="layaway-days">{days} día(s)</span>
                <span className="layaway-balance">${formatPrice(l.balance)}</span>
              </div>
              {(!isAll || l.status === 'active') && (
                <button
                  className="btn btn-danger layaway-cancel-btn"
                  onClick={e => { e.stopPropagation(); onCancel(l.id); }}
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