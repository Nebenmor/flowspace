import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Lock, Mail, X, ChevronDown, ChevronRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useWorkspace } from '../context/WorkspaceContext'
import { listWorkspaceMembers, updateWorkspace, archiveWorkspace, addWorkspaceMember } from '../api/workspaces'
import { listOrgMembers, changeOrgMemberRole } from '../api/organizations'
import { listLabels, createLabel, deleteLabel } from '../api/labels'
import { listCustomFields, createCustomField, deleteCustomField } from '../api/customFields'
import { listWebhooks, createWebhook, updateWebhook, deleteWebhook, listWebhookDeliveries } from '../api/webhooks'
import { listInvitations, createInvitation, cancelInvitation } from '../api/invitations'

const TABS = ['Workspace', 'Labels', 'Custom fields', 'Webhooks', 'Members']

function Card({ children }) {
  return <div className="bg-white border border-slate-200 rounded-xl p-5">{children}</div>
}

function AdminNotice({ scope = 'workspace admin' }) {
  return (
    <div className="flex items-center gap-2 bg-amber-50 text-amber-700 text-sm px-3 py-2 rounded-lg mb-4">
      <Lock size={14} /> Only a {scope} can make changes here — you can still view everything below.
    </div>
  )
}

// ── Workspace tab ──────────────────────────────────────────────────────────

