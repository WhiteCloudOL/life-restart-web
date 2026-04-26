import request from '@/api/request';
import type {
  AdminUser,
  CreateAdminUserPayload,
  PaginatedUsersResponse,
  UpdateAdminUserPayload,
} from '@/types/admin';

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

export const createAdminUser = async (payload: CreateAdminUserPayload): Promise<AdminUser> => {
  const { data } = await request.post<AdminUser>('/admin/users', payload);
  return data;
};

export const updateAdminUser = async (
  userId: number,
  payload: UpdateAdminUserPayload,
): Promise<AdminUser> => {
  const { data } = await request.patch<AdminUser>(`/admin/users/${userId}`, payload);
  return data;
};

export const deleteAdminUser = async (userId: number): Promise<void> => {
  await request.delete(`/admin/users/${userId}`);
};
