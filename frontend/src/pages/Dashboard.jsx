import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bell, CheckCircle, Clock, AlertCircle, ListTodo } from 'lucide-react'
import { useWorkspace } from '../context/WorkspaceContext'
import { useAuth } from '../context/AuthContext'
import { getTasksSummary } from '../api/analytics'
import { listTasks } from '../api/tasks'
import { listNotifications } from '../api/notifications'
import NotificationsPanel from '../components/NotificationsPanel'
import useWebSocket from '../hooks/useWebSocket'

const STATUS_COLORS = {
  todo: 'text-slate-500',
  in_progress: 'text-blue-600',
  in_review: 'text-purple-600',
  done: 'text-green-600',
  cancelled: 'text-slate-400',
}

const PRIORITY_BADGE = {
  low: 'bg-slate-100 text-slate-600',
  medium: 'bg-amber-100 text-amber-700',
  high: 'bg-red-100 text-red-700',
}

export default function Dashboard() {
  const { user } = useAuth()
  const { currentOrg, currentWorkspace } = useWorkspace()
  const [showNotifications, setShowNotifications] = useState(false)

  const orgSlug = currentOrg?.slug
  const workspaceSlug = currentWorkspace?.slug
  const enabled = !!orgSlug && !!workspaceSlug

  useWebSocket(orgSlug, workspaceSlug)

  const { data: summary } = useQuery({
    queryKey: ['analytics-summary', orgSlug, workspaceSlug],
    queryFn: () => getTasksSummary(orgSlug, workspaceSlug).then((r) => r.data),
    enabled,
  })

  const { data: tasksData } = useQuery({
    queryKey: ['tasks-recent', orgSlug, workspaceSlug],
    queryFn: () => listTasks(orgSlug, workspaceSlug, { page_size: 5 }).then((r) => r.data),
    enabled,
  })

  const { data: notifData } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => listNotifications().then((r) => r.data),
  })

  const notifications = notifData?.items || notifData || []
  const unreadCount = notifications.filter((n) => !n.is_read).length

  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 17) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div className="p-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            {greeting()}, {user?.full_name?.split(' ')[0] || user?.username} 👋
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {currentWorkspace?.name} · {currentOrg?.name}
          </p>
        </div>
        <button
          onClick={() => setShowNotifications(true)}
          className="relative p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
        >
          <Bell size={20} />
          {unreadCount > 0 && (
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
          )}
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <SummaryCard icon={<ListTodo size={18} />} label="Total tasks" value={summary?.total} color="bg-slate-50" />
        <SummaryCard icon={<CheckCircle size={18} className="text-green-600" />} label="Completed" value={summary?.completed} color="bg-green-50" />
        <SummaryCard icon={<Clock size={18} className="text-blue-600" />} label="In progress" value={summary?.in_progress} color="bg-blue-50" />
        <SummaryCard icon={<AlertCircle size={18} className="text-red-500" />} label="Overdue" value={summary?.overdue} color="bg-red-50" />
      </div>

      {/* Recent tasks */}
      <div className="bg-white border border-slate-200 rounded-xl">
        <div className="px-4 py-3 border-b border-slate-100">
          <h2 className="text-sm font-medium text-slate-700">Recent tasks</h2>
        </div>
        <ul className="divide-y divide-slate-100">
          {tasksData?.items?.length === 0 && (
            <li className="px-4 py-4 text-sm text-slate-400">No tasks yet.</li>
          )}
          {tasksData?.items?.map((task) => (
            <li key={task.id} className="flex items-center justify-between px-4 py-3 hover:bg-slate-50">
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-800 truncate">{task.title}</p>
                <p className={`text-xs mt-0.5 ${STATUS_COLORS[task.status]}`}>
                  {task.status.replace('_', ' ')}
                </p>
              </div>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-md flex-shrink-0 ml-3 ${PRIORITY_BADGE[task.priority]}`}>
                {task.priority}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {showNotifications && (
        <NotificationsPanel onClose={() => setShowNotifications(false)} />
      )}
    </div>
  )
}

function SummaryCard({ icon, label, value, color }) {
  return (
    <div className={`${color} border border-slate-200 rounded-xl p-4`}>
      <div className="flex items-center gap-2 text-slate-500 mb-2">
        {icon}
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className="text-2xl font-semibold text-slate-900">{value ?? '—'}</p>
    </div>
  )
}