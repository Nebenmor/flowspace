import api from './axios'

const wsBase = (orgSlug, workspaceSlug) =>
  `/organizations/${orgSlug}/workspaces/${workspaceSlug}/custom-fields`

const taskBase = (orgSlug, workspaceSlug, taskId) =>
  `/organizations/${orgSlug}/workspaces/${workspaceSlug}/tasks/${taskId}/custom-fields`

export const listCustomFields = (orgSlug, workspaceSlug) =>
  api.get(wsBase(orgSlug, workspaceSlug))

export const createCustomField = (orgSlug, workspaceSlug, data) =>
  api.post(wsBase(orgSlug, workspaceSlug), data)

export const deleteCustomField = (orgSlug, workspaceSlug, fieldId) =>
  api.delete(`${wsBase(orgSlug, workspaceSlug)}/${fieldId}`)

export const listTaskCustomFieldValues = (orgSlug, workspaceSlug, taskId) =>
  api.get(taskBase(orgSlug, workspaceSlug, taskId))

export const setCustomFieldValue = (orgSlug, workspaceSlug, taskId, fieldId, value) =>
  api.put(`${taskBase(orgSlug, workspaceSlug, taskId)}/${fieldId}`, { value })