import api from './axios'

const wsBase = (orgSlug, workspaceSlug) =>
  `/organizations/${orgSlug}/workspaces/${workspaceSlug}/labels`

const taskBase = (orgSlug, workspaceSlug, taskId) =>
  `/organizations/${orgSlug}/workspaces/${workspaceSlug}/tasks/${taskId}/labels`

export const listLabels = (orgSlug, workspaceSlug) =>
  api.get(wsBase(orgSlug, workspaceSlug))

export const createLabel = (orgSlug, workspaceSlug, data) =>
  api.post(wsBase(orgSlug, workspaceSlug), data)

export const deleteLabel = (orgSlug, workspaceSlug, labelId) =>
  api.delete(`${wsBase(orgSlug, workspaceSlug)}/${labelId}`)

export const listTaskLabels = (orgSlug, workspaceSlug, taskId) =>
  api.get(taskBase(orgSlug, workspaceSlug, taskId))

export const addTaskLabel = (orgSlug, workspaceSlug, taskId, labelId) =>
  api.post(taskBase(orgSlug, workspaceSlug, taskId), { label_id: labelId })

export const removeTaskLabel = (orgSlug, workspaceSlug, taskId, labelId) =>
  api.delete(`${taskBase(orgSlug, workspaceSlug, taskId)}/${labelId}`)