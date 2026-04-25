export interface RegisterFormValue {
  username: string;
  password: string;
  confirmPassword: string;
}

export const USERNAME_MIN_LENGTH = 3;
export const USERNAME_MAX_LENGTH = 32;
export const PASSWORD_MIN_LENGTH = 10;
export const PASSWORD_MAX_LENGTH = 128;

const usernamePattern = /^[a-zA-Z0-9_]+$/;
const hasUppercase = /[A-Z]/;
const hasLowercase = /[a-z]/;
const hasNumber = /\d/;
const hasSpecial = /[^A-Za-z0-9]/;
const weakWords = ['password', 'qwerty', 'admin', '123456'];

export const validateUsername = (username: string): string => {
  const trimmed = username.trim();
  if (trimmed.length < USERNAME_MIN_LENGTH) {
    return `用户名长度至少为 ${USERNAME_MIN_LENGTH}`;
  }
  if (trimmed.length > USERNAME_MAX_LENGTH) {
    return `用户名长度不能超过 ${USERNAME_MAX_LENGTH}`;
  }
  if (!usernamePattern.test(trimmed)) {
    return '用户名仅支持字母、数字、下划线';
  }
  return '';
};

export const validatePassword = (password: string): string => {
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `密码长度至少为 ${PASSWORD_MIN_LENGTH}`;
  }
  if (password.length > PASSWORD_MAX_LENGTH) {
    return `密码长度不能超过 ${PASSWORD_MAX_LENGTH}`;
  }
  if (!hasUppercase.test(password)) {
    return '密码需至少包含 1 个大写字母';
  }
  if (!hasLowercase.test(password)) {
    return '密码需至少包含 1 个小写字母';
  }
  if (!hasNumber.test(password)) {
    return '密码需至少包含 1 个数字';
  }
  if (!hasSpecial.test(password)) {
    return '密码需至少包含 1 个特殊字符';
  }
  const lowered = password.toLowerCase();
  if (weakWords.some((word) => lowered.includes(word))) {
    return '密码过于常见，请更换更强密码';
  }
  if (new TextEncoder().encode(password).length > 72) {
    return '密码过长（最多 72 字节）';
  }
  return '';
};

export const validateConfirmPassword = (password: string, confirmPassword: string): string => {
  if (password !== confirmPassword) {
    return '两次输入的密码不一致';
  }
  return '';
};
