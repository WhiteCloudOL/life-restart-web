import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { login as loginApi } from '@/api/auth';
import { fetchMe, updateMe } from '@/api/user';
import { ACCESS_TOKEN_KEY } from '@/constants/storage';
import type { LoginPayload } from '@/types/auth';
import type { UpdateMePayload, UserProfile } from '@/types/user';

export interface AuthUser {
  user_id: number;
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

const toAuthUser = (profile: UserProfile): AuthUser => ({
  user_id: profile.id,
  username: profile.username,
  nickname: profile.nickname,
  api_mode: profile.api_mode,
  world_entry_limit: profile.world_entry_limit,
  world_entries_used_today: profile.world_entries_used_today,
  model_call_limit: profile.model_call_limit,
  model_calls_used_today: profile.model_calls_used_today,
  is_admin: profile.is_admin,
  has_custom_api_key: profile.has_custom_api_key,
  custom_model_name: profile.custom_model_name,
  custom_base_url: profile.custom_base_url,
  last_active_date: profile.last_active_date,
});

let hasUnauthorizedListener = false;

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(
    typeof window === 'undefined' ? null : window.localStorage.getItem(ACCESS_TOKEN_KEY),
  );
  const user = ref<AuthUser | null>(null);
  const isFetchingUser = ref<boolean>(false);
  const isLoggingIn = ref<boolean>(false);

  const isLoggedIn = computed<boolean>(() => Boolean(token.value));
  const quotaText = computed<string>(() => {
    if (!user.value) {
      return '未登录';
    }

    const isCustomUnlimited =
      user.value.api_mode === 'custom' &&
      user.value.has_custom_api_key &&
      Boolean(user.value.custom_model_name);
    if (isCustomUnlimited) {
      return '无限额度 (自定义 API 模式)';
    }

    const used = user.value.world_entries_used_today;
    const total = user.value.world_entry_limit;
    const callUsed = user.value.model_calls_used_today;
    const callTotal = user.value.model_call_limit;
    return `进入世界: ${Math.max(total - used, 0)}/${total} · 模型调用: ${Math.max(callTotal - callUsed, 0)}/${callTotal}`;
  });

  const setToken = (nextToken: string): void => {
    token.value = nextToken;
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(ACCESS_TOKEN_KEY, nextToken);
    }
  };

  const clearAuthState = (): void => {
    token.value = null;
    user.value = null;
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    }
  };

  const login = async (payload: LoginPayload): Promise<void> => {
    isLoggingIn.value = true;
    try {
      const data = await loginApi(payload);
      setToken(data.access_token);
      await fetchUserInfo();
    } finally {
      isLoggingIn.value = false;
    }
  };

  const logout = (): void => {
    clearAuthState();
  };

  const fetchUserInfo = async (): Promise<AuthUser | null> => {
    if (!token.value) {
      return null;
    }

    isFetchingUser.value = true;
    try {
      const profile = await fetchMe();
      user.value = toAuthUser(profile);
      return user.value;
    } catch (error) {
      clearAuthState();
      throw error;
    } finally {
      isFetchingUser.value = false;
    }
  };

  const updateUserInfo = async (payload: UpdateMePayload): Promise<AuthUser> => {
    const profile = await updateMe(payload);
    user.value = toAuthUser(profile);
    return user.value;
  };

  const syncQuota = (
    worldEntryLimit: number,
    worldEntriesUsedToday: number,
    modelCallLimit: number,
    modelCallsUsedToday: number,
  ): void => {
    if (!user.value) {
      return;
    }
    user.value.world_entry_limit = worldEntryLimit;
    user.value.world_entries_used_today = worldEntriesUsedToday;
    user.value.model_call_limit = modelCallLimit;
    user.value.model_calls_used_today = modelCallsUsedToday;
  };

  const syncAdminManagedProfile = (
    nickname: string,
    isAdmin: boolean,
    worldEntryLimit: number,
    worldEntriesUsedToday: number,
    modelCallLimit: number,
    modelCallsUsedToday: number,
  ): void => {
    if (!user.value) {
      return;
    }
    user.value.nickname = nickname;
    user.value.is_admin = isAdmin;
    user.value.world_entry_limit = worldEntryLimit;
    user.value.world_entries_used_today = worldEntriesUsedToday;
    user.value.model_call_limit = modelCallLimit;
    user.value.model_calls_used_today = modelCallsUsedToday;
  };

  if (typeof window !== 'undefined' && !hasUnauthorizedListener) {
    window.addEventListener('auth:unauthorized', () => {
      clearAuthState();
    });
    hasUnauthorizedListener = true;
  }

  return {
    token,
    user,
    isLoggedIn,
    isFetchingUser,
    isLoggingIn,
    quotaText,
    login,
    logout,
    fetchUserInfo,
    updateUserInfo,
    syncQuota,
    syncAdminManagedProfile,
    clearAuthState,
  };
});
