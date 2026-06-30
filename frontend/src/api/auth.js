import api from './axios'

export const login = (email, password) =>
  api.post('/auth/login', { email, password })

export const register = (email, username, full_name, password) =>
  api.post('/auth/register', { email, username, full_name, password })

export const getMe = () =>
  api.get('/auth/me')

export const refreshToken = (refresh_token) =>
  api.post('/auth/refresh', { refresh_token })