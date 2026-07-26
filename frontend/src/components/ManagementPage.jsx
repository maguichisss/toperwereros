import { useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import CustomerManager from './CustomerManager.jsx'
import ColorManager from './ColorManager.jsx'
import CategoryManager from './CategoryManager.jsx'
import UserManager from './UserManager.jsx'

const SUB_TABS = [
  { key: 'customers', label: 'Clientes' },
  { key: 'colors', label: 'Colores', adminOnly: true },
  { key: 'categories', label: 'Categorías', adminOnly: true },
  { key: 'users', label: 'Usuarios', adminOnly: true },
]

export default function ManagementPage() {
  const { can } = useAuth()
  const [subTab, setSubTab] = useState('customers')

  const visibleTabs = SUB_TABS.filter(t => !t.adminOnly || can('user.manage'))

  return (
    <>
      <div className="sub-tabs">
        {visibleTabs.map(t => (
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
