import api from './axios'

export const listOrganizations = () =>
  api.get('/organizations')

export const getOrganization = (orgSlug) =>
  api.get(`/organizations/${orgSlug}`)

export const createOrganization = (data) =>
  api.post('/organizations', data)

export const updateOrganization = (orgSlug, data) =>
  api.patch(`/organizations/${orgSlug}`, data)

export const listOrgMembers = (orgSlug) =>
  api.get(`/organizations/${orgSlug}/members`)

export const changeOrgMemberRole = (orgSlug, userId, role) =>
  api.patch(`/organizations/${orgSlug}/members/${userId}/role?role=${encodeURIComponent(role)}`)