import api from './axios'

export const getTaskActivity = (orgSlug, workspaceSlug, taskId, params = {}) => {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '' && value !== null) {
      query.append(key, value)
    }
  })
  return api.get(
    `/organizations/${orgSlug}/workspaces/${workspaceSlug}/tasks/${taskId}/activity?${query}`
  )
}