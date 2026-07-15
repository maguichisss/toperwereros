import { useState, useEffect } from 'react';
import { colorsApi } from '../api/client.js';
import Toast from './Toast.jsx';

export default function ColorManager() {
  const [colors, setColors] = useState([]);
  const [newName, setNewName] = useState('');
  const [newHex, setNewHex] = useState('#000000');
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [editHex, setEditHex] = useState('#000000');
  const [toast, setToast] = useState(null);

  useEffect(() => {
    load();
  }, []);

  function showToast(message, type = 'error') {
    setToast({ message, type });
  }

  async function load() {
    try {
      setColors(await colorsApi.list());
    } catch {}
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      await colorsApi.create({ name: newName.trim(), hex: newHex });
      showToast('Color creado', 'success');
      setNewName('');
      setNewHex('#000000');
      load();
    } catch (err) {
      showToast(err.message);
    }
  }

  async function handleUpdate(id) {
    if (!editName.trim()) return;
    try {
      await colorsApi.update(id, { name: editName.trim(), hex: editHex });
      showToast('Color actualizado', 'success');
      setEditingId(null);
      load();
    } catch (err) {
      showToast(err.message);
    }
  }

  async function handleDelete(id) {
    if (!confirm('¿Eliminar este color?')) return;
    try {
      await colorsApi.remove(id);
      showToast('Color eliminado', 'success');
      load();
    } catch (err) {
      showToast(err.message);
    }
  }

  return (
    <div className="category-manager">
      <h2>Colores</h2>

      <Toast
        message={toast?.message}
        type={toast?.type}
        onClose={() => setToast(null)}
      />

      <form className="category-form" onSubmit={handleCreate}>
        <input
          placeholder="Nombre de nuevo color"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          style={{ flex: 1 }}
          autoComplete="off"
          autoCorrect="off"
          spellCheck="false"
        />
        <input
          type="color"
          value={newHex}
          onChange={(e) => setNewHex(e.target.value)}
          title="Color hexadecimal"
          style={{ width: 40, height: 36, padding: 0, border: 'none', cursor: 'pointer' }}
        />
        <button type="submit" className="btn btn-primary">
          Añadir
        </button>
      </form>

      {colors.length === 0 && (
        <p className="empty-state">No hay colores aún.</p>
      )}

      {colors.map((c) => (
        <div key={c.id} className="category-item">
          {editingId === c.id ? (
            <>
              <input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleUpdate(c.id)}
                autoFocus
                style={{ flex: 1, padding: '0.3rem 0.5rem' }}
                autoComplete="off"
                autoCorrect="off"
                spellCheck="false"
              />
              <input
                type="color"
                value={editHex}
                onChange={(e) => setEditHex(e.target.value)}
                title="Color hexadecimal"
                style={{ width: 40, height: 36, padding: 0, border: 'none', cursor: 'pointer' }}
              />
              <div style={{ display: 'flex', gap: '0.25rem' }}>
                <button
                  className="btn btn-primary"
                  onClick={() => handleUpdate(c.id)}
                >
                  Guardar
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => setEditingId(null)}
                >
                  Cancelar
                </button>
              </div>
            </>
          ) : (
            <>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span
                  style={{
                    display: 'inline-block',
                    width: 20,
                    height: 20,
                    borderRadius: 4,
                    background: c.hex,
                    border: '1px solid #ccc',
                  }}
                />
                {c.name}
              </span>
              <div style={{ display: 'flex', gap: '0.25rem' }}>
                <button
                  className="btn btn-primary"
                  onClick={() => {
                    setEditingId(c.id);
                    setEditName(c.name);
                    setEditHex(c.hex);
                  }}
                >
                  Editar
                </button>
                <button
                  className="btn btn-danger"
                  onClick={() => handleDelete(c.id)}
                >
                  Eliminar
                </button>
              </div>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
