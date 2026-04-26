<script setup lang="ts">
import { reactive, ref, watch } from 'vue';
import BaseButton from '@/components/BaseButton.vue';
import BaseInput from '@/components/BaseInput.vue';
import { useAuthStore } from '@/stores/useAuthStore';

const authStore = useAuthStore();
const isSaving = ref<boolean>(false);
const errorMessage = ref<string>('');
const successMessage = ref<string>('');

const form = reactive({
  username: '',
  nickname: '',
  api_mode: 'default' as 'default' | 'custom',
  custom_model_name: '',
  custom_api_key: '',
  custom_base_url: '',
});

const isSyncingFromStore = ref<boolean>(false);
const hasUnsavedChanges = ref<boolean>(false);
const lastSyncedUserId = ref<number | null>(null);

const applyUserToForm = (user: NonNullable<typeof authStore.user>): void => {
  isSyncingFromStore.value = true;
  form.username = user.username;
  form.nickname = user.nickname ?? user.username;
  form.api_mode = user.api_mode ?? 'default';
  form.custom_model_name = user.custom_model_name ?? '';
  form.custom_base_url = user.custom_base_url ?? '';
  form.custom_api_key = '';
  lastSyncedUserId.value = user.user_id;
  hasUnsavedChanges.value = false;
  isSyncingFromStore.value = false;
};

watch(
  () => authStore.user,
  (user) => {
    if (!user) {
      return;
    }
    const isDifferentUser = lastSyncedUserId.value !== user.user_id;
    if (isDifferentUser || !hasUnsavedChanges.value) {
      applyUserToForm(user);
    }
  },
  { immediate: true },
);

watch(
  form,
  () => {
    if (isSyncingFromStore.value) {
      return;
    }
    hasUnsavedChanges.value = true;
  },
  { deep: true },
);

const onSave = async (): Promise<void> => {
  errorMessage.value = '';
  successMessage.value = '';
  const safeNickname = form.nickname.trim();
  if (!safeNickname) {
    errorMessage.value = '昵称不能为空';
    return;
  }
  if (safeNickname.length > 32) {
    errorMessage.value = '昵称长度不能超过 32 个字符';
    return;
  }

  isSaving.value = true;
  try {
    const payload: {
      nickname: string;
      api_mode: 'default' | 'custom';
      custom_model_name?: string | null;
      custom_api_key?: string | null;
      custom_base_url?: string | null;
    } = {
      nickname: safeNickname,
      api_mode: form.api_mode,
      custom_model_name: form.custom_model_name.trim() || null,
      custom_base_url: form.custom_base_url.trim() || null,
    };

    if (form.custom_api_key.trim()) {
      payload.custom_api_key = form.custom_api_key.trim();
    }

    const updatedUser = await authStore.updateUserInfo({
      ...payload,
    });
    applyUserToForm(updatedUser);
    successMessage.value = '设置已更新';
  } catch (error) {
    const message = (error as { message?: string }).message;
    errorMessage.value = message ?? '保存失败，请稍后重试';
  } finally {
    isSaving.value = false;
  }
};
</script>

<template>
  <section class="px-4 pb-16 pt-6 lg:pt-10">
    <div
      class="mx-auto w-full max-w-4xl rounded-[2rem] border border-zinc-200/60 bg-white/90 p-8 shadow-[0_24px_80px_rgba(24,24,27,0.07)] ring-1 ring-zinc-900/5 backdrop-blur-2xl lg:p-10"
    >
      <div class="mb-8">
        <p class="text-xs font-semibold uppercase tracking-[0.28em] text-zinc-500">Profile Settings</p>
        <h1 class="mt-4 text-3xl font-bold tracking-tight text-zinc-900">个人设置</h1>
        <p class="mt-3 max-w-2xl text-sm leading-7 text-zinc-500">
          用户名不可修改。你可以更新昵称，并在默认 API 与自定义 API 模式之间切换。
        </p>
      </div>

      <form class="grid gap-6" @submit.prevent="onSave">
        <div class="grid gap-5 lg:grid-cols-2">
          <BaseInput v-model="form.username" label="用户名（不可修改）" autocomplete="username" disabled />
          <BaseInput v-model="form.nickname" label="昵称" autocomplete="nickname" placeholder="用于展示的昵称" />
        </div>

        <fieldset class="rounded-[1.5rem] border border-zinc-200/60 bg-zinc-50/70 p-5 ring-1 ring-zinc-900/5">
          <legend class="px-2 text-sm font-medium text-zinc-500">调用模式</legend>
          <div class="mt-3 grid gap-3 sm:grid-cols-2">
            <label
              class="flex cursor-pointer items-start gap-3 rounded-2xl border p-4 transition-all"
              :class="form.api_mode === 'default' ? 'border-zinc-800 bg-white ring-1 ring-zinc-800/10' : 'border-zinc-200 bg-white/70'"
            >
              <input v-model="form.api_mode" type="radio" value="default" class="mt-1 h-4 w-4 accent-zinc-800" />
              <span>
                <span class="block text-sm font-medium text-zinc-800">默认 API</span>
                <span class="mt-1 block text-xs leading-6 text-zinc-500">计入系统额度，适合直接开始体验。</span>
              </span>
            </label>
            <label
              class="flex cursor-pointer items-start gap-3 rounded-2xl border p-4 transition-all"
              :class="form.api_mode === 'custom' ? 'border-zinc-800 bg-white ring-1 ring-zinc-800/10' : 'border-zinc-200 bg-white/70'"
            >
              <input v-model="form.api_mode" type="radio" value="custom" class="mt-1 h-4 w-4 accent-zinc-800" />
              <span>
                <span class="block text-sm font-medium text-zinc-800">自定义 API</span>
                <span class="mt-1 block text-xs leading-6 text-zinc-500">不计平台额度，适合接入自己的模型与网关。</span>
              </span>
            </label>
          </div>
        </fieldset>

        <div class="grid gap-5 lg:grid-cols-2">
          <BaseInput
            v-model="form.custom_model_name"
            label="自定义模型名"
            placeholder="例如 gpt-4o-mini"
            :disabled="form.api_mode === 'default'"
          />
          <BaseInput
            v-model="form.custom_base_url"
            label="自定义 Base URL"
            placeholder="例如 https://api.openai.com/v1"
            :disabled="form.api_mode === 'default'"
          />
        </div>

        <BaseInput
          v-model="form.custom_api_key"
          label="自定义 API Key"
          type="password"
          placeholder="留空表示不修改；输入新值会覆盖"
          :disabled="form.api_mode === 'default'"
        />

        <div class="flex flex-col gap-3">
          <p v-if="errorMessage" class="text-sm text-red-500">{{ errorMessage }}</p>
          <p v-if="successMessage" class="text-sm text-emerald-600">{{ successMessage }}</p>
        </div>

        <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
          <BaseButton type="submit" :loading="isSaving" :block="false">保存设置</BaseButton>
          <p class="text-xs text-zinc-500">自定义 Key 留空时不会覆盖已有值。</p>
        </div>
      </form>
    </div>
  </section>
</template>
