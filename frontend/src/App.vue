<script setup lang="ts">
import { RouterView } from 'vue-router';
import AppToast from '@/components/AppToast.vue';
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <Transition name="route-fade-up" mode="out-in">
      <component :is="Component" :key="route.fullPath" />
    </Transition>
  </RouterView>
  <AppToast />
</template>

<style scoped>
.route-fade-up-enter-active,
.route-fade-up-leave-active {
  transition: opacity 0.2s ease-out;
}

.route-fade-up-enter-from,
.route-fade-up-leave-to {
  opacity: 0;
}
</style>
