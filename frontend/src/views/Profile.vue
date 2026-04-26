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

    // 空值不覆盖 Key，防止误清空；如果要清空可在后续加“清空 Key”显式开关。
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
  <section class="panel">
    <h1>个人设置</h1>
    <p class="hint">用户名不可修改。可修改昵称并切换默认 API / 自定义 API（自定义模式不计额度）。</p>
    <form class="form" @submit.prevent="onSave">
      <BaseInput v-model="form.username" label="用户名（不可修改）" autocomplete="username" disabled />
      <BaseInput v-model="form.nickname" label="昵称" autocomplete="nickname" placeholder="用于展示的昵称" />
      <fieldset class="mode-group">
        <legend>调用模式</legend>
        <label>
          <input v-model="form.api_mode" type="radio" value="default" />
          <span>默认 API（计入额度）</span>
        </label>
        <label>
          <input v-model="form.api_mode" type="radio" value="custom" />
          <span>自定义 API（不计额度）</span>
        </label>
      </fieldset>
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
      <BaseInput
        v-model="form.custom_api_key"
        label="自定义 API Key"
        type="password"
        placeholder="留空表示不修改；输入新值会覆盖"
        :disabled="form.api_mode === 'default'"
      />
      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      <p v-if="successMessage" class="success">{{ successMessage }}</p>
      <BaseButton type="submit" :loading="isSaving">保存设置</BaseButton>
    </form>
  </section>
</template>

<style scoped>
.panel {
  padding: 24px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: var(--panel);
  backdrop-filter: blur(14px);
  box-shadow: var(--shadow-soft);
  width: min(760px, 100%);
}

h1 {
  margin: 0;
  color: var(--title);
  font-family: var(--font-serif);
}

.hint {
  margin: 10px 0 0;
  color: var(--subtext);
  line-height: 1.75;
}

.form {
  display: grid;
  gap: 14px;
  margin-top: 20px;
}

.mode-group {
  margin: 0;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 12px 14px;
  display: grid;
  gap: 10px;
  background: rgba(255, 255, 255, 0.66);
}

.mode-group legend {
  padding: 0 6px;
  color: var(--subtext);
  font-size: 13px;
}

.mode-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text);
}

.error {
  margin: 0;
  color: var(--danger);
  font-size: 13px;
}

.success {
  margin: 0;
  color: var(--accent-2);
  font-size: 13px;
}
</style>
