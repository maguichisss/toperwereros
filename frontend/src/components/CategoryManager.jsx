import { useState, useEffect } from 'react';
import { categoriesApi } from '../api/client.js';

export default function CategoryManager() {
  const [categories, setCategories] = useState([]);
  const [newName, setNewName] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');

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
      load();
    } catch {}
  }

  async function handleUpdate(id) {
    if (!editName.trim()) return;
    try {
      await categoriesApi.update(id, editName.trim());
      setEditingId(null);
      load();
    } catch {}
  }

  async function handleDelete(id) {
    if (!confirm('¿Eliminar esta categoría?')) return;
    try {
      await categoriesApi.remove(id);
      load();
    } catch (err) {
      alert(err.message);
    }
  }

  return (
    <div className="category-manager">
      <h2>Categorías</h2>

      <form className="category-form" onSubmit={handleCreate}>
        <input
          placeholder="Nombre de nueva categoría"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
        />
        <button type="submit" className="btn btn-primary">
          Añadir
        </button>
      </form>

      {categories.length === 0 && (
        <p className="empty-state">No hay categorías aún.</p>
      )}

      {categories.map((c) => (
        <div key={c.id} className="category-item">
          {editingId === c.id ? (
            <>
              <input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleUpdate(c.id)}
                autoFocus
                style={{ flex: 1, padding: '0.3rem 0.5rem' }}
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
              <span>{c.name}</span>
              <div style={{ display: 'flex', gap: '0.25rem' }}>
                <button
                  className="btn btn-primary"
                  onClick={() => {
                    setEditingId(c.id);
                    setEditName(c.name);
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
