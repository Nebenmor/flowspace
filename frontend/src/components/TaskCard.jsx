import { Calendar, User, AlertTriangle } from 'lucide-react'
import { isOverdue, overdueDays } from '../utils/taskDates'

const PRIORITY_COLORS = {
  low: 'bg-slate-100 text-slate-600',
  medium: 'bg-amber-100 text-amber-700',
  high: 'bg-red-100 text-red-700',
}

const STATUS_COLORS = {
  todo: 'bg-slate-100 text-slate-600',
  in_progress: 'bg-blue-100 text-blue-700',
  in_review: 'bg-purple-100 text-purple-700',
  done: 'bg-green-100 text-green-700',
  cancelled: 'bg-slate-100 text-slate-400',
}

export default function TaskCard({ task, onStatusChange, onClick }) {
  const overdue = isOverdue(task)
  const days = overdueDays(task)

  return (
    <div
      onClick={() => onClick?.(task)}
      className="bg-white border border-slate-200 rounded-lg p-4 hover:border-slate-300 transition-colors cursor-pointer"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-slate-900 truncate">{task.title}</h3>
          {task.description && (
            <p className="text-xs text-slate-500 mt-1 line-clamp-2">{task.description}</p>
          )}
        </div>

        <select
          value={task.status}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => onStatusChange?.(task.id, e.target.value)}
          className={`text-xs font-medium px-2 py-1 rounded-md border-0 focus:outline-none flex-shrink-0 ${STATUS_COLORS[task.status]}`}
        >
          <option value="todo">Todo</option>
          <option value="in_progress">In progress</option>
          <option value="in_review">In review</option>
          <option value="done">Done</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      <div className="flex items-center gap-3 mt-3">
        <span className={`text-xs font-medium px-2 py-0.5 rounded-md ${PRIORITY_COLORS[task.priority]}`}>
          {task.priority}
        </span>

        {task.due_date && (
          <span className={`flex items-center gap-1 text-xs ${overdue ? 'text-red-600 font-medium' : 'text-slate-400'}`}>
            <Calendar size={12} />
            {new Date(task.due_date).toLocaleDateString()}
          </span>
        )}

        {overdue && (
          <span className="flex items-center gap-1 text-xs text-red-600 font-medium">
            <AlertTriangle size={12} />
            {days} {days === 1 ? 'day' : 'days'} overdue
          </span>
        )}

        {task.assignee_id && (
          <span className="flex items-center gap-1 text-xs text-slate-400">
            <User size={12} />
            Assigned
          </span>
        )}
      </div>
    </div>
  )
}