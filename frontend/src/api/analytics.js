import api from './axios'

const base = (orgSlug, workspaceSlug) =>
  `/organizations/${orgSlug}/workspaces/${workspaceSlug}/analytics`

export const getTasksSummary = (orgSlug, workspaceSlug) =>
  api.get(`${base(orgSlug, workspaceSlug)}/tasks-summary`)

export const getCompletedOverTime = (orgSlug, workspaceSlug, days = 30) =>
  api.get(`${base(orgSlug, workspaceSlug)}/completed-over-time?days=${days}`)

export const getTeamProductivity = (orgSlug, workspaceSlug) =>
  api.get(`${base(orgSlug, workspaceSlug)}/team-productivity`)

export const getTimeToCompletion = (orgSlug, workspaceSlug) =>
  api.get(`${base(orgSlug, workspaceSlug)}/time-to-completion`)