import { useState, useEffect } from 'react';
import { customersApi } from '../api/client.js';
import ConfirmDialog from './ConfirmDialog.jsx';
import Toast from './Toast.jsx';
import useToast from '../hooks/useToast.js';

export default function CustomerManager() {
  const [customers, setCustomers] = useState([]);
  const [newName, setNewName] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null); // { id, name }
  const { toast, notify, clear } = useToast();

  useEffect(() => { load(); }, []);

  async function load() {
    try {
      setCustomers(await customersApi.list());
    } catch {}
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      await customersApi.create({ name: newName.trim(), phone: newPhone.trim() || null, email: newEmail.trim() || null });
      notify('Cliente creado', 'success');
      setNewName('');
      setNewPhone('');
      setNewEmail('');
      load();
    } catch {}
  }

  async function handleUpdate(id) {
    if (!editName.trim()) return;
    try {
      await customersApi.update(id, { name: editName.trim(), phone: editPhone.trim() || null, email: editEmail.trim() || null });
      notify('Cliente actualizado', 'success');
      setEditingId(null);
      load();
    } catch {}
  }

  async function confirmDeleteCustomer() {
    if (!confirmDelete) return;
    try {
      await customersApi.remove(confirmDelete.id);
      setConfirmDelete(null);
      notify('Cliente eliminado', 'success');
      load();
    } catch (e) {
      notify(e.message, 'error');
      setConfirmDelete(null);
    }
  }

  return (
    <div className="customer-manager">
      <h2>Clientes</h2>

      <form className="category-form" onSubmit={handleCreate}>
        <input
          type="text"
          placeholder="Nombre *"
          value={newName}
          onChange={e => setNewName(e.target.value)}
          aria-label="Nombre del cliente"
          autoComplete="name"
          autoCorrect="off"
          spellCheck="false"
        />
        <input
          type="tel"
          inputMode="tel"
          placeholder="Teléfono"
          value={newPhone}
          onChange={e => setNewPhone(e.target.value)}
          aria-label="Teléfono del cliente"
          autoComplete="tel"
          autoCorrect="off"
          spellCheck="false"
        />
        <input
          type="email"
          placeholder="Email"
          value={newEmail}
          onChange={e => setNewEmail(e.target.value)}
          aria-label="Email del cliente"
          autoComplete="email"
          autoCorrect="off"
          spellCheck="false"
        />
        <button type="submit" className="btn btn--primary">Añadir</button>
      </form>

      <Toast message={toast?.message} type={toast?.type} onClose={clear} />

      {confirmDelete && (
        <ConfirmDialog
          title="Eliminar Cliente"
          message={`¿Estás seguro de eliminar "${confirmDelete.name}"? Esta acción no se puede deshacer.`}
          onConfirm={confirmDeleteCustomer}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      {customers.length === 0 ? (
        <div className="empty-state">
          <p>No hay clientes aún. Crea uno usando el formulario de arriba.</p>
        </div>
      ) : (
        <div className="table-scroll">
        <table className="receipt-items">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Teléfono</th>
              <th>Email</th>
              <th className="actions-col">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {customers.map(c => (
              <tr key={c.id}>
                {editingId === c.id ? (
                  <>
                    <td>
                      <input
                        className="input-cell"
                        type="text"
                        value={editName}
                        onChange={e => setEditName(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleUpdate(c.id)}
                        autoFocus
                        aria-label="Editar nombre"
                        autoComplete="off"
                        autoCorrect="off"
                        spellCheck="false"
                      />
                    </td>
                    <td>
                      <input
                        className="input-cell"
                        type="tel"
                        inputMode="tel"
                        value={editPhone}
                        onChange={e => setEditPhone(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleUpdate(c.id)}
                        aria-label="Editar teléfono"
                        autoComplete="off"
                        autoCorrect="off"
                        spellCheck="false"
                      />
                    </td>
                    <td>
                      <input
                        className="input-cell"
                        type="email"
                        value={editEmail}
                        onChange={e => setEditEmail(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleUpdate(c.id)}
                        aria-label="Editar email"
                        autoComplete="off"
                        autoCorrect="off"
                        spellCheck="false"
                      />
                    </td>
                    <td>
                      <div className="row row-gap-sm">
                        <button type="button" className="btn btn--primary" onClick={() => handleUpdate(c.id)}>Guardar</button>
                        <button type="button" className="btn btn--secondary" onClick={() => setEditingId(null)}>Cancelar</button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td><strong>{c.name}</strong></td>
                    <td className="cell-muted">{c.phone || ''}</td>
                    <td className="cell-muted">{c.email || ''}</td>
                    <td>
                      <div className="row row-gap-sm">
                        <button type="button" className="btn btn--primary" onClick={() => {
                          setEditingId(c.id);
                          setEditName(c.name);
                          setEditPhone(c.phone || '');
                          setEditEmail(c.email || '');
                        }}>Editar</button>
                        <button type="button" className="btn btn--danger" onClick={() => setConfirmDelete({ id: c.id, name: c.name })}>Eliminar</button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </div>
  );
}