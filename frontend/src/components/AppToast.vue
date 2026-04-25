<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import type { ToastPayload } from '@/api/request';

interface QueueToast extends ToastPayload {
  id: number;
}

const queue = ref<QueueToast[]>([]);
let seedId = 0;
let timer: number | null = null;

const currentToast = computed<QueueToast | null>(() => queue.value[0] ?? null);

const dismissCurrent = (): void => {
  queue.value.shift();
  if (queue.value.length > 0) {
    scheduleDismiss();
  } else if (timer !== null) {
    window.clearTimeout(timer);
    timer = null;
  }
};

const scheduleDismiss = (): void => {
  if (timer !== null) {
    window.clearTimeout(timer);
  }
  timer = window.setTimeout(() => {
    dismissCurrent();
  }, 2600);
};

const onToast = (event: Event): void => {
  const custom = event as CustomEvent<ToastPayload>;
  queue.value.push({
    id: ++seedId,
    type: custom.detail.type,
    message: custom.detail.message,
  });

  if (queue.value.length === 1) {
    scheduleDismiss();
  }
};

onMounted(() => {
  window.addEventListener('app:toast', onToast);
});

onBeforeUnmount(() => {
  window.removeEventListener('app:toast', onToast);
  if (timer !== null) {
    window.clearTimeout(timer);
  }
});
</script>

<template>
  <Transition name="fade-up" mode="out-in">
    <div v-if="currentToast" :key="currentToast.id" class="toast-root">
      <div class="toast-card" :class="`is-${currentToast.type}`">
        <span>{{ currentToast.message }}</span>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.toast-root {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 1000;
}

.toast-card {
  min-width: 180px;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(11, 16, 30, 0.94);
  color: #e9f5ff;
  backdrop-filter: blur(8px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

.toast-card.is-warning {
  border-color: rgba(255, 183, 3, 0.45);
}

.toast-card.is-error {
  border-color: rgba(255, 92, 122, 0.45);
}

.toast-card.is-success {
  border-color: rgba(43, 212, 162, 0.45);
}

.fade-up-enter-active,
.fade-up-leave-active {
  transition: all 0.22s ease;
}

.fade-up-enter-from,
.fade-up-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>

