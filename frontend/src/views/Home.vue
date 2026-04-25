<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import BaseButton from '@/components/BaseButton.vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useGameStore } from '@/stores/useGameStore';

const authStore = useAuthStore();
const gameStore = useGameStore();
const router = useRouter();

const onStart = async (presetId: number): Promise<void> => {
  try {
    gameStore.preparePreset(presetId);
    await router.push('/game');
  } catch (error) {
    const message = (error as { message?: string }).message ?? '启动失败，请稍后重试';
    window.dispatchEvent(
      new CustomEvent('app:toast', {
        detail: { type: 'error', message },
      }),
    );
  }
};

onMounted(() => {
  if (!authStore.user && authStore.token) {
    authStore.fetchUserInfo().catch(() => null);
  }
  gameStore.fetchPresets().catch(() => null);
});
</script>

<template>
  <section class="hero">
    <p class="tag">AI 人生重开模拟器</p>
    <h1>世界大厅</h1>
    <p class="subtitle">选择一个开局世界，先完成属性分配，再开始你独一无二的人生线路。</p>
  </section>

  <section class="grid">
    <article v-for="preset in gameStore.presets" :key="preset.id" class="card">
      <h3 class="title">{{ preset.title }}</h3>
      <p>{{ preset.description }}</p>
      <p class="worldview">{{ preset.worldview }}</p>
      <p class="meta">属性总点上限：{{ preset.max_attribute_points }}</p>
      <BaseButton :loading="gameStore.isActionPending" @click="onStart(preset.id)">
        配置并进入
      </BaseButton>
    </article>
  </section>

  <section v-if="!gameStore.isLoadingPresets && gameStore.presets.length === 0" class="empty">
    暂无可用预设，请稍后刷新。
  </section>
</template>

<style scoped>
.hero {
  margin-bottom: 22px;
  padding: 24px 22px 18px;
  border-radius: 24px;
  border: 1px solid var(--line);
  background: linear-gradient(130deg, rgba(132, 169, 140, 0.14), rgba(232, 208, 162, 0.18));
  backdrop-filter: blur(14px);
  box-shadow: var(--shadow-soft);
}

.tag {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 12px;
  letter-spacing: 1px;
}

h1 {
  margin: 0;
  font-size: clamp(28px, 4vw, 40px);
  color: var(--title);
  font-family: var(--font-serif);
}

.subtitle {
  margin: 10px 0 0;
  color: var(--subtext);
}

.grid {
  display: grid;
  grid-template-columns: repeat(1, minmax(0, 1fr));
  gap: 18px;
}

@media (min-width: 768px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.card {
  padding: 18px;
  border-radius: 24px;
  border: 1px solid var(--line);
  background:
    linear-gradient(165deg, rgba(255, 255, 255, 0.84), rgba(248, 250, 252, 0.74)),
    linear-gradient(180deg, rgba(42, 157, 143, 0.08), rgba(232, 208, 162, 0.06));
  backdrop-filter: blur(14px);
  display: grid;
  gap: 12px;
  box-shadow: var(--shadow-soft);
  transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}

.card:hover {
  transform: translateY(-4px);
  border-color: var(--line-strong);
  box-shadow: 0 16px 34px rgba(0, 0, 0, 0.08);
}

.title {
  margin: 0;
  color: var(--title);
  font-family: var(--font-serif);
  font-size: 24px;
}

.card p {
  margin: 0;
  color: var(--subtext);
  line-height: 1.8;
}

.worldview {
  min-height: 60px;
  font-size: 13px;
  line-height: 1.5;
}

.meta {
  margin: 0;
  font-size: 12px;
  color: var(--accent);
}

.empty {
  margin-top: 18px;
  color: var(--subtext);
}
</style>
