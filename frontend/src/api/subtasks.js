import api from './axios'

const base = (orgSlug, workspaceSlug, taskId) =>
  `/organizations/${orgSlug}/workspaces/${workspaceSlug}/tasks/${taskId}/subtasks`

export const listSubtasks = (orgSlug, workspaceSlug, taskId) =>
  api.get(base(orgSlug, workspaceSlug, taskId))

export const createSubtask = (orgSlug, workspaceSlug, taskId, data) =>
  api.post(base(orgSlug, workspaceSlug, taskId), data)