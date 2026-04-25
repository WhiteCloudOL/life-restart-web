import request from '@/api/request';
import type { GameHistorySession } from '@/types/game';
import type { UpdateMePayload, UserProfile } from '@/types/user';

export const fetchMe = async (): Promise<UserProfile> => {
  const { data } = await request.get<UserProfile>('/user/me');
  return data;
};

export const updateMe = async (payload: UpdateMePayload): Promise<UserProfile> => {
  const { data } = await request.put<UserProfile>('/user/me', payload);
  return data;
};

export const fetchMyHistory = async (): Promise<GameHistorySession[]> => {
  const { data } = await request.get<GameHistorySession[]>('/user/history');
  return data;
};

