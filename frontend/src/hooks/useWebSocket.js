import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

export default function useWebSocket(orgSlug, workspaceSlug) {
  const queryClient = useQueryClient()
  const wsRef = useRef(null)

  useEffect(() => {
    if (!orgSlug || !workspaceSlug) return

    const token = localStorage.getItem('access_token')
    if (!token) return

    // Backend route is /ws/{org_slug}/{workspace_slug} — not the workspace id.
    // Connect via the current origin so Vite's dev proxy (see vite.config.js)
    // forwards it to the API instead of hardcoding the backend port.
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(
      `${protocol}//${window.location.host}/ws/${orgSlug}/${workspaceSlug}?token=${token}`
    )
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        const taskEvents = ['task.created', 'task.updated', 'task.deleted']
        if (taskEvents.includes(message.event)) {
          // Invalidate task queries so the list refreshes automatically
          queryClient.invalidateQueries({ queryKey: ['tasks'] })
        }
      } catch (e) {
        // ignore malformed messages
      }
    }

    ws.onerror = () => {
      // fail silently — WebSocket is an enhancement, not a requirement
    }

    return () => {
      ws.close()
    }
  }, [orgSlug, workspaceSlug, queryClient])

  return wsRef
}