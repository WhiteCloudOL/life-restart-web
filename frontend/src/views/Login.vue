<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter, useRoute, RouterLink } from 'vue-router';
import AuthCard from '@/components/AuthCard.vue';
import BaseButton from '@/components/BaseButton.vue';
import BaseInput from '@/components/BaseInput.vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { PASSWORD_MAX_LENGTH, validateUsername } from '@/utils/auth-validators';

const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();

const username = ref<string>('');
const password = ref<string>('');
const globalError = ref<string>('');
const usernameError = ref<string>('');
const passwordError = ref<string>('');

const canSubmit = computed<boolean>(() => !authStore.isLoggingIn);

const validateForm = (): boolean => {
  usernameError.value = validateUsername(username.value);
  if (!password.value) {
    passwordError.value = '请输入密码';
  } else if (password.value.length > PASSWORD_MAX_LENGTH) {
    passwordError.value = `密码长度不能超过 ${PASSWORD_MAX_LENGTH}`;
  } else {
    passwordError.value = '';
  }
  return !usernameError.value && !passwordError.value;
};

const onSubmit = async (): Promise<void> => {
  globalError.value = '';
  if (!validateForm()) {
    return;
  }

  try {
    await authStore.login({
      username: username.value.trim(),
      password: password.value,
    });

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/';
    await router.replace(redirect);
  } catch (error) {
    const message = (error as { message?: string }).message;
    globalError.value = message ?? '登录失败，请稍后重试';
  }
};
</script>

<template>
  <AuthCard title="欢迎回来" subtitle="继续你的 AI 人生推演">
    <form class="grid gap-5" @submit.prevent="onSubmit">
      <BaseInput
        v-model="username"
        label="用户名"
        autocomplete="username"
        placeholder="请输入用户名"
        :error="usernameError"
        @blur="validateForm"
      />
      <BaseInput
        v-model="password"
        label="密码"
        type="password"
        autocomplete="current-password"
        placeholder="请输入密码"
        :error="passwordError"
        :max-length="PASSWORD_MAX_LENGTH"
        @blur="validateForm"
      />
      <p v-if="globalError" class="text-sm text-red-500">{{ globalError }}</p>
      <BaseButton type="submit" :loading="authStore.isLoggingIn" :disabled="!canSubmit">
        {{ authStore.isLoggingIn ? '登录中...' : '登录' }}
      </BaseButton>
    </form>
    <p class="mt-6 text-sm text-zinc-500">
      没有账号？
      <RouterLink to="/register" class="font-medium text-zinc-900 transition-colors hover:text-zinc-600">去注册</RouterLink>
    </p>
  </AuthCard>
</template>
