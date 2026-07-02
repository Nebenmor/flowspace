import api from './axios'

export const listTasks = (orgSlug, workspaceSlug, filters = {}) => {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '' && value !== null) {
      params.append(key, value)
    }
  })
  return api.get(`/organizations/${orgSlug}/workspaces/${workspaceSlug}/tasks?${params}`)
}

export const getTask = (orgSlug, workspaceSlug, taskId) =>
  api.get(`/organizations/${orgSlug}/workspaces/${workspaceSlug}/tasks/${taskId}`)

export const createTask = (orgSlug, workspaceSlug, data) =>
  api.post(`/organizations/${orgSlug}/workspaces/${workspaceSlug}/tasks`, data)

export const updateTask = (orgSlug, workspaceSlug, taskId, data) =>
  api.patch(`/organizations/${orgSlug}/workspaces/${workspaceSlug}/tasks/${taskId}`, data)

export const deleteTask = (orgSlug, workspaceSlug, taskId) =>
  api.delete(`/organizations/${orgSlug}/workspaces/${workspaceSlug}/tasks/${taskId}`)