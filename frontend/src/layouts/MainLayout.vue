<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/useAuthStore';

const authStore = useAuthStore();
const route = useRoute();
let syncTimer: number | null = null;

const userName = computed<string>(() => authStore.user?.nickname ?? authStore.user?.username ?? '游客');

const navItems = computed(() => {
  const base = [
    { label: '大厅', to: '/' },
    { label: '设置', to: '/profile' },
  ];

  if (authStore.user?.is_admin) {
    base.push({ label: '管理', to: '/admin' });
  }

  return base;
});

const isGameRoute = computed<boolean>(() => route.path === '/game');

const onLogout = (): void => {
  authStore.logout();
  window.location.replace('/login');
};

const stopQuotaSync = (): void => {
  if (syncTimer !== null) {
    window.clearInterval(syncTimer);
    syncTimer = null;
  }
};

const startQuotaSync = (): void => {
  stopQuotaSync();
  if (!authStore.token) {
    return;
  }
  syncTimer = window.setInterval(() => {
    if (!authStore.token || authStore.isFetchingUser) {
      return;
    }
    authStore.fetchUserInfo().catch(() => null);
  }, 8000);
};

onMounted(() => {
  startQuotaSync();
});

onBeforeUnmount(() => {
  stopQuotaSync();
});

watch(
  () => authStore.token,
  () => {
    startQuotaSync();
  },
);
</script>

<template>
  <div class="min-h-screen bg-zinc-50">
    <header
      class="fixed inset-x-0 top-0 z-50 flex h-16 items-center justify-between border-b border-zinc-100 bg-white/70 px-6 backdrop-blur-xl lg:px-12"
    >
      <RouterLink to="/" class="text-lg font-bold tracking-tight text-zinc-800">AI Life Simulator</RouterLink>

      <nav class="hidden items-center gap-8 text-sm font-medium text-zinc-500 md:flex">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="transition-colors hover:text-zinc-900"
          :class="route.path === item.to ? 'text-zinc-900' : ''"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="flex min-w-0 items-center gap-2 lg:gap-3">
        <span
          class="hidden items-center gap-1.5 rounded-full bg-zinc-100/80 px-3 py-1.5 text-xs font-semibold text-zinc-600 ring-1 ring-inset ring-zinc-200 xl:inline-flex"
        >
          <span class="h-1.5 w-1.5 rounded-full bg-zinc-400" />
          {{ authStore.quotaText }}
        </span>
        <span
          class="inline-flex items-center gap-1.5 rounded-full bg-zinc-100/80 px-3 py-1.5 text-xs font-semibold text-zinc-600 ring-1 ring-inset ring-zinc-200"
        >
          {{ userName }}
        </span>
        <button
          type="button"
          class="rounded-full bg-zinc-800 px-3.5 py-2 text-xs font-medium text-white transition-all duration-300 hover:bg-zinc-900 hover:shadow-md"
          @click="onLogout"
        >
          退出
        </button>
      </div>
    </header>

    <main :class="isGameRoute ? 'px-0' : 'px-0'">
      <div :class="isGameRoute ? 'pt-16' : 'mx-auto max-w-[1400px] px-0 pt-16'">
        <RouterView v-slot="{ Component, route: currentRoute }">
          <Transition name="page-float" mode="out-in">
            <component :is="Component" :key="currentRoute.fullPath" />
          </Transition>
        </RouterView>
      </div>
    </main>
  </div>
</template>

<style scoped>
.page-float-enter-active,
.page-float-leave-active {
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.page-float-enter-from,
.page-float-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
