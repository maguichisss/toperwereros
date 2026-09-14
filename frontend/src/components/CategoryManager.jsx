import { useState, useEffect } from 'react';
import { categoriesApi } from '../api/client.js';
import ConfirmDialog from './ConfirmDialog.jsx';
import Toast from './Toast.jsx';
import useToast from '../hooks/useToast.js';

export default function CategoryManager() {
  const [categories, setCategories] = useState([]);
  const [newName, setNewName] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null); // { id, name }
  const { toast, notify, clear } = useToast();

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      setCategories(await categoriesApi.list());
    } catch {}
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      await categoriesApi.create(newName.trim());
      setNewName('');
      notify('Categoría creada', 'success');
      load();
    } catch {}
  }

  async function handleUpdate(id) {
    if (!editName.trim()) return;
    try {
      await categoriesApi.update(id, editName.trim());
      setEditingId(null);
      notify('Categoría actualizada', 'success');
      load();
    } catch {}
  }

  async function confirmDeleteCategory() {
    if (!confirmDelete) return;
    try {
      await categoriesApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      notify('Categoría eliminada', 'success');
      load();
    } catch (e) {
      notify(e.message, 'error');
      setConfirmDelete(null);
    }
  }

  return (
    <div className="category-manager">
      <h2>Categorías</h2>

      <form className="category-form" onSubmit={handleCreate}>
        <input
          type="text"
          placeholder="Nombre de nueva categoría"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          aria-label="Nombre de nueva categoría"
          autoComplete="off"
          autoCorrect="off"
          spellCheck="false"
        />
        <button type="submit" className="btn btn--primary">
          Añadir
        </button>
      </form>

      <Toast message={toast?.message} type={toast?.type} onClose={clear} />

      {confirmDelete && (
        <ConfirmDialog
          title="Eliminar Categoría"
          message={`¿Estás seguro de eliminar "${confirmDelete.name}"? Esta acción no se puede deshacer.`}
          onConfirm={confirmDeleteCategory}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      {categories.length === 0 && (
        <div className="empty-state">
          <p>No hay categorías aún. Crea una usando el formulario de arriba.</p>
        </div>
      )}

      {categories.map((c) => (
        <div key={c.id} className="category-item">
          {editingId === c.id ? (
            <>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleUpdate(c.id)}
                autoFocus
                aria-label="Editar nombre de categoría"
                autoComplete="off"
                autoCorrect="off"
                spellCheck="false"
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
              <span>{c.name}</span>
              <div className="row row-gap-sm">
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={() => {
                    setEditingId(c.id);
                    setEditName(c.name);
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