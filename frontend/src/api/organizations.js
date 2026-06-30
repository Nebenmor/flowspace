import api from './axios'

export const listOrganizations = () =>
  api.get('/organizations')

export const getOrganization = (orgSlug) =>
  api.get(`/organizations/${orgSlug}`)