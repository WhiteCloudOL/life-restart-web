<script setup lang="ts">
withDefaults(
  defineProps<{
    type?: 'button' | 'submit' | 'reset';
    loading?: boolean;
    disabled?: boolean;
    block?: boolean;
  }>(),
  {
    type: 'button',
    loading: false,
    disabled: false,
    block: true,
  },
);
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    class="inline-flex h-11 items-center justify-center rounded-xl bg-zinc-800 px-5 text-sm font-medium text-white transition-all duration-300 hover:bg-zinc-900 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-zinc-800/20 disabled:cursor-not-allowed disabled:opacity-60"
    :class="block ? 'w-full' : ''"
  >
    <span v-if="loading">处理中...</span>
    <slot v-else />
  </button>
</template>
