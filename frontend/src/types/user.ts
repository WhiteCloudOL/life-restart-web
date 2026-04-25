export interface UserProfile {
  id: number;
  username: string;
  nickname: string;
  api_mode: 'default' | 'custom';
  world_entry_limit: number;
  world_entries_used_today: number;
  model_call_limit: number;
  model_calls_used_today: number;
  is_admin: boolean;
  has_custom_api_key: boolean;
  custom_model_name: string | null;
  custom_base_url: string | null;
  last_active_date: string;
}

export interface UpdateMePayload {
  nickname?: string;
  api_mode?: 'default' | 'custom';
  custom_api_key?: string | null;
  custom_model_name?: string | null;
  custom_base_url?: string | null;
}
