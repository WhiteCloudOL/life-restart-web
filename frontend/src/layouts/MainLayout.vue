<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue';
import { RouterLink, RouterView } from 'vue-router';
import { useAuthStore } from '@/stores/useAuthStore';

const authStore = useAuthStore();
let syncTimer: number | null = null;

const userName = computed<string>(() => authStore.user?.nickname ?? authStore.user?.username ?? '游客');

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
  <div class="layout-shell">
    <header class="topbar">
      <RouterLink class="brand" to="/">AI Life Simulator</RouterLink>
      <nav class="nav">
        <RouterLink to="/">大厅</RouterLink>
        <RouterLink to="/profile">设置</RouterLink>
        <RouterLink v-if="authStore.user?.is_admin" to="/admin">管理</RouterLink>
      </nav>
      <div class="right">
        <span class="quota">{{ authStore.quotaText }}</span>
        <span class="name">{{ userName }}</span>
        <button class="logout" type="button" @click="onLogout">退出</button>
      </div>
    </header>
    <main class="main-content">
      <RouterView v-slot="{ Component, route }">
        <Transition name="page-float" mode="out-in">
          <component :is="Component" :key="route.fullPath" />
        </Transition>
      </RouterView>
    </main>
  </div>
</template>

<style scoped>
.layout-shell {
  min-height: 100vh;
}

.topbar {
  min-height: 66px;
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px);
  box-shadow: var(--shadow-soft);
}

.brand {
  font-weight: 700;
  letter-spacing: 0.7px;
  color: var(--title);
  text-transform: uppercase;
  font-size: 13px;
  font-family: var(--font-serif);
}

.nav {
  display: flex;
  gap: 8px;
  font-size: 14px;
}

.nav a {
  color: var(--subtext);
  padding: 6px 10px;
  border-radius: 999px;
  transition: color 0.2s ease, background-color 0.2s ease;
}

.nav a:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.66);
}

.nav a.router-link-exact-active {
  color: #0f766e;
  background: rgba(212, 239, 229, 0.95);
  border: 1px solid rgba(42, 157, 143, 0.4);
}

.right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.quota {
  color: var(--subtext);
  font-size: 14px;
}

.name {
  font-size: 14px;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.72);
}

.logout {
  border: 1px solid var(--line);
  color: var(--text);
  background: rgba(255, 255, 255, 0.72);
  height: 32px;
  padding: 0 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.3s ease, background-color 0.3s ease, transform 0.3s ease;
}

.logout:hover {
  border-color: var(--line-strong);
  background: rgba(235, 247, 241, 0.95);
  transform: scale(1.02);
}

.main-content {
  width: min(1220px, 100%);
  margin: 0 auto;
  padding: 28px 20px 44px;
}

@media (max-width: 860px) {
  .topbar {
    height: auto;
    min-height: 64px;
    padding: 10px 14px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .nav {
    order: 3;
    width: 100%;
  }
}

.page-float-enter-active,
.page-float-leave-active {
  transition: opacity 0.2s ease-out;
}

.page-float-enter-from,
.page-float-leave-to {
  opacity: 0;
}
</style>
