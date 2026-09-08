import { ApiClient } from './client';
import type { AuthTokens, User } from '../types';

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  name: string;
}

export const authApi = {
  login: (payload: LoginPayload) => ApiClient.post<AuthTokens>('/api/v1/auth/login', payload),
  register: (payload: RegisterPayload) => ApiClient.post<AuthTokens>('/api/v1/auth/register', payload),
  getMe: () => ApiClient.get<User>('/api/v1/auth/me'),
  logout: () => {
    ApiClient.clearTokens();
    return Promise.resolve();
  },
};