function WorkspaceTab({ orgSlug, workspace, isAdmin, onArchived }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState(workspace.name)
  const [description, setDescription] = useState(workspace.description || '')

  const updateMutation = useMutation({
    mutationFn: (data) => updateWorkspace(orgSlug, workspace.slug, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workspaces'] }),
  })

  const archiveMutation = useMutation({
    mutationFn: () => archiveWorkspace(orgSlug, workspace.slug),
    onSuccess: onArchived,
  })

  return (
    <div className="space-y-4 max-w-md">
      {!isAdmin && <AdminNotice />}
      <Card>
        <label className="text-xs font-medium text-slate-500">Workspace name</label>
        <input
          value={name}
          disabled={!isAdmin}
          onChange={(e) => setName(e.target.value)}
          onBlur={() => name.trim() && name !== workspace.name && updateMutation.mutate({ name })}
          className="mt-1 w-full text-sm border border-slate-200 rounded-lg px-3 py-2 disabled:bg-slate-50 disabled:text-slate-400"
        />
        <label className="text-xs font-medium text-slate-500 mt-4 block">Description</label>
        <textarea
          value={description}
          disabled={!isAdmin}
          rows={3}
          onChange={(e) => setDescription(e.target.value)}
          onBlur={() => description !== (workspace.description || '') && updateMutation.mutate({ description })}
          className="mt-1 w-full text-sm border border-slate-200 rounded-lg px-3 py-2 disabled:bg-slate-50 disabled:text-slate-400"
        />
      </Card>

      {isAdmin && (
        <Card>
          <p className="text-sm font-medium text-red-700">Archive this workspace</p>
          <p className="text-xs text-slate-500 mt-1 mb-3">Archived workspaces are hidden but not deleted.</p>
          <button
            onClick={() => {
              if (confirm(`Archive "${workspace.name}"? You can restore it from the database later, but it will disappear from the app.`)) {
                archiveMutation.mutate()
              }
            }}
            className="text-sm px-3 py-1.5 border border-red-200 text-red-700 rounded-lg hover:bg-red-50"
          >
            Archive workspace
          </button>
        </Card>
      )}
    </div>
  )
}

// ── Labels tab ──────────────────────────────────────────────────────────────

function LabelsTab({ orgSlug, workspaceSlug, isAdmin }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [color, setColor] = useState('#6366f1')

  const { data: labels } = useQuery({
    queryKey: ['labels', orgSlug, workspaceSlug],
    queryFn: () => listLabels(orgSlug, workspaceSlug).then((r) => r.data),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['labels', orgSlug, workspaceSlug] })

  const createMutation = useMutation({
    mutationFn: () => createLabel(orgSlug, workspaceSlug, { name, color }),
    onSuccess: () => { setName(''); invalidate() },
  })
  const deleteMutation = useMutation({
    mutationFn: (id) => deleteLabel(orgSlug, workspaceSlug, id),
    onSuccess: invalidate,
  })

  return (
    <div className="max-w-md space-y-4">
      {!isAdmin && <AdminNotice />}
      <Card>
        {isAdmin && (
          <form
            onSubmit={(e) => { e.preventDefault(); if (name.trim()) createMutation.mutate() }}
            className="flex items-center gap-2 mb-4"
          >
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Label name"
              className="flex-1 text-sm border border-slate-200 rounded-lg px-3 py-1.5"
            />
            <input
              type="color"
              value={color}
              onChange={(e) => setColor(e.target.value)}
              className="w-9 h-8 border border-slate-200 rounded-lg cursor-pointer"
            />
            <button
              type="submit"
              disabled={!name.trim()}
              className="p-2 bg-slate-900 text-white rounded-lg disabled:opacity-40"
            >
              <Plus size={14} />
            </button>
          </form>
        )}

        <div className="space-y-1.5">
          {(labels || []).length === 0 && <p className="text-sm text-slate-400">No labels yet.</p>}
          {(labels || []).map((label) => (
            <div key={label.id} className="flex items-center justify-between text-sm px-2 py-1.5 rounded-lg hover:bg-slate-50">
              <span className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: label.color }} />
                {label.name}
              </span>
              {isAdmin && (
                <button onClick={() => deleteMutation.mutate(label.id)} className="text-slate-400 hover:text-red-600">
                  <Trash2 size={13} />
                </button>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

// ── Custom fields tab ─────────────────────────────────────────────────────

const FIELD_TYPES = ['text', 'number', 'date', 'boolean', 'select']

function CustomFieldsTab({ orgSlug, workspaceSlug, isAdmin }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [fieldType, setFieldType] = useState('text')
  const [options, setOptions] = useState('')

  const { data: fields } = useQuery({
    queryKey: ['custom-fields', orgSlug, workspaceSlug],
    queryFn: () => listCustomFields(orgSlug, workspaceSlug).then((r) => r.data),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['custom-fields', orgSlug, workspaceSlug] })

  const createMutation = useMutation({
    mutationFn: () => createCustomField(orgSlug, workspaceSlug, {
      name,
      field_type: fieldType,
      options: fieldType === 'select' ? options.split(',').map((o) => o.trim()).filter(Boolean) : null,
    }),
    onSuccess: () => { setName(''); setOptions(''); invalidate() },
  })
  const deleteMutation = useMutation({
    mutationFn: (id) => deleteCustomField(orgSlug, workspaceSlug, id),
    onSuccess: invalidate,
  })

  return (
    <div className="max-w-md space-y-4">
      {!isAdmin && <AdminNotice />}
      <Card>
        {isAdmin && (
          <form
            onSubmit={(e) => { e.preventDefault(); if (name.trim()) createMutation.mutate() }}
            className="space-y-2 mb-4 pb-4 border-b border-slate-100"
          >
            <div className="flex items-center gap-2">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Field name"
                className="flex-1 text-sm border border-slate-200 rounded-lg px-3 py-1.5"
              />
              <select
                value={fieldType}
                onChange={(e) => setFieldType(e.target.value)}
                className="text-sm border border-slate-200 rounded-lg px-2 py-1.5"
              >
                {FIELD_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            {fieldType === 'select' && (
              <input
                value={options}
                onChange={(e) => setOptions(e.target.value)}
                placeholder="Comma-separated options"
                className="w-full text-sm border border-slate-200 rounded-lg px-3 py-1.5"
              />
            )}
            <button
              type="submit"
              disabled={!name.trim()}
              className="text-sm px-3 py-1.5 bg-slate-900 text-white rounded-lg disabled:opacity-40"
            >
              Add field
            </button>
          </form>
        )}

        <div className="space-y-1.5">
          {(fields || []).length === 0 && <p className="text-sm text-slate-400">No custom fields yet.</p>}
          {(fields || []).map((field) => (
            <div key={field.id} className="flex items-center justify-between text-sm px-2 py-1.5 rounded-lg hover:bg-slate-50">
              <span>{field.name} <span className="text-slate-400 text-xs">({field.field_type})</span></span>
              {isAdmin && (
                <button onClick={() => deleteMutation.mutate(field.id)} className="text-slate-400 hover:text-red-600">
                  <Trash2 size={13} />
                </button>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

// ── Webhooks tab ──────────────────────────────────────────────────────────

const WEBHOOK_EVENTS = ['task.created', 'task.updated', 'task.deleted', 'task.assigned', 'task.completed', 'member.invited', 'member.joined']

function DeliveryLog({ orgSlug, webhookId }) {
  const { data: deliveries } = useQuery({
    queryKey: ['webhook-deliveries', orgSlug, webhookId],
    queryFn: () => listWebhookDeliveries(orgSlug, webhookId).then((r) => r.data),
  })

  if (!deliveries) return <p className="text-xs text-slate-400 px-3 py-2">Loading deliveries...</p>
  if (deliveries.length === 0) return <p className="text-xs text-slate-400 px-3 py-2">No deliveries yet.</p>

  return (
    <div className="px-3 py-2 space-y-1 bg-slate-50 rounded-lg">
      {deliveries.slice(0, 10).map((d) => (
        <div key={d.id} className="flex items-center justify-between text-xs">
          <span className="text-slate-600">{d.event_type}</span>
          <span className={`px-1.5 py-0.5 rounded ${d.status === 'success' ? 'bg-green-100 text-green-700' : d.status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-slate-200 text-slate-600'}`}>
            {d.status}{d.response_status ? ` · ${d.response_status}` : ''}
          </span>
          <span className="text-slate-400">{new Date(d.created_at).toLocaleString()}</span>
        </div>
      ))}
    </div>
  )
}

function WebhooksTab({ orgSlug, isOrgAdmin }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [events, setEvents] = useState([])
  const [expanded, setExpanded] = useState(null)

  const { data: webhooks } = useQuery({
    queryKey: ['webhooks', orgSlug],
    queryFn: () => listWebhooks(orgSlug).then((r) => r.data),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['webhooks', orgSlug] })

  const createMutation = useMutation({
    mutationFn: () => createWebhook(orgSlug, { name, url, events }),
    onSuccess: () => { setName(''); setUrl(''); setEvents([]); invalidate() },
  })
  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }) => updateWebhook(orgSlug, id, { is_active }),
    onSuccess: invalidate,
  })
  const deleteMutation = useMutation({
    mutationFn: (id) => deleteWebhook(orgSlug, id),
    onSuccess: invalidate,
  })

  return (
    <div className="max-w-lg space-y-4">
      {!isOrgAdmin && <AdminNotice scope="organization owner or admin" />}
      <Card>
        {isOrgAdmin && (
          <form
            onSubmit={(e) => { e.preventDefault(); if (name.trim() && url.trim() && events.length) createMutation.mutate() }}
            className="space-y-2 mb-4 pb-4 border-b border-slate-100"
          >
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Webhook name"
              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-1.5"
            />
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/webhook"
              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-1.5"
            />
            <div className="flex flex-wrap gap-1.5">
              {WEBHOOK_EVENTS.map((ev) => (
                <button
                  type="button"
                  key={ev}
                  onClick={() => setEvents((prev) => prev.includes(ev) ? prev.filter((e2) => e2 !== ev) : [...prev, ev])}
                  className={`text-xs px-2 py-1 rounded-full border ${
                    events.includes(ev) ? 'bg-slate-900 text-white border-slate-900' : 'border-slate-200 text-slate-600'
                  }`}
                >
                  {ev}
                </button>
              ))}
            </div>
            <button
              type="submit"
              disabled={!name.trim() || !url.trim() || events.length === 0}
              className="text-sm px-3 py-1.5 bg-slate-900 text-white rounded-lg disabled:opacity-40"
            >
              Add webhook
            </button>
          </form>
        )}

        <div className="space-y-1.5">
          {(webhooks || []).length === 0 && <p className="text-sm text-slate-400">No webhooks configured.</p>}
          {(webhooks || []).map((wh) => (
            <div key={wh.id} className="rounded-lg hover:bg-slate-50">
              <div className="flex items-center justify-between px-2 py-1.5">
                <button
                  onClick={() => setExpanded(expanded === wh.id ? null : wh.id)}
                  className="flex items-center gap-1.5 text-sm text-left min-w-0 flex-1"
                >
                  {expanded === wh.id ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                  <span className="truncate">{wh.name}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded flex-shrink-0 ${wh.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-200 text-slate-500'}`}>
                    {wh.is_active ? 'active' : 'paused'}
                  </span>
                </button>
                {isOrgAdmin && (
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => toggleMutation.mutate({ id: wh.id, is_active: !wh.is_active })}
                      className="text-xs text-slate-500 hover:text-slate-900"
                    >
                      {wh.is_active ? 'Pause' : 'Resume'}
                    </button>
                    <button onClick={() => deleteMutation.mutate(wh.id)} className="text-slate-400 hover:text-red-600">
                      <Trash2 size={13} />
                    </button>
                  </div>
                )}
              </div>
              {expanded === wh.id && <DeliveryLog orgSlug={orgSlug} webhookId={wh.id} />}
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

// ── Members & invitations tab ──────────────────────────────────────────────

const ORG_ROLES = ['admin', 'member', 'guest']
const WORKSPACE_ROLES = ['admin', 'member', 'viewer']

function MembersTab({ orgSlug, workspaceSlug, isOrgAdmin, isWorkspaceAdmin, currentUserId }) {
  const queryClient = useQueryClient()
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')
  const [addUserId, setAddUserId] = useState('')
  const [addRole, setAddRole] = useState('member')

  const { data: orgMembers } = useQuery({
    queryKey: ['org-members', orgSlug],
    queryFn: () => listOrgMembers(orgSlug).then((r) => r.data),
  })

  const { data: wsMembers } = useQuery({
    queryKey: ['members', orgSlug, workspaceSlug],
    queryFn: () => listWorkspaceMembers(orgSlug, workspaceSlug).then((r) => r.data),
  })

  const { data: invitations } = useQuery({
    queryKey: ['invitations', orgSlug],
    queryFn: () => listInvitations(orgSlug).then((r) => r.data),
    enabled: isOrgAdmin,
  })

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }) => changeOrgMemberRole(orgSlug, userId, role),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['org-members', orgSlug] }),
  })

  const inviteMutation = useMutation({
    mutationFn: () => createInvitation(orgSlug, inviteEmail, inviteRole),
    onSuccess: () => { setInviteEmail(''); queryClient.invalidateQueries({ queryKey: ['invitations', orgSlug] }) },
  })

  const cancelMutation = useMutation({
    mutationFn: (id) => cancelInvitation(orgSlug, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['invitations', orgSlug] }),
  })

  const addMemberMutation = useMutation({
    mutationFn: () => addWorkspaceMember(orgSlug, workspaceSlug, addUserId, addRole),
    onSuccess: () => { setAddUserId(''); queryClient.invalidateQueries({ queryKey: ['members', orgSlug, workspaceSlug] }) },
  })

  const wsMemberIds = new Set((wsMembers || []).map((m) => m.user_id))
  const availableToAdd = (orgMembers || []).filter((m) => !wsMemberIds.has(m.user_id))

  return (
    <div className="max-w-lg space-y-4">
      {/* Organization members */}
      <Card>
        <h3 className="text-sm font-semibold text-slate-800 mb-3">Organization members</h3>
        {!isOrgAdmin && <AdminNotice scope="organization owner or admin" />}
        <div className="space-y-1.5">
          {(orgMembers || []).map((m) => (
            <div key={m.id} className="flex items-center justify-between text-sm px-2 py-1.5 rounded-lg hover:bg-slate-50">
              <span className="truncate">{m.full_name || m.username} <span className="text-slate-400 text-xs">{m.email}</span></span>
              {isOrgAdmin && m.role !== 'owner' ? (
                <select
                  value={m.role}
                  onChange={(e) => roleMutation.mutate({ userId: m.user_id, role: e.target.value })}
                  className="text-xs border border-slate-200 rounded-lg px-1.5 py-1 flex-shrink-0"
                >
                  {ORG_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              ) : (
                <span className="text-xs text-slate-400 flex-shrink-0">{m.role}</span>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Invitations */}
      {isOrgAdmin && (
        <Card>
          <h3 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-1.5"><Mail size={14} /> Invitations</h3>
          <form
            onSubmit={(e) => { e.preventDefault(); if (inviteEmail.trim()) inviteMutation.mutate() }}
            className="flex items-center gap-2 mb-3"
          >
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="email@example.com"
              className="flex-1 text-sm border border-slate-200 rounded-lg px-3 py-1.5"
            />
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="text-sm border border-slate-200 rounded-lg px-2 py-1.5"
            >
              {ORG_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            <button
              type="submit"
              disabled={!inviteEmail.trim()}
              className="p-2 bg-slate-900 text-white rounded-lg disabled:opacity-40"
            >
              <Plus size={14} />
            </button>
          </form>
          <div className="space-y-1.5">
            {(invitations || []).filter((i) => !i.accepted_at).length === 0 && (
              <p className="text-sm text-slate-400">No pending invitations.</p>
            )}
            {(invitations || []).filter((i) => !i.accepted_at).map((inv) => (
              <div key={inv.id} className="flex items-center justify-between text-sm px-2 py-1.5 rounded-lg hover:bg-slate-50">
                <span className="truncate">{inv.email} <span className="text-slate-400 text-xs">({inv.role})</span></span>
                <button onClick={() => cancelMutation.mutate(inv.id)} className="text-slate-400 hover:text-red-600 flex-shrink-0">
                  <X size={13} />
                </button>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Workspace members */}
      <Card>
        <h3 className="text-sm font-semibold text-slate-800 mb-3">Workspace members</h3>
        {!isWorkspaceAdmin && <AdminNotice />}
        <div className="space-y-1.5 mb-3">
          {(wsMembers || []).map((m) => (
            <div key={m.id} className="flex items-center justify-between text-sm px-2 py-1.5 rounded-lg hover:bg-slate-50">
              <span className="truncate">{m.full_name || m.username}</span>
              <span className="text-xs text-slate-400 flex-shrink-0">{m.role}</span>
            </div>
          ))}
        </div>

        {isWorkspaceAdmin && availableToAdd.length > 0 && (
          <form
            onSubmit={(e) => { e.preventDefault(); if (addUserId) addMemberMutation.mutate() }}
            className="flex items-center gap-2 pt-3 border-t border-slate-100"
          >
            <select
              value={addUserId}
              onChange={(e) => setAddUserId(e.target.value)}
              className="flex-1 text-sm border border-slate-200 rounded-lg px-2 py-1.5"
            >
              <option value="">Add org member to this workspace...</option>
              {availableToAdd.map((m) => (
                <option key={m.user_id} value={m.user_id}>{m.full_name || m.username}</option>
              ))}
            </select>
            <select
              value={addRole}
              onChange={(e) => setAddRole(e.target.value)}
              className="text-sm border border-slate-200 rounded-lg px-2 py-1.5"
            >
              {WORKSPACE_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            <button
              type="submit"
              disabled={!addUserId}
              className="p-2 bg-slate-900 text-white rounded-lg disabled:opacity-40"
            >
              <Plus size={14} />
            </button>
          </form>
        )}
      </Card>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────

export default function Settings() {
  const { user } = useAuth()
  const { currentOrg, currentWorkspace, refreshWorkspaces } = useWorkspace()
  const [tab, setTab] = useState('Workspace')

  const orgSlug = currentOrg?.slug
  const workspaceSlug = currentWorkspace?.slug

  const { data: orgMembers } = useQuery({
    queryKey: ['org-members', orgSlug],
    queryFn: () => listOrgMembers(orgSlug).then((r) => r.data),
    enabled: !!orgSlug,
  })

  const { data: wsMembers } = useQuery({
    queryKey: ['members', orgSlug, workspaceSlug],
    queryFn: () => listWorkspaceMembers(orgSlug, workspaceSlug).then((r) => r.data),
    enabled: !!orgSlug && !!workspaceSlug,
  })

  if (!currentWorkspace) {
    return <div className="p-6 text-slate-500 text-sm">Select a workspace to view settings.</div>
  }

  const isOrgAdmin = ['owner', 'admin'].includes((orgMembers || []).find((m) => m.user_id === user?.id)?.role)
  const isWorkspaceAdmin = (wsMembers || []).find((m) => m.user_id === user?.id)?.role === 'admin'

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold text-slate-900 mb-4">Settings</h1>

      <div className="flex items-center gap-1 border-b border-slate-200 mb-6">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`text-sm px-3 py-2 border-b-2 -mb-px transition-colors ${
              tab === t ? 'border-slate-900 text-slate-900 font-medium' : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Workspace' && (
        <WorkspaceTab
          orgSlug={orgSlug}
          workspace={currentWorkspace}
          isAdmin={isWorkspaceAdmin}
          onArchived={() => refreshWorkspaces()}
        />
      )}
      {tab === 'Labels' && <LabelsTab orgSlug={orgSlug} workspaceSlug={workspaceSlug} isAdmin={isWorkspaceAdmin} />}
      {tab === 'Custom fields' && <CustomFieldsTab orgSlug={orgSlug} workspaceSlug={workspaceSlug} isAdmin={isWorkspaceAdmin} />}
      {tab === 'Webhooks' && <WebhooksTab orgSlug={orgSlug} isOrgAdmin={isOrgAdmin} />}
      {tab === 'Members' && (
        <MembersTab
          orgSlug={orgSlug}
          workspaceSlug={workspaceSlug}
          isOrgAdmin={isOrgAdmin}
          isWorkspaceAdmin={isWorkspaceAdmin}
          currentUserId={user?.id}
        />
      )}
    </div>
  )
}