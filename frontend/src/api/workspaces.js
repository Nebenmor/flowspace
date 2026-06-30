import api from './axios'

export const listWorkspaces = (orgSlug) =>
  api.get(`/organizations/${orgSlug}/workspaces`)

export const getWorkspace = (orgSlug, workspaceSlug) =>
  api.get(`/organizations/${orgSlug}/workspaces/${workspaceSlug}`)

export const listWorkspaceMembers = (orgSlug, workspaceSlug) =>
  api.get(`/organizations/${orgSlug}/workspaces/${workspaceSlug}/members`)