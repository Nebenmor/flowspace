import api from './axios'

export const listWorkspaces = (orgSlug) =>
  api.get(`/organizations/${orgSlug}/workspaces`)

export const getWorkspace = (orgSlug, workspaceSlug) =>
  api.get(`/organizations/${orgSlug}/workspaces/${workspaceSlug}`)

export const createWorkspace = (orgSlug, data) =>
  api.post(`/organizations/${orgSlug}/workspaces`, data)

export const updateWorkspace = (orgSlug, workspaceSlug, data) =>
  api.patch(`/organizations/${orgSlug}/workspaces/${workspaceSlug}`, data)

export const archiveWorkspace = (orgSlug, workspaceSlug) =>
  api.delete(`/organizations/${orgSlug}/workspaces/${workspaceSlug}`)

export const listWorkspaceMembers = (orgSlug, workspaceSlug) =>
  api.get(`/organizations/${orgSlug}/workspaces/${workspaceSlug}/members`)

export const addWorkspaceMember = (orgSlug, workspaceSlug, userId, role = 'member') =>
  api.post(`/organizations/${orgSlug}/workspaces/${workspaceSlug}/members?user_id=${userId}&role=${encodeURIComponent(role)}`)