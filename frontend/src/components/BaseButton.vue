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
  <button :type="type" :disabled="disabled || loading" :class="{ block }">
    <span v-if="loading">处理中...</span>
    <slot v-else />
  </button>
</template>

<style scoped>
button {
  position: relative;
  overflow: hidden;
  height: 42px;
  border: 0;
  border-radius: 14px;
  font-weight: 700;
  letter-spacing: 0.2px;
  color: #fff;
  cursor: pointer;
  background: linear-gradient(92deg, var(--accent), #6da58f);
  box-shadow: var(--shadow-soft);
  transition: transform 0.3s ease, opacity 0.3s ease, box-shadow 0.3s ease, background-color 0.3s ease;
}

button:hover:enabled {
  transform: translateY(-1px) scale(1.02);
  box-shadow: 0 10px 30px rgba(42, 157, 143, 0.2);
}

button:focus-visible {
  outline: 2px solid rgba(105, 178, 255, 0.6);
  outline-offset: 2px;
}

button:disabled {
  opacity: 0.62;
  cursor: not-allowed;
}

.block {
  width: 100%;
}
</style>
