<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/useAuthStore';
import { useGameStore } from '@/stores/useGameStore';

const authStore = useAuthStore();
const gameStore = useGameStore();
const router = useRouter();

const worlds = computed(() => gameStore.presets);

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
  <section class="space-y-10 pb-16 pt-6 lg:pt-10">
    <div
      class="relative overflow-hidden rounded-[2rem] border border-zinc-200/60 bg-white/80 px-6 py-8 shadow-[0_24px_80px_rgba(24,24,27,0.06)] ring-1 ring-zinc-900/5 backdrop-blur-xl lg:px-10 lg:py-12"
    >
      <div
        class="pointer-events-none absolute inset-x-10 top-0 h-24 rounded-full bg-[radial-gradient(circle_at_center,rgba(24,24,27,0.05),transparent_72%)]"
      />
      <div class="relative mx-auto max-w-3xl text-center">
        <p class="text-xs font-semibold uppercase tracking-[0.32em] text-zinc-500">Observer Mode</p>
        <h1 class="mt-4 text-4xl font-bold tracking-tight text-zinc-900 lg:text-5xl">世界大厅</h1>
        <p class="mx-auto mt-5 max-w-2xl text-sm leading-8 text-zinc-500 lg:text-[15px]">
          选择一个世界切面，先完成开局设定，再以更高维的观测视角，看见一段人生如何被选择缓慢雕刻。
        </p>
      </div>
    </div>

    <section
      class="max-w-7xl mx-auto grid grid-cols-1 gap-6 px-4 py-12 md:grid-cols-2 lg:grid-cols-3 lg:gap-8"
    >
      <article
        v-for="preset in worlds"
        :key="preset.id"
        class="group relative flex min-h-[22rem] flex-col rounded-2xl border border-zinc-200/50 bg-white p-6 shadow-sm transition-all duration-500 hover:-translate-y-1 hover:border-zinc-300 hover:shadow-xl hover:shadow-zinc-200/40"
      >
        <div class="mb-5 flex items-start justify-between gap-4">
          <div>
            <h3 class="mb-2.5 text-[1.15rem] font-bold text-zinc-800">{{ preset.title }}</h3>
            <p class="text-[11px] uppercase tracking-[0.22em] text-zinc-400">
              {{ preset.is_custom ? 'Custom World' : 'Preset World' }}
            </p>
          </div>
          <span
            class="inline-flex items-center rounded-full bg-zinc-100 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500 ring-1 ring-inset ring-zinc-200"
          >
            {{ preset.character_options.length }} 人设
          </span>
        </div>

        <p class="mb-4 text-[13px] leading-relaxed text-zinc-500 line-clamp-3">{{ preset.description }}</p>
        <p class="mb-6 text-[13px] leading-7 text-zinc-500/90 line-clamp-4 flex-grow">{{ preset.worldview }}</p>

        <span class="mb-4 inline-block rounded bg-zinc-50 px-2 py-1 font-mono text-[11px] text-zinc-400">
          属性点上限 {{ preset.max_attribute_points }}
        </span>

        <button
          type="button"
          class="w-full rounded-xl border border-zinc-200/50 bg-zinc-50 py-2.5 text-sm font-medium text-zinc-600 transition-all group-hover:border-zinc-800 group-hover:bg-zinc-800 group-hover:text-white"
          :disabled="gameStore.isActionPending"
          @click="onStart(preset.id)"
        >
          {{ gameStore.isActionPending ? '正在进入...' : '配置并进入' }}
        </button>
      </article>
    </section>

    <section
      v-if="gameStore.isLoadingPresets"
      class="mx-auto max-w-7xl px-4 text-center text-sm text-zinc-500"
    >
      正在整理可进入的世界...
    </section>

    <section
      v-else-if="worlds.length === 0"
      class="mx-auto max-w-3xl rounded-[1.75rem] border border-dashed border-zinc-200 bg-white/70 px-6 py-12 text-center text-sm text-zinc-500 ring-1 ring-zinc-900/5"
    >
      暂无可用预设，请稍后刷新。
    </section>
  </section>
</template>
