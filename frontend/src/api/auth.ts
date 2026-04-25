import request from '@/api/request';
import type { AuthTokenResponse, LoginPayload, RegisterPayload } from '@/types/auth';
import type { UserProfile } from '@/types/user';

export const register = async (payload: RegisterPayload): Promise<UserProfile> => {
  const { data } = await request.post<UserProfile>('/auth/register', payload);
  return data;
};

export const login = async (payload: LoginPayload): Promise<AuthTokenResponse> => {
  const { data } = await request.post<AuthTokenResponse>('/auth/login', payload);
  return data;
};
