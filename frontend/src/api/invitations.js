import api from './axios'

const base = (orgSlug) => `/organizations/${orgSlug}/invitations`

export const listInvitations = (orgSlug) => api.get(base(orgSlug))

export const createInvitation = (orgSlug, email, role = 'member') =>
  api.post(base(orgSlug), { email, role })

export const cancelInvitation = (orgSlug, invitationId) =>
  api.delete(`${base(orgSlug)}/${invitationId}`)

export const acceptInvitation = (token) =>
  api.post(`/invitations/accept?token=${encodeURIComponent(token)}`)