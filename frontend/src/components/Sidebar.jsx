import { Link, useLocation } from 'react-router-dom'
import { LayoutGrid, ListTodo, BarChart3, LogOut, ChevronDown } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useWorkspace } from '../context/WorkspaceContext'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutGrid },
  { to: '/tasks', label: 'Tasks', icon: ListTodo },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
]

export default function Sidebar() {
  const { user, logoutUser } = useAuth()
  const { organizations, workspaces, currentOrg, currentWorkspace, setCurrentOrg, setCurrentWorkspace } = useWorkspace()
  const location = useLocation()

  return (
    <aside className="w-60 h-screen bg-slate-900 text-slate-300 flex flex-col flex-shrink-0">
      <div className="p-4 border-b border-slate-800">
        <h1 className="text-white font-semibold text-lg">Flowspace</h1>
      </div>

      {/* Org / Workspace switcher */}
      <div className="p-3 border-b border-slate-800 space-y-2">
        <select
          value={currentOrg?.slug || ''}
          onChange={(e) => {
            const org = organizations.find((o) => o.slug === e.target.value)
            setCurrentOrg(org)
          }}
          className="w-full bg-slate-800 text-sm text-white rounded-lg px-2 py-1.5 border border-slate-700 focus:outline-none"
        >
          {organizations.map((org) => (
            <option key={org.id} value={org.slug}>{org.name}</option>
          ))}
        </select>

        <select
          value={currentWorkspace?.slug || ''}
          onChange={(e) => {
            const ws = workspaces.find((w) => w.slug === e.target.value)
            setCurrentWorkspace(ws)
          }}
          className="w-full bg-slate-800 text-sm text-white rounded-lg px-2 py-1.5 border border-slate-700 focus:outline-none"
        >
          {workspaces.map((ws) => (
            <option key={ws.id} value={ws.slug}>{ws.name}</option>
          ))}
        </select>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ to, label, icon: Icon }) => {
          const active = location.pathname === to
          return (
            <Link
              key={to}
              to={to}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                active ? 'bg-slate-800 text-white' : 'hover:bg-slate-800/60 hover:text-white'
              }`}
            >
              <Icon size={16} />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* User + logout */}
      <div className="p-3 border-t border-slate-800">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="text-sm text-white truncate">{user?.full_name || user?.username}</p>
            <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          </div>
          <button
            onClick={logoutUser}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors flex-shrink-0"
            title="Log out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  )
}