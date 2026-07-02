import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { X, AlertTriangle, Clock, User, Calendar, Lock } from 'lucide-react'
import { getTask, updateTask } from '../api/tasks'
import { getTaskActivity } from '../api/activities'
import { isOverdue, overdueDays } from '../utils/taskDates'
import { useAuth } from '../context/AuthContext'

const STATUS_OPTIONS = [
  { value: 'todo', label: 'Todo' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'in_review', label: 'In review' },
  { value: 'done', label: 'Done' },
  { value: 'cancelled', label: 'Cancelled' },
]

const PRIORITY_OPTIONS = ['urgent', 'high', 'medium', 'low', 'none']

function fieldLabel(key) {
  const labels = {
    title: 'Title',
    description: 'Description',
    status: 'Status',
    priority: 'Priority',
    assignee_id: 'Assignee',
    due_date: 'Due date',
  }
  return labels[key] || key
}

function formatValue(key, value, memberName) {
  if (value === null || value === undefined) return 'none'
  if (key === 'due_date') return new Date(value).toLocaleDateString()
  if (key === 'assignee_id') return memberName ? memberName(value) : value
  return String(value).replace('_', ' ')
}

export default function TaskDetailModal({ task, orgSlug, workspaceSlug, members = [], onClose }) {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [description, setDescription] = useState(task.description || '')
  const [permissionError, setPermissionError] = useState('')

  const currentMember = members.find((m) => m.user_id === user?.id)
  const isAdmin = currentMember?.role === 'admin'

  const { data: liveTask } = useQuery({
    queryKey: ['task', orgSlug, workspaceSlug, task.id],
    queryFn: () => getTask(orgSlug, workspaceSlug, task.id).then((r) => r.data),
    initialData: task,
  })

  const { data: activityData, isLoading: activityLoading } = useQuery({
    queryKey: ['task-activity', orgSlug, workspaceSlug, task.id],
    queryFn: () => getTaskActivity(orgSlug, workspaceSlug, task.id).then((r) => r.data),
  })

  useEffect(() => {
    setDescription(liveTask?.description || '')
  }, [liveTask?.id, liveTask?.description])

  const patchMutation = useMutation({
    mutationFn: (patch) => updateTask(orgSlug, workspaceSlug, task.id, patch),
    onSuccess: () => {
      setPermissionError('')
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      queryClient.invalidateQueries({ queryKey: ['task', orgSlug, workspaceSlug, task.id] })
      queryClient.invalidateQueries({ queryKey: ['task-activity', orgSlug, workspaceSlug, task.id] })
    },
    onError: (error) => {
      if (error.response?.status === 403) {
        setPermissionError(error.response.data?.detail || 'You do not have permission to do that.')
      }
    },
  })

  const t = liveTask || task
  const overdue = isOverdue(t)
  const days = overdueDays(t)
  const activities = activityData?.items || []

  const memberName = (userId) => {
    const m = members.find((mem) => mem.user_id === userId)
    return m?.full_name || m?.username || 'Unknown'
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl w-full max-w-lg max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-slate-100">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-slate-900 truncate">{t.title}</h2>
            <p className="text-xs text-slate-400 mt-1">
              Created {new Date(t.created_at).toLocaleString()} · Updated {new Date(t.updated_at).toLocaleString()}
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 flex-shrink-0 ml-3">
            <X size={18} />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-4 space-y-5">
          {permissionError && (
            <div className="flex items-center gap-2 bg-red-50 text-red-700 text-sm font-medium px-3 py-2 rounded-lg">
              <Lock size={15} />
              {permissionError}
            </div>
          )}

          {overdue && (
            <div className="flex items-center gap-2 bg-red-50 text-red-700 text-sm font-medium px-3 py-2 rounded-lg">
              <AlertTriangle size={15} />
              Overdue by {days} {days === 1 ? 'day' : 'days'} — was due {new Date(t.due_date).toLocaleDateString()}
            </div>
          )}

          {t.completed_at && (
            <div className="flex items-center gap-2 bg-green-50 text-green-700 text-sm font-medium px-3 py-2 rounded-lg">
              <Clock size={15} />
              Completed on {new Date(t.completed_at).toLocaleString()}
            </div>
          )}

          {/* Editable fields */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-500">Status</label>
              <select
                value={t.status}
                onChange={(e) => patchMutation.mutate({ status: e.target.value })}
                className="mt-1 w-full text-sm border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-slate-900"
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-500">Priority</label>
              <select
                value={t.priority}
                onChange={(e) => patchMutation.mutate({ priority: e.target.value })}
                className="mt-1 w-full text-sm border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-slate-900"
              >
                {PRIORITY_OPTIONS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-500 flex items-center gap-1">
                <Calendar size={12} /> Due date
                {!isAdmin && <Lock size={11} className="text-slate-400" />}
              </label>
              <input
                type="date"
                value={t.due_date ? t.due_date.slice(0, 10) : ''}
                disabled={!isAdmin}
                title={!isAdmin ? 'Only workspace admins can change the due date' : undefined}
                onChange={(e) => {
                  if (!isAdmin) return
                  patchMutation.mutate({ due_date: e.target.value || null })
                }}
                className={`mt-1 w-full text-sm border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-slate-900 ${
                  !isAdmin ? 'bg-slate-50 text-slate-400 cursor-not-allowed' : ''
                }`}
              />
            </div>

            {members.length > 0 && (
              <div>
                <label className="text-xs font-medium text-slate-500 flex items-center gap-1">
                  <User size={12} /> Assignee
                </label>
                <select
                  value={t.assignee_id || ''}
                  onChange={(e) => patchMutation.mutate({ assignee_id: e.target.value || null })}
                  className="mt-1 w-full text-sm border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-slate-900"
                >
                  <option value="">Unassigned</option>
                  {members.map((m) => (
                    <option key={m.user_id} value={m.user_id}>{m.full_name || m.username}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="text-xs font-medium text-slate-500">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              onBlur={() => {
                if (description !== (t.description || '')) {
                  patchMutation.mutate({ description })
                }
              }}
              rows={3}
              placeholder="No description"
              className="mt-1 w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>

          {/* Activity / audit history */}
          <div>
            <h3 className="text-xs font-medium text-slate-500 mb-2">History</h3>
            {activityLoading ? (
              <p className="text-sm text-slate-400">Loading history...</p>
            ) : activities.length === 0 ? (
              <p className="text-sm text-slate-400">No activity recorded yet.</p>
            ) : (
              <ul className="space-y-2">
                {activities.map((a) => (
                  <li key={a.id} className="text-xs text-slate-600 border-l-2 border-slate-200 pl-2.5">
                    <span className="font-medium text-slate-800">{memberName(a.actor_id)}</span>{' '}
                    {a.action === 'created' && 'created this task'}
                    {a.action === 'archived' && 'deleted this task'}
                    {a.action === 'updated' && a.new_value && (
                      <>
                        updated{' '}
                        {Object.keys(a.new_value).map((key, i) => (
                          <span key={key}>
                            {i > 0 && ', '}
                            {fieldLabel(key).toLowerCase()} from{' '}
                            <span className="italic">{formatValue(key, a.old_value?.[key], memberName)}</span> to{' '}
                            <span className="italic">{formatValue(key, a.new_value[key], memberName)}</span>
                          </span>
                        ))}
                      </>
                    )}
                    <div className="text-slate-400 mt-0.5">{new Date(a.created_at).toLocaleString()}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}