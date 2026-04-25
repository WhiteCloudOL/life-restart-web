<script setup lang="ts">
defineProps<{
  visible: boolean;
  title: string;
}>();

const emit = defineEmits<{
  (event: 'close'): void;
}>();
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="overlay" @click.self="emit('close')">
        <section class="modal">
          <header class="head">
            <h3>{{ title }}</h3>
            <button class="close" type="button" @click="emit('close')">×</button>
          </header>
          <div class="body">
            <slot />
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.18);
  z-index: 999;
}

.modal {
  width: min(480px, calc(100vw - 28px));
  border-radius: 24px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(14px);
  box-shadow: var(--shadow-soft);
}

.head {
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

h3 {
  margin: 0;
  font-size: 16px;
}

.close {
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  color: var(--text);
  cursor: pointer;
}

.body {
  padding: 16px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
