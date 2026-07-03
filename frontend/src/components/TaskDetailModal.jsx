import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { X, AlertTriangle, Clock, User, Calendar, Lock, Tag, Plus, ListTree, Link2, Trash2, Check } from 'lucide-react'
import { getTask, updateTask, listTasks } from '../api/tasks'
import { getTaskActivity } from '../api/activities'
import { listLabels, listTaskLabels, addTaskLabel, removeTaskLabel } from '../api/labels'
import { listCustomFields, listTaskCustomFieldValues, setCustomFieldValue } from '../api/customFields'
import { listSubtasks, createSubtask } from '../api/subtasks'
import { listDependencies, addDependency, removeDependency } from '../api/dependencies'
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

function LabelsSection({ orgSlug, workspaceSlug, taskId, isAdmin }) {
  const queryClient = useQueryClient()
  const [showPicker, setShowPicker] = useState(false)

  const { data: allLabels } = useQuery({
    queryKey: ['labels', orgSlug, workspaceSlug],
    queryFn: () => listLabels(orgSlug, workspaceSlug).then((r) => r.data),
  })

  const { data: taskLabels } = useQuery({
    queryKey: ['task-labels', orgSlug, workspaceSlug, taskId],
    queryFn: () => listTaskLabels(orgSlug, workspaceSlug, taskId).then((r) => r.data),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['task-labels', orgSlug, workspaceSlug, taskId] })

  const addMutation = useMutation({
    mutationFn: (labelId) => addTaskLabel(orgSlug, workspaceSlug, taskId, labelId),
    onSuccess: invalidate,
  })
  const removeMutation = useMutation({
    mutationFn: (labelId) => removeTaskLabel(orgSlug, workspaceSlug, taskId, labelId),
    onSuccess: invalidate,
  })

  const attachedIds = new Set((taskLabels || []).map((l) => l.id))
  const available = (allLabels || []).filter((l) => !attachedIds.has(l.id))

  if (!isAdmin && (allLabels || []).length === 0) return null

  return (
    <div>
      <h3 className="text-xs font-medium text-slate-500 mb-2 flex items-center gap-1">
        <Tag size={12} /> Labels
      </h3>
      <div className="flex flex-wrap items-center gap-1.5">
        {(taskLabels || []).map((label) => (
          <span
            key={label.id}
            className="flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
            style={{ backgroundColor: `${label.color}22`, color: label.color }}
          >
            {label.name}
            <button onClick={() => removeMutation.mutate(label.id)} className="hover:opacity-70">
              <X size={10} />
            </button>
          </span>
        ))}

        <div className="relative">
          <button
            onClick={() => setShowPicker((s) => !s)}
            className="flex items-center gap-1 text-xs text-slate-500 border border-dashed border-slate-300 rounded-full px-2 py-0.5 hover:border-slate-400"
          >
            <Plus size={10} /> Add
          </button>
          {showPicker && (
            <div className="absolute z-10 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg py-1 w-40 max-h-40 overflow-y-auto">
              {available.length === 0 ? (
                <p className="text-xs text-slate-400 px-3 py-1.5">No more labels</p>
              ) : (
                available.map((label) => (
                  <button
                    key={label.id}
                    onClick={() => {
                      addMutation.mutate(label.id)
                      setShowPicker(false)
                    }}
                    className="w-full text-left text-xs px-3 py-1.5 hover:bg-slate-50 flex items-center gap-1.5"
                  >
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: label.color }} />
                    {label.name}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function CustomFieldInput({ field, value, onSave }) {
  const [local, setLocal] = useState(value ?? '')

  useEffect(() => setLocal(value ?? ''), [value])

  const commit = (v) => {
    if (v === '' || v === null || v === undefined) return
    onSave(v)
  }

  if (field.field_type === 'boolean') {
    return (
      <select
        value={local === true || local === 'true' ? 'true' : 'false'}
        onChange={(e) => { setLocal(e.target.value); commit(e.target.value === 'true') }}
        className="mt-1 w-full text-sm border border-slate-200 rounded-lg px-2.5 py-1.5"
      >
        <option value="false">No</option>
        <option value="true">Yes</option>
      </select>
    )
  }
  if (field.field_type === 'select') {
    return (
      <select
        value={local}
        onChange={(e) => { setLocal(e.target.value); commit(e.target.value) }}
        className="mt-1 w-full text-sm border border-slate-200 rounded-lg px-2.5 py-1.5"
      >
        <option value="">—</option>
        {(field.options || []).map((opt) => <option key={opt} value={opt}>{opt}</option>)}
      </select>
    )
  }
  return (
    <input
      type={field.field_type === 'number' ? 'number' : field.field_type === 'date' ? 'date' : 'text'}
      value={local}
      onChange={(e) => setLocal(e.target.value)}
      onBlur={() => commit(local)}
      className="mt-1 w-full text-sm border border-slate-200 rounded-lg px-2.5 py-1.5"
    />
  )
}

function CustomFieldsSection({ orgSlug, workspaceSlug, taskId }) {
  const queryClient = useQueryClient()

  const { data: fields } = useQuery({
    queryKey: ['custom-fields', orgSlug, workspaceSlug],
    queryFn: () => listCustomFields(orgSlug, workspaceSlug).then((r) => r.data),
  })

  const { data: values } = useQuery({
    queryKey: ['task-custom-field-values', orgSlug, workspaceSlug, taskId],
    queryFn: () => listTaskCustomFieldValues(orgSlug, workspaceSlug, taskId).then((r) => r.data),
  })

  const saveMutation = useMutation({
    mutationFn: ({ fieldId, value }) => setCustomFieldValue(orgSlug, workspaceSlug, taskId, fieldId, value),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['task-custom-field-values', orgSlug, workspaceSlug, taskId] }),
  })

  if (!fields || fields.length === 0) return null

  const valueFor = (fieldId) => values?.find((v) => v.field_id === fieldId)?.value

  return (
    <div>
      <h3 className="text-xs font-medium text-slate-500 mb-2">Custom fields</h3>
      <div className="grid grid-cols-2 gap-3">
        {fields.map((field) => (
          <div key={field.id}>
            <label className="text-xs font-medium text-slate-500">{field.name}</label>
            <CustomFieldInput
              field={field}
              value={valueFor(field.id)}
              onSave={(value) => saveMutation.mutate({ fieldId: field.id, value })}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

function SubtasksSection({ orgSlug, workspaceSlug, taskId }) {
  const queryClient = useQueryClient()
  const [newTitle, setNewTitle] = useState('')

  const { data: subtasks } = useQuery({
    queryKey: ['subtasks', orgSlug, workspaceSlug, taskId],
    queryFn: () => listSubtasks(orgSlug, workspaceSlug, taskId).then((r) => r.data),
  })

  const createMutation = useMutation({
    mutationFn: (title) => createSubtask(orgSlug, workspaceSlug, taskId, { title }),
    onSuccess: () => {
      setNewTitle('')
      queryClient.invalidateQueries({ queryKey: ['subtasks', orgSlug, workspaceSlug, taskId] })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: ({ subtaskId, status }) => updateTask(orgSlug, workspaceSlug, subtaskId, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['subtasks', orgSlug, workspaceSlug, taskId] }),
  })

  return (
    <div>
      <h3 className="text-xs font-medium text-slate-500 mb-2 flex items-center gap-1">
        <ListTree size={12} /> Subtasks
      </h3>
      <div className="space-y-1.5">
        {(subtasks || []).map((sub) => {
          const done = sub.status === 'done'
          return (
            <div key={sub.id} className="flex items-center gap-2 text-sm">
              <button
                onClick={() => toggleMutation.mutate({ subtaskId: sub.id, status: done ? 'todo' : 'done' })}
                className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
                  done ? 'bg-slate-900 border-slate-900 text-white' : 'border-slate-300'
                }`}
              >
                {done && <Check size={11} />}
              </button>
              <span className={done ? 'line-through text-slate-400' : 'text-slate-700'}>{sub.title}</span>
            </div>
          )
        })}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (newTitle.trim()) createMutation.mutate(newTitle.trim())
        }}
        className="flex items-center gap-1.5 mt-2"
      >
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="Add a subtask..."
          className="flex-1 text-sm border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-slate-900"
        />
        <button
          type="submit"
          disabled={!newTitle.trim() || createMutation.isPending}
          className="text-sm px-2.5 py-1.5 bg-slate-900 text-white rounded-lg disabled:opacity-40"
        >
          <Plus size={14} />
        </button>
      </form>
    </div>
  )
}

function DependencyRow({ orgSlug, workspaceSlug, dep, onRemove }) {
  const { data: depTask } = useQuery({
    queryKey: ['task', orgSlug, workspaceSlug, dep.depends_on_id],
    queryFn: () => getTask(orgSlug, workspaceSlug, dep.depends_on_id).then((r) => r.data),
    staleTime: 60_000,
  })

  return (
    <div className="flex items-center justify-between text-sm bg-slate-50 rounded-lg px-2.5 py-1.5">
      <span className="text-slate-700 truncate">
        {depTask?.title || 'Loading...'}
        <span className="text-slate-400 ml-1.5 text-xs">({dep.dependency_type.replace('_', ' ')})</span>
      </span>
      <button onClick={onRemove} className="text-slate-400 hover:text-red-600 flex-shrink-0">
        <Trash2 size={13} />
      </button>
    </div>
  )
}

function DependenciesSection({ orgSlug, workspaceSlug, taskId }) {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [showPicker, setShowPicker] = useState(false)

  const { data: dependencies } = useQuery({
    queryKey: ['dependencies', orgSlug, workspaceSlug, taskId],
    queryFn: () => listDependencies(orgSlug, workspaceSlug, taskId).then((r) => r.data),
  })

  const { data: searchResults } = useQuery({
    queryKey: ['task-search', orgSlug, workspaceSlug, search],
    queryFn: () => listTasks(orgSlug, workspaceSlug, { search, page_size: 8 }).then((r) => r.data),
    enabled: showPicker && search.trim().length > 1,
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['dependencies', orgSlug, workspaceSlug, taskId] })

  const addMutation = useMutation({
    mutationFn: (dependsOnId) => addDependency(orgSlug, workspaceSlug, taskId, dependsOnId),
    onSuccess: () => {
      invalidate()
      setShowPicker(false)
      setSearch('')
    },
  })

  const removeMutation = useMutation({
    mutationFn: (dependencyId) => removeDependency(orgSlug, workspaceSlug, taskId, dependencyId),
    onSuccess: invalidate,
  })

  const results = (searchResults?.items || []).filter((t) => t.id !== taskId)

  return (
    <div>
      <h3 className="text-xs font-medium text-slate-500 mb-2 flex items-center gap-1">
        <Link2 size={12} /> Depends on
      </h3>
      <div className="space-y-1.5">
        {(dependencies || []).length === 0 && !showPicker && (
          <p className="text-sm text-slate-400">No dependencies</p>
        )}
        {(dependencies || []).map((dep) => (
          <DependencyRow
            key={dep.id}
            orgSlug={orgSlug}
            workspaceSlug={workspaceSlug}
            dep={dep}
            onRemove={() => removeMutation.mutate(dep.id)}
          />
        ))}
      </div>

      {showPicker ? (
        <div className="mt-2 relative">
          <input
            autoFocus
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tasks..."
            className="w-full text-sm border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
          {search.trim().length > 1 && (
            <div className="absolute z-10 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg w-full max-h-40 overflow-y-auto">
              {results.length === 0 ? (
                <p className="text-xs text-slate-400 px-3 py-1.5">No matching tasks</p>
              ) : (
                results.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => addMutation.mutate(t.id)}
                    className="w-full text-left text-xs px-3 py-1.5 hover:bg-slate-50 truncate"
                  >
                    {t.title}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      ) : (
        <button
          onClick={() => setShowPicker(true)}
          className="flex items-center gap-1 text-xs text-slate-500 border border-dashed border-slate-300 rounded-full px-2 py-0.5 hover:border-slate-400 mt-1.5"
        >
          <Plus size={10} /> Add dependency
        </button>
      )}
    </div>
  )
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

          <LabelsSection orgSlug={orgSlug} workspaceSlug={workspaceSlug} taskId={t.id} isAdmin={isAdmin} />

          <CustomFieldsSection orgSlug={orgSlug} workspaceSlug={workspaceSlug} taskId={t.id} />

          <SubtasksSection orgSlug={orgSlug} workspaceSlug={workspaceSlug} taskId={t.id} />

          <DependenciesSection orgSlug={orgSlug} workspaceSlug={workspaceSlug} taskId={t.id} />

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