<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    modelValue: string;
    label: string;
    type?: 'text' | 'password' | 'email';
    placeholder?: string;
    autocomplete?: string;
    error?: string;
    disabled?: boolean;
    maxLength?: number;
  }>(),
  {
    type: 'text',
    placeholder: '',
    autocomplete: 'off',
    error: '',
    disabled: false,
    maxLength: undefined,
  },
);

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void;
  (event: 'blur'): void;
}>();

const fieldClass = computed<string>(() => (props.error ? 'input is-error' : 'input'));

const onInput = (event: Event): void => {
  const target = event.target as HTMLInputElement;
  emit('update:modelValue', target.value);
};
</script>

<template>
  <label class="field">
    <span class="label">{{ label }}</span>
    <input
      :class="fieldClass"
      :value="modelValue"
      :type="type"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      :disabled="disabled"
      :maxlength="maxLength"
      @input="onInput"
      @blur="$emit('blur')"
    />
    <span v-if="error" class="error">{{ error }}</span>
  </label>
</template>

<style scoped>
.field {
  display: grid;
  gap: 7px;
}

.label {
  font-size: 13px;
  color: var(--subtext);
}

.input {
  height: 42px;
  border-radius: 14px;
  border: 1px solid var(--line);
  padding: 0 12px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--text);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.input:focus {
  outline: none;
  border-color: rgba(76, 201, 240, 0.55);
  box-shadow: 0 0 0 3px rgba(76, 201, 240, 0.15);
}

.input.is-error {
  border-color: rgba(255, 92, 122, 0.65);
}

.input:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.error {
  font-size: 12px;
  color: var(--danger);
}
</style>
