import { Search } from 'lucide-react'

const STATUS_OPTIONS = ['todo', 'in_progress', 'in_review', 'done', 'cancelled']
const PRIORITY_OPTIONS = ['low', 'medium', 'high']

export default function TaskFilters({ filters, onChange, members = [] }) {
  const handleChange = (key, value) => {
    onChange({ ...filters, [key]: value })
  }

  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      <div className="relative flex-1 min-w-[200px] max-w-xs">
        <Search size={15} className="absolute left-2.5 top-2.5 text-slate-400" />
        <input
          type="text"
          placeholder="Search tasks..."
          value={filters.search || ''}
          onChange={(e) => handleChange('search', e.target.value)}
          className="w-full pl-8 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
        />
      </div>

      <select
        value={filters.status || ''}
        onChange={(e) => handleChange('status', e.target.value)}
        className="text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-900"
      >
        <option value="">All statuses</option>
        {STATUS_OPTIONS.map((s) => (
          <option key={s} value={s}>{s.replace('_', ' ')}</option>
        ))}
      </select>

      <select
        value={filters.priority || ''}
        onChange={(e) => handleChange('priority', e.target.value)}
        className="text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-900"
      >
        <option value="">All priorities</option>
        {PRIORITY_OPTIONS.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      {members.length > 0 && (
        <select
          value={filters.assignee_id || ''}
          onChange={(e) => handleChange('assignee_id', e.target.value)}
          className="text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-slate-900"
        >
          <option value="">All assignees</option>
          {members.map((m) => (
            <option key={m.user_id} value={m.user_id}>{m.full_name || m.username}</option>
          ))}
        </select>
      )}

      <label className="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer">
        <input
          type="checkbox"
          checked={filters.is_overdue || false}
          onChange={(e) => handleChange('is_overdue', e.target.checked || undefined)}
          className="rounded border-slate-300"
        />
        Overdue only
      </label>
    </div>
  )
}