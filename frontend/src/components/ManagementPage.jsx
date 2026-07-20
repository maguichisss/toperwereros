import { useState } from 'react'
import CustomerManager from './CustomerManager.jsx'
import ColorManager from './ColorManager.jsx'
import CategoryManager from './CategoryManager.jsx'
import UserManager from './UserManager.jsx'

const SUB_TABS = [
  { key: 'customers', label: 'Clientes' },
  { key: 'colors', label: 'Colores' },
  { key: 'categories', label: 'Categorías' },
  { key: 'users', label: 'Usuarios' },
]

export default function ManagementPage() {
  const [subTab, setSubTab] = useState('customers')

  return (
    <>
      <div className="sub-tabs">
        {SUB_TABS.map(t => (
          <button
            key={t.key}
            className={subTab === t.key ? 'active' : ''}
            onClick={() => setSubTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      {subTab === 'customers' && <CustomerManager />}
      {subTab === 'colors' && <ColorManager />}
      {subTab === 'categories' && <CategoryManager />}
      {subTab === 'users' && <UserManager />}
    </>
  )
}
