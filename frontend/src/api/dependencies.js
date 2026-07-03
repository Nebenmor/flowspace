import api from './axios'

const base = (orgSlug, workspaceSlug, taskId) =>
  `/organizations/${orgSlug}/workspaces/${workspaceSlug}/tasks/${taskId}/dependencies`

export const listDependencies = (orgSlug, workspaceSlug, taskId) =>
  api.get(base(orgSlug, workspaceSlug, taskId))

export const addDependency = (orgSlug, workspaceSlug, taskId, dependsOnId, dependencyType = 'blocks') =>
  api.post(base(orgSlug, workspaceSlug, taskId), { depends_on_id: dependsOnId, dependency_type: dependencyType })

export const removeDependency = (orgSlug, workspaceSlug, taskId, dependencyId) =>
  api.delete(`${base(orgSlug, workspaceSlug, taskId)}/${dependencyId}`)