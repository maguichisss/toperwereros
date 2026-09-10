import { useState, useEffect, useCallback } from 'react';
import { layawaysApi } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx';
import ConfirmDialog from './ConfirmDialog.jsx';
import LayawayList from './LayawayList.jsx';
import LayawayCreateView from './LayawayCreateView.jsx';
import LayawayDetailView from './LayawayDetailView.jsx';
import Pagination from './Pagination.jsx';

export default function LayawayView({ initialMode }) {
  const { can } = useAuth();
  const [mode, setMode] = useState(initialMode || 'active');
  const [activeLayaways, setActiveLayaways] = useState([]);
  const [allLayaways, setAllLayaways] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedLayaway, setSelectedLayaway] = useState(null);

  const [error, setError] = useState('');
  const [confirmCancel, setConfirmCancel] = useState(null);
  const [confirmComplete, setConfirmComplete] = useState(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  useEffect(() => {
    if (initialMode) setMode(initialMode)
  }, [initialMode])

  const loadActive = useCallback(async () => {
    try {
      const res = await layawaysApi.list({ status: 'active', perPage: 100 });
      setActiveLayaways(res.layaways || []);
    } catch {}
  }, []);

  const loadAll = useCallback(async () => {
    try {
      const res = await layawaysApi.list({ perPage: 100 });
      setAllLayaways(res.layaways || []);
    } catch {}
  }, []);

  useEffect(() => {
    if (mode === 'active') loadActive();
    if (mode === 'all') loadAll();
  }, [mode, loadActive, loadAll]);

  function handleSelect(id) {
    setSelectedId(id);
    setSelectedLayaway(null);
    setMode('detail');
  }

  function handleBack() {
    setSelectedId(null);
    setSelectedLayaway(null);
    if (mode === 'detail') setMode('active');
  }

  async function executeCancel() {
    if (!confirmCancel) return;
    try {
      await layawaysApi.cancel(confirmCancel);
      setConfirmCancel(null);
      loadActive();
      if (selectedId === confirmCancel) handleBack();
    } catch (e) {
      setError(e.message);
    }
  }

  async function executeComplete() {
    if (!confirmComplete) return;
    try {
      await layawaysApi.complete(confirmComplete);
      setConfirmComplete(null);
      setSelectedId(null);
      setSelectedLayaway(null);
      setMode('active');
      loadActive();
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    if (mode === 'detail' && selectedId && !selectedLayaway) {
      layawaysApi.get(selectedId).then(setSelectedLayaway).catch(() => {});
    }
  }, [mode, selectedId, selectedLayaway]);

  useEffect(() => {
    setPage(1);
  }, [search, mode]);

  function filterLayaways(list) {
    const q = search.trim().toLowerCase();
    if (!q) return list;
    const idMatch = q.match(/^id:\s*#?(\d+)$/);
    if (idMatch) {
      const targetId = parseInt(idMatch[1], 10);
      return list.filter(l => l.id === targetId);
    }
    return list.filter(l => l.customer_name?.toLowerCase().includes(q));
  }

  function paginate(list) {
    const start = (page - 1) * perPage;
    return list.slice(start, start + perPage);
  }

  const filteredActive = filterLayaways(activeLayaways);
  const filteredAll = filterLayaways(allLayaways);
  const pagedActive = paginate(filteredActive);
  const pagedAll = paginate(filteredAll);

  const activeTotalPages = Math.ceil(filteredActive.length / perPage);
  const allTotalPages = Math.ceil(filteredAll.length / perPage);
  const currentTotalPages = mode === 'active' ? activeTotalPages : allTotalPages;

  return (
    <div className="layaway-view">
      <div className="sales-tabs">
        <button className={mode === 'active' ? 'active' : ''} onClick={() => setMode('active')}>Apartados Activos</button>
        <button className={mode === 'all' ? 'active' : ''} onClick={() => setMode('all')}>Todos</button>
        {can('apartado.create') && (
          <button className={mode === 'create' ? 'active' : ''} onClick={() => { setMode('create'); setError(''); }}>Nuevo Apartado</button>
        )}
      </div>

      {(mode === 'active' || mode === 'all') && (
        <div className="filter-bar" style={{ marginBottom: '0.75rem' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 200, width: '100%' }}>
            <input
              className="search-input"
              placeholder="Buscar por nombre o #ID..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              autoComplete="off"
              autoCorrect="off"
              spellCheck="false"
              style={{ paddingRight: search ? '2rem' : undefined }}
            />
            {search && (
              <button
                className="input-clear"
                onClick={() => setSearch('')}
              >
                ✕
              </button>
            )}
          </div>
          <select
            value={perPage}
            onChange={e => { setPerPage(Number(e.target.value)); setPage(1); }}
            className="input-sm"
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
          </select>
        </div>
      )}

      {error && <p className="error-text">{error}</p>}

      {confirmCancel && (
        <ConfirmDialog
          title="Cancelar Apartado"
          message="¿Cancelar este apartado? Se restaurará el stock de los productos."
          onConfirm={executeCancel}
          onCancel={() => setConfirmCancel(null)}
        />
      )}

      {confirmComplete && (
        <ConfirmDialog
          title="Completar Apartado"
          message="¿Completar este apartado? Se creará una venta y se descontará del stock."
          onConfirm={executeComplete}
          onCancel={() => setConfirmComplete(null)}
        />
      )}

      {mode === 'active' && (
        <LayawayList
          variant="active"
          layaways={pagedActive}
          onSelect={handleSelect}
          onCancel={setConfirmCancel}
          isEmpty={activeLayaways.length === 0}
          isFilterNoResults={activeLayaways.length > 0 && filteredActive.length === 0}
        />
      )}

      {mode === 'all' && (
        <LayawayList
          variant="all"
          layaways={pagedAll}
          onSelect={handleSelect}
          onCancel={setConfirmCancel}
          isEmpty={allLayaways.length === 0}
          isFilterNoResults={allLayaways.length > 0 && filteredAll.length === 0}
        />
      )}

      {mode === 'create' && (
        <LayawayCreateView onBack={() => { setMode('active'); loadActive(); }} onCreated={() => { setMode('active'); loadActive(); }} />
      )}

      {mode === 'detail' && selectedLayaway && (
        <LayawayDetailView
          layaway={selectedLayaway}
          onBack={handleBack}
          onCancel={setConfirmCancel}
          onComplete={setConfirmComplete}
          onUpdated={setSelectedLayaway}
        />
      )}

      {(mode === 'active' || mode === 'all') && currentTotalPages > 1 && (
        <>
          <Pagination page={page} totalPages={currentTotalPages} onChange={setPage} />
          <p style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)', margin: '0.3rem 0 0' }}>Página {page} de {currentTotalPages}</p>
        </>
      )}
    </div>
  );
}