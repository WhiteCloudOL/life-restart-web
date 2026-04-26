export interface AdminUser {
  id: number;
  username: string;
  nickname: string;
  api_mode: 'default' | 'custom';
  is_admin: boolean;
  world_entry_limit: number;
  world_entries_used_today: number;
  model_call_limit: number;
  model_calls_used_today: number;
  last_active_date: string;
  has_custom_api_key: boolean;
}

export interface CreateAdminUserPayload {
  username: string;
  password: string;
  nickname?: string;
  is_admin: boolean;
}

export interface UpdateAdminUserPayload {
  nickname?: string;
  password?: string;
  is_admin?: boolean;
  world_entry_limit?: number;
  model_call_limit?: number;
  model_calls_used_today?: number;
}

export interface PaginatedUsersResponse {
  page: number;
  size: number;
  total: number;
  items: AdminUser[];
  next_page: number | null;
}
