import { useState, useEffect } from 'react';
import { customersApi } from '../api/client.js';

export default function CustomerManager() {
  const [customers, setCustomers] = useState([]);
  const [newName, setNewName] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [editEmail, setEditEmail] = useState('');

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
      setEditingId(null);
      load();
    } catch {}
  }

  async function handleDelete(id) {
    if (!confirm('¿Eliminar este cliente?')) return;
    try {
      await customersApi.remove(id);
      load();
    } catch (err) {
      alert(err.message);
    }
  }

  return (
    <div className="customer-manager">
      <h2>Clientes</h2>

      <form className="category-form" onSubmit={handleCreate}>
        <input
          placeholder="Nombre *"
          value={newName}
          onChange={e => setNewName(e.target.value)}
          style={{ flex: 1 }}
          autoComplete="off"
          autoCorrect="off"
          spellCheck="false"
        />
        <input
          placeholder="Teléfono"
          value={newPhone}
          onChange={e => setNewPhone(e.target.value)}
          style={{ flex: 0.7 }}
          autoComplete="off"
          autoCorrect="off"
          spellCheck="false"
        />
        <input
          placeholder="Email"
          value={newEmail}
          onChange={e => setNewEmail(e.target.value)}
          style={{ flex: 0.7 }}
          autoComplete="off"
          autoCorrect="off"
          spellCheck="false"
        />
        <button type="submit" className="btn btn-primary">Añadir</button>
      </form>

      {customers.length === 0 ? (
        <p className="empty-state">No hay clientes aún.</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
        <table className="receipt-items">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Teléfono</th>
              <th>Email</th>
              <th style={{ width: 140 }}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {customers.map(c => (
              <tr key={c.id}>
                {editingId === c.id ? (
                  <>
                    <td>
                      <input
                        value={editName}
                        onChange={e => setEditName(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleUpdate(c.id)}
                        autoFocus
                        style={{ width: '100%', padding: '0.3rem 0.4rem' }}
                        autoComplete="off"
                        autoCorrect="off"
                        spellCheck="false"
                      />
                    </td>
                    <td>
                      <input
                        value={editPhone}
                        onChange={e => setEditPhone(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleUpdate(c.id)}
                        style={{ width: '100%', padding: '0.3rem 0.4rem' }}
                        autoComplete="off"
                        autoCorrect="off"
                        spellCheck="false"
                      />
                    </td>
                    <td>
                      <input
                        value={editEmail}
                        onChange={e => setEditEmail(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleUpdate(c.id)}
                        style={{ width: '100%', padding: '0.3rem 0.4rem' }}
                        autoComplete="off"
                        autoCorrect="off"
                        spellCheck="false"
                      />
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.25rem' }}>
                        <button className="btn btn-primary" onClick={() => handleUpdate(c.id)}>Guardar</button>
                        <button className="btn btn-secondary" onClick={() => setEditingId(null)}>Cancelar</button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td><strong>{c.name}</strong></td>
                    <td style={{ color: '#666' }}>{c.phone || ''}</td>
                    <td style={{ color: '#666' }}>{c.email || ''}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.25rem' }}>
                        <button className="btn btn-primary" onClick={() => {
                          setEditingId(c.id);
                          setEditName(c.name);
                          setEditPhone(c.phone || '');
                          setEditEmail(c.email || '');
                        }}>Editar</button>
                        <button className="btn btn-danger" onClick={() => handleDelete(c.id)}>Eliminar</button>
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
