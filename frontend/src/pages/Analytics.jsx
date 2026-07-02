import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid,
} from 'recharts'
import { useWorkspace } from '../context/WorkspaceContext'
import {
  getTasksSummary,
  getCompletedOverTime,
  getTeamProductivity,
  getTimeToCompletion,
} from '../api/analytics'

function StatCard({ label, value, sub }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-semibold text-slate-900 mt-1">{value ?? '—'}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  )
}

export default function Analytics() {
  const { currentOrg, currentWorkspace } = useWorkspace()
  const orgSlug = currentOrg?.slug
  const workspaceSlug = currentWorkspace?.slug
  const enabled = !!orgSlug && !!workspaceSlug

  const { data: summary } = useQuery({
    queryKey: ['analytics-summary', orgSlug, workspaceSlug],
    queryFn: () => getTasksSummary(orgSlug, workspaceSlug).then((r) => r.data),
    enabled,
  })

  const { data: overTime } = useQuery({
    queryKey: ['analytics-over-time', orgSlug, workspaceSlug],
    queryFn: () => getCompletedOverTime(orgSlug, workspaceSlug, 90).then((r) => r.data),
    enabled,
  })

  const { data: productivity } = useQuery({
    queryKey: ['analytics-productivity', orgSlug, workspaceSlug],
    queryFn: () => getTeamProductivity(orgSlug, workspaceSlug).then((r) => r.data),
    enabled,
  })

  const { data: timeToCompletion } = useQuery({
    queryKey: ['analytics-ttc', orgSlug, workspaceSlug],
    queryFn: () => getTimeToCompletion(orgSlug, workspaceSlug).then((r) => r.data),
    enabled,
  })

  if (!currentWorkspace) {
    return <div className="p-6 text-slate-500 text-sm">Select a workspace to view analytics.</div>
  }

  return (
    <div className="p-6 max-w-5xl space-y-8">
      <h1 className="text-xl font-semibold text-slate-900">Analytics</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard label="Total" value={summary?.total} />
        <StatCard label="Completed" value={summary?.completed} />
        <StatCard label="In progress" value={summary?.in_progress} />
        <StatCard label="Todo" value={summary?.todo} />
        <StatCard label="Overdue" value={summary?.overdue} />
        <StatCard label="Completion" value={summary ? `${summary.completion_rate}%` : null} />
      </div>

      {/* Completed over time */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="text-sm font-medium text-slate-700 mb-4">Tasks completed over time (last 90 days)</h2>
        {overTime?.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={overTime}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(d) => d.slice(5)} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="completed" stroke="#0f172a" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-slate-400">No completion data for this period.</p>
        )}
      </div>

      {/* Team productivity */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="text-sm font-medium text-slate-700 mb-4">Team productivity</h2>
        {productivity?.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={productivity}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="username" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="completed_tasks" name="Completed" fill="#0f172a" radius={[4, 4, 0, 0]} />
              <Bar dataKey="open_tasks" name="Open" fill="#cbd5e1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-slate-400">No assignment data yet.</p>
        )}
      </div>

      {/* Time to completion */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="text-sm font-medium text-slate-700 mb-4">Avg. time to completion by priority</h2>
        {timeToCompletion?.length > 0 ? (
          <div className="space-y-3">
            {timeToCompletion.map((row) => (
              <div key={row.priority} className="flex items-center justify-between text-sm">
                <span className="capitalize text-slate-700 w-20">{row.priority}</span>
                <div className="flex-1 mx-4 bg-slate-100 rounded-full h-2">
                  <div
                    className="bg-slate-900 h-2 rounded-full"
                    style={{ width: `${Math.min((row.avg_hours / 240) * 100, 100)}%` }}
                  />
                </div>
                <span className="text-slate-500 w-24 text-right">{row.avg_hours}h avg</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400">No completed tasks to analyze yet.</p>
        )}
      </div>
    </div>
  )
}