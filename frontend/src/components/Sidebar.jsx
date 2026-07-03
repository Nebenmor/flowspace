import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { LayoutGrid, ListTodo, BarChart3, LogOut, Plus, Settings as SettingsIcon, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useWorkspace } from '../context/WorkspaceContext'
import { createOrganization } from '../api/organizations'
import { createWorkspace } from '../api/workspaces'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutGrid },
  { to: '/tasks', label: 'Tasks', icon: ListTodo },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
]

function NewOrgModal({ onClose, onCreated }) {
  const [name, setName] = useState('')
  const mutation = useMutation({
    mutationFn: () => createOrganization({ name }),
    onSuccess: (res) => onCreated(res.data.slug),
  })

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl w-full max-w-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-slate-900">New organization</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={16} /></button>
        </div>
        <form onSubmit={(e) => { e.preventDefault(); if (name.trim()) mutation.mutate() }} className="space-y-3">
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Organization name"
            className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
          {mutation.isError && (
            <p className="text-xs text-red-600">{mutation.error?.response?.data?.detail || 'Could not create organization.'}</p>
          )}
          <button
            type="submit"
            disabled={!name.trim() || mutation.isPending}
            className="w-full text-sm py-2 bg-slate-900 text-white rounded-lg disabled:opacity-40"
          >
            Create organization
          </button>
        </form>
      </div>
    </div>
  )
}

function NewWorkspaceModal({ orgSlug, onClose, onCreated }) {
  const [name, setName] = useState('')
  const mutation = useMutation({
    mutationFn: () => createWorkspace(orgSlug, { name }),
    onSuccess: (res) => onCreated(res.data.slug),
  })

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl w-full max-w-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-slate-900">New workspace</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={16} /></button>
        </div>
        <form onSubmit={(e) => { e.preventDefault(); if (name.trim()) mutation.mutate() }} className="space-y-3">
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Workspace name"
            className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
          {mutation.isError && (
            <p className="text-xs text-red-600">{mutation.error?.response?.data?.detail || 'Could not create workspace.'}</p>
          )}
          <button
            type="submit"
            disabled={!name.trim() || mutation.isPending}
            className="w-full text-sm py-2 bg-slate-900 text-white rounded-lg disabled:opacity-40"
          >
            Create workspace
          </button>
        </form>
      </div>
    </div>
  )
}

export default function Sidebar() {
  const { user, logoutUser } = useAuth()
  const {
    organizations, workspaces, currentOrg, currentWorkspace,
    setCurrentOrg, setCurrentWorkspace, refreshOrganizations, refreshWorkspaces,
  } = useWorkspace()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [showNewOrg, setShowNewOrg] = useState(false)
  const [showNewWorkspace, setShowNewWorkspace] = useState(false)

  return (
    <aside className="w-60 h-screen bg-slate-900 text-slate-300 flex flex-col flex-shrink-0">
      <div className="p-4 border-b border-slate-800">
        <h1 className="text-white font-semibold text-lg">Flowspace</h1>
      </div>

      {/* Org / Workspace switcher */}
      <div className="p-3 border-b border-slate-800 space-y-2">
        <div className="flex items-center gap-1.5">
          <select
            value={currentOrg?.slug || ''}
            onChange={(e) => {
              const org = organizations.find((o) => o.slug === e.target.value)
              setCurrentOrg(org)
            }}
            className="flex-1 min-w-0 bg-slate-800 text-sm text-white rounded-lg px-2 py-1.5 border border-slate-700 focus:outline-none"
          >
            {organizations.map((org) => (
              <option key={org.id} value={org.slug}>{org.name}</option>
            ))}
          </select>
          <button
            onClick={() => setShowNewOrg(true)}
            title="New organization"
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg flex-shrink-0"
          >
            <Plus size={14} />
          </button>
        </div>

        <div className="flex items-center gap-1.5">
          <select
            value={currentWorkspace?.slug || ''}
            onChange={(e) => {
              const ws = workspaces.find((w) => w.slug === e.target.value)
              setCurrentWorkspace(ws)
            }}
            className="flex-1 min-w-0 bg-slate-800 text-sm text-white rounded-lg px-2 py-1.5 border border-slate-700 focus:outline-none"
          >
            {workspaces.map((ws) => (
              <option key={ws.id} value={ws.slug}>{ws.name}</option>
            ))}
          </select>
          <button
            onClick={() => setShowNewWorkspace(true)}
            title="New workspace"
            disabled={!currentOrg}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg flex-shrink-0 disabled:opacity-30"
          >
            <Plus size={14} />
          </button>
        </div>
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

      {showNewOrg && (
        <NewOrgModal
          onClose={() => setShowNewOrg(false)}
          onCreated={(slug) => {
            setShowNewOrg(false)
            refreshOrganizations(slug)
          }}
        />
      )}

      {showNewWorkspace && currentOrg && (
        <NewWorkspaceModal
          orgSlug={currentOrg.slug}
          onClose={() => setShowNewWorkspace(false)}
          onCreated={(slug) => {
            setShowNewWorkspace(false)
            refreshWorkspaces(slug)
            queryClient.invalidateQueries({ queryKey: ['workspaces'] })
          }}
        />
      )}
    </aside>
  )
}