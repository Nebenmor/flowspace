import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { X, Bell, CheckCheck } from 'lucide-react'
import { listNotifications, markAsRead, markAllAsRead } from '../api/notifications'

export default function NotificationsPanel({ onClose }) {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => listNotifications().then((r) => r.data),
  })

  const readMutation = useMutation({
    mutationFn: markAsRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  const readAllMutation = useMutation({
    mutationFn: markAllAsRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  const notifications = data?.items || data || []
  const unreadCount = notifications.filter((n) => !n.is_read).length

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />

      {/* Panel */}
      <div className="relative w-full max-w-sm bg-white shadow-xl flex flex-col h-full">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <Bell size={16} className="text-slate-600" />
            <h2 className="text-sm font-semibold text-slate-900">Notifications</h2>
            {unreadCount > 0 && (
              <span className="text-xs bg-slate-900 text-white px-1.5 py-0.5 rounded-full">
                {unreadCount}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {unreadCount > 0 && (
              <button
                onClick={() => readAllMutation.mutate()}
                className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1"
              >
                <CheckCheck size={13} />
                Mark all read
              </button>
            )}
            <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <p className="text-sm text-slate-400 p-4">Loading...</p>
          ) : notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2">
              <Bell size={32} className="opacity-30" />
              <p className="text-sm">No notifications yet</p>
            </div>
          ) : (
            <ul>
              {notifications.map((n) => (
                <li
                  key={n.id}
                  onClick={() => !n.is_read && readMutation.mutate(n.id)}
                  className={`px-4 py-3 border-b border-slate-100 cursor-pointer hover:bg-slate-50 transition-colors ${
                    !n.is_read ? 'bg-slate-50' : ''
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {!n.is_read && (
                      <span className="mt-1.5 w-2 h-2 rounded-full bg-slate-900 flex-shrink-0" />
                    )}
                    <div className={!n.is_read ? '' : 'ml-4'}>
                      <p className="text-sm font-medium text-slate-800">{n.title}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{n.body}</p>
                      <p className="text-xs text-slate-400 mt-1">
                        {new Date(n.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}