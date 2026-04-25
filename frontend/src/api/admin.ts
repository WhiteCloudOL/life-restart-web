import request from '@/api/request';
import type { AdminUser, PaginatedUsersResponse } from '@/types/admin';

export const listUsersByPage = async (page: number, size = 10): Promise<PaginatedUsersResponse> => {
  const { data } = await request.get<PaginatedUsersResponse>('/admin/users', {
    params: { page, size },
  });
  return data;
};

export const updateUserQuota = async (
  userId: number,
  payload: {
    world_entry_limit?: number;
    model_call_limit?: number;
  },
): Promise<AdminUser> => {
  const { data } = await request.put<AdminUser>(`/admin/users/${userId}/quota`, {
    ...payload,
  });
  return data;
};
