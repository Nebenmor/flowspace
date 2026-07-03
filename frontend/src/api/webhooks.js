import api from './axios'

const base = (orgSlug) => `/organizations/${orgSlug}/webhooks`

export const listWebhooks = (orgSlug) => api.get(base(orgSlug))

export const createWebhook = (orgSlug, data) => api.post(base(orgSlug), data)

export const updateWebhook = (orgSlug, webhookId, data) =>
  api.patch(`${base(orgSlug)}/${webhookId}`, data)

export const deleteWebhook = (orgSlug, webhookId) =>
  api.delete(`${base(orgSlug)}/${webhookId}`)

export const listWebhookDeliveries = (orgSlug, webhookId) =>
  api.get(`${base(orgSlug)}/${webhookId}/deliveries`)