import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, X, Calendar } from 'lucide-react'
import { useWorkspace } from '../context/WorkspaceContext'
import { listTasks, createTask, updateTask } from '../api/tasks'
import { listWorkspaceMembers } from '../api/workspaces'
import TaskFilters from '../components/TaskFilters'
import TaskCard from '../components/TaskCard'
import TaskDetailModal from '../components/TaskDetailModal'
import useWebSocket from '../hooks/useWebSocket'


export default function Tasks() {
  const { currentOrg, currentWorkspace } = useWorkspace()
  const [filters, setFilters] = useState({})
  const [showCreate, setShowCreate] = useState(false)
  const [selectedTask, setSelectedTask] = useState(null)
  const queryClient = useQueryClient()

  const orgSlug = currentOrg?.slug
  const workspaceSlug = currentWorkspace?.slug

  useWebSocket(orgSlug, workspaceSlug)

  const { data, isLoading } = useQuery({
    queryKey: ['tasks', orgSlug, workspaceSlug, filters],
    queryFn: () => listTasks(orgSlug, workspaceSlug, filters).then((res) => res.data),
    enabled: !!orgSlug && !!workspaceSlug,
  })

  const { data: members } = useQuery({
    queryKey: ['members', orgSlug, workspaceSlug],
    queryFn: () => listWorkspaceMembers(orgSlug, workspaceSlug).then((res) => res.data),
    enabled: !!orgSlug && !!workspaceSlug,
  })

  const statusMutation = useMutation({
    mutationFn: ({ taskId, status }) => updateTask(orgSlug, workspaceSlug, taskId, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  })

  const createMutation = useMutation({
    mutationFn: (data) => createTask(orgSlug, workspaceSlug, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      setShowCreate(false)
    },
  })

  if (!currentWorkspace) {
    return <div className="p-6 text-slate-500 text-sm">Select a workspace to view tasks.</div>
  }

  return (
    <div className="p-6 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-slate-900">Tasks</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-1.5 bg-slate-900 text-white text-sm font-medium px-3 py-2 rounded-lg hover:bg-slate-800"
        >
          <Plus size={16} />
          New task
        </button>
      </div>

      <TaskFilters filters={filters} onChange={setFilters} members={members || []} />

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading tasks...</p>
      ) : data?.items?.length === 0 ? (
        <p className="text-sm text-slate-500">No tasks found.</p>
      ) : (
        <div className="space-y-2">
          {data?.items?.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onStatusChange={(taskId, status) => statusMutation.mutate({ taskId, status })}
              onClick={(t) => setSelectedTask(t)}
            />
          ))}
        </div>
      )}

      {showCreate && (
        <CreateTaskModal
          onClose={() => setShowCreate(false)}
          onSubmit={(data) => createMutation.mutate(data)}
          loading={createMutation.isPending}
        />
      )}

      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          orgSlug={orgSlug}
          workspaceSlug={workspaceSlug}
          members={members || []}
          onClose={() => setSelectedTask(null)}
        />
      )}
    </div>
  )
}

function CreateTaskModal({ onClose, onSubmit, loading }) {
  const [form, setForm] = useState({ title: '', description: '', priority: 'medium', status: 'todo', due_date: '' })

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({ ...form, due_date: form.due_date || null })
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900">New task</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            required
            placeholder="Task title"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
          <textarea
            placeholder="Description (optional)"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={3}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
          <select
            value={form.priority}
            onChange={(e) => setForm({ ...form, priority: e.target.value })}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
          >
            <option value="low">Low priority</option>
            <option value="medium">Medium priority</option>
            <option value="high">High priority</option>
          </select>

          <div>
            <label className="text-xs font-medium text-slate-500 flex items-center gap-1 mb-1">
              <Calendar size={12} /> Due date (optional)
            </label>
            <input
              type="date"
              value={form.due_date}
              onChange={(e) => setForm({ ...form, due_date: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-slate-900 text-white text-sm font-medium py-2.5 rounded-lg hover:bg-slate-800 disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Create task'}
          </button>
        </form>
      </div>
    </div>
  )
}