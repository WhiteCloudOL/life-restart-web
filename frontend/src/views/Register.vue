<script setup lang="ts">
import { computed, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { register } from '@/api/auth';
import AuthCard from '@/components/AuthCard.vue';
import BaseButton from '@/components/BaseButton.vue';
import BaseInput from '@/components/BaseInput.vue';
import {
  PASSWORD_MAX_LENGTH,
  USERNAME_MAX_LENGTH,
  USERNAME_MIN_LENGTH,
  validateConfirmPassword,
  validatePassword,
  validateUsername,
} from '@/utils/auth-validators';

const router = useRouter();
const form = ref({
  username: '',
  password: '',
  confirmPassword: '',
});

const isSubmitting = ref<boolean>(false);
const globalError = ref<string>('');
const successMessage = ref<string>('');
const usernameError = ref<string>('');
const passwordError = ref<string>('');
const confirmPasswordError = ref<string>('');

const canSubmit = computed<boolean>(() => !isSubmitting.value);

const validateForm = (): boolean => {
  usernameError.value = validateUsername(form.value.username);
  passwordError.value = validatePassword(form.value.password);
  confirmPasswordError.value = validateConfirmPassword(
    form.value.password,
    form.value.confirmPassword,
  );
  return !usernameError.value && !passwordError.value && !confirmPasswordError.value;
};

const onSubmit = async (): Promise<void> => {
  globalError.value = '';
  successMessage.value = '';
  if (!validateForm()) {
    return;
  }

  isSubmitting.value = true;
  try {
    await register({
      username: form.value.username.trim(),
      password: form.value.password,
    });
    successMessage.value = '注册成功，请前往登录';
    form.value.password = '';
    form.value.confirmPassword = '';
    setTimeout(() => {
      router.push('/login');
    }, 600);
  } catch (error) {
    const message = (error as { message?: string }).message;
    globalError.value = message ?? '注册失败，请稍后重试';
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <AuthCard title="创建新角色" subtitle="注册后即可开启你的第一段人生轨迹">
    <form class="form" @submit.prevent="onSubmit">
      <BaseInput
        v-model="form.username"
        label="用户名"
        autocomplete="username"
        placeholder="3-32 位，仅支持字母/数字/下划线"
        :error="usernameError"
        :max-length="USERNAME_MAX_LENGTH"
        @blur="validateForm"
      />
      <BaseInput
        v-model="form.password"
        label="密码"
        type="password"
        autocomplete="new-password"
        placeholder="至少 10 位，需包含字母和数字"
        :error="passwordError"
        :max-length="PASSWORD_MAX_LENGTH"
        @blur="validateForm"
      />
      <BaseInput
        v-model="form.confirmPassword"
        label="确认密码"
        type="password"
        autocomplete="new-password"
        placeholder="再次输入密码"
        :error="confirmPasswordError"
        :max-length="PASSWORD_MAX_LENGTH"
        @blur="validateForm"
      />
      <p v-if="globalError" class="error">{{ globalError }}</p>
      <p v-if="successMessage" class="success">{{ successMessage }}</p>
      <BaseButton type="submit" :loading="isSubmitting" :disabled="!canSubmit">
        {{ isSubmitting ? '提交中...' : '创建账号' }}
      </BaseButton>
    </form>
    <p class="foot">
      已有账号？
      <RouterLink to="/login">去登录</RouterLink>
    </p>
    <p class="hint">用户名最少 {{ USERNAME_MIN_LENGTH }} 位，密码至少 10 位且需含数字。</p>
  </AuthCard>
</template>

<style scoped>
.form {
  display: grid;
  gap: 14px;
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

.foot {
  margin: 16px 0 0;
  color: var(--subtext);
  font-size: 14px;
}

.hint {
  margin: 12px 0 0;
  color: rgba(134, 164, 194, 0.8);
  font-size: 12px;
}
</style>
