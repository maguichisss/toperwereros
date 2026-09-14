import { useState, useEffect } from 'react';
import { colorsApi } from '../api/client.js';
import Toast from './Toast.jsx';
import ConfirmDialog from './ConfirmDialog.jsx';
import useToast from '../hooks/useToast.js';

export default function ColorManager() {
  const [colors, setColors] = useState([]);
  const [newName, setNewName] = useState('');
  const [newHex, setNewHex] = useState('#000000');
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [editHex, setEditHex] = useState('#000000');
  const { toast, notify, clear } = useToast();
  const [confirmDelete, setConfirmDelete] = useState(null); // { id, name }

  useEffect(() => {
    load();
  }, []);

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
      notify('Color creado', 'success');
      setNewName('');
      setNewHex('#000000');
      load();
    } catch (err) {
      notify(err.message);
    }
  }

  async function handleUpdate(id) {
    if (!editName.trim()) return;
    try {
      await colorsApi.update(id, { name: editName.trim(), hex: editHex });
      notify('Color actualizado', 'success');
      setEditingId(null);
      load();
    } catch (err) {
      notify(err.message);
    }
  }

  async function confirmDeleteColor() {
    if (!confirmDelete) return;
    try {
      await colorsApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      notify('Color eliminado', 'success');
      load();
    } catch (err) {
      notify(err.message, 'error');
      setConfirmDelete(null);
    }
  }

  return (
    <div className="category-manager">
      <h2>Colores</h2>

      <Toast message={toast?.message} type={toast?.type} onClose={clear} />

      {confirmDelete && (
        <ConfirmDialog
          title="Eliminar Color"
          message={`¿Estás seguro de eliminar "${confirmDelete.name}"? Esta acción no se puede deshacer.`}
          onConfirm={confirmDeleteColor}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      <form className="category-form" onSubmit={handleCreate}>
        <input
          type="text"
          placeholder="Nombre de nuevo color"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          aria-label="Nombre del color"
          autoComplete="off"
          autoCorrect="off"
          spellCheck="false"
        />
        <input
          type="color"
          className="color-jump"
          value={newHex}
          onChange={(e) => setNewHex(e.target.value)}
          title="Color hexadecimal"
          aria-label="Color hexadecimal"
        />
        <button type="submit" className="btn btn--primary">
          Añadir
        </button>
      </form>

      {colors.length === 0 && (
        <div className="empty-state">
          <p>No hay colores aún. Crea uno usando el formulario de arriba.</p>
        </div>
      )}

      {colors.map((c) => (
        <div key={c.id} className="category-item">
          {editingId === c.id ? (
            <>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleUpdate(c.id)}
                autoFocus
                aria-label="Editar nombre de color"
                autoComplete="off"
                autoCorrect="off"
                spellCheck="false"
              />
              <input
                type="color"
                className="color-jump"
                value={editHex}
                onChange={(e) => setEditHex(e.target.value)}
                title="Color hexadecimal"
                aria-label="Editar color hexadecimal"
              />
              <div className="row row-gap-sm">
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={() => handleUpdate(c.id)}
                >
                  Guardar
                </button>
                <button
                  type="button"
                  className="btn btn--secondary"
                  onClick={() => setEditingId(null)}
                >
                  Cancelar
                </button>
              </div>
            </>
          ) : (
            <>
              <span className="color-item-name">
                <span
                  className="color-preview"
                  style={{ background: c.hex }}
                  aria-hidden="true"
                />
                {c.name}
              </span>
              <div className="row row-gap-sm">
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={() => {
                    setEditingId(c.id);
                    setEditName(c.name);
                    setEditHex(c.hex);
                  }}
                >
                  Editar
                </button>
                <button
                  type="button"
                  className="btn btn--danger"
                  onClick={() => setConfirmDelete({ id: c.id, name: c.name })}
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