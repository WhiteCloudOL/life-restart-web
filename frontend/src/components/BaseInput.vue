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

const fieldClass = computed<string>(() =>
  props.error
    ? 'border-red-200 bg-red-50/50 focus:border-red-400 focus:ring-red-200'
    : 'border-zinc-200 bg-zinc-50/50 focus:border-zinc-800 focus:ring-zinc-800/20',
);

const onInput = (event: Event): void => {
  const target = event.target as HTMLInputElement;
  emit('update:modelValue', target.value);
};
</script>

<template>
  <label class="grid gap-2">
    <span class="text-sm font-medium text-zinc-600">{{ label }}</span>
    <input
      :value="modelValue"
      :type="type"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      :disabled="disabled"
      :maxlength="maxLength"
      class="w-full rounded-xl border px-4 py-3 text-sm text-zinc-700 placeholder-zinc-400 transition-all focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:opacity-60"
      :class="fieldClass"
      @input="onInput"
      @blur="$emit('blur')"
    />
    <span v-if="error" class="text-xs text-red-500">{{ error }}</span>
  </label>
</template>
