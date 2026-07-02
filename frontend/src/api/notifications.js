import api from './axios'

export const listNotifications = (params = {}) => {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '' && value !== null) {
      query.append(key, value)
    }
  })
  return api.get(`/notifications?${query}`)
}

export const markAsRead = (notificationId) =>
  api.patch(`/notifications/${notificationId}/read`)

export const markAllAsRead = () =>
  api.patch('/notifications/read-all')

export const deleteNotification = (notificationId) =>
  api.delete(`/notifications/${notificationId}`)