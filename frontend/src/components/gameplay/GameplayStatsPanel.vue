<script setup lang="ts">
defineProps<{
  getStatDelta: (key: string) => number;
  getStatTextTone: (key: string) => string;
  formatStatLabel: (key: string) => string;
  sortedStats: Array<{ key: string; value: number }>;
}>();
</script>

<template>
  <div class="contents">
    <aside
      class="sticky top-24 hidden h-fit w-72 flex-col gap-4 rounded-2xl border border-zinc-200/60 bg-white/80 p-6 shadow-sm backdrop-blur-md lg:flex"
    >
      <div class="border-b border-zinc-100 pb-4">
        <p class="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">Live Metrics</p>
        <h2 class="mt-2 text-xl font-bold text-zinc-900">实时属性</h2>
      </div>

      <div class="space-y-1">
        <div
          v-for="item in sortedStats"
          :key="item.key"
          class="flex items-center justify-between border-b border-zinc-100 py-2 last:border-0"
        >
          <span class="text-sm text-zinc-500">{{ formatStatLabel(item.key) }}</span>
          <div class="flex items-center gap-2">
            <span
              v-if="getStatDelta(item.key) !== 0"
              class="text-[11px] font-semibold"
              :class="getStatDelta(item.key) > 0 ? 'text-emerald-600' : 'text-red-500'"
            >
              {{ getStatDelta(item.key) > 0 ? `+${getStatDelta(item.key)}` : getStatDelta(item.key) }}
            </span>
            <span class="font-mono text-base font-bold" :class="getStatTextTone(item.key)">{{ item.value }}</span>
          </div>
        </div>
      </div>
    </aside>

    <section
      class="mb-4 rounded-2xl border border-zinc-200/60 bg-white/80 p-4 shadow-sm backdrop-blur-md lg:hidden"
    >
      <div class="mb-3 flex items-center justify-between">
        <p class="text-sm font-semibold text-zinc-800">实时属性</p>
        <p class="text-xs text-zinc-500">移动视图</p>
      </div>
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div
          v-for="item in sortedStats"
          :key="`mobile-${item.key}`"
          class="rounded-xl border border-zinc-100 bg-zinc-50/80 px-3 py-2"
        >
          <p class="text-xs text-zinc-500">{{ formatStatLabel(item.key) }}</p>
          <div class="mt-1 flex items-center gap-2">
            <span class="font-mono text-base font-bold" :class="getStatTextTone(item.key)">{{ item.value }}</span>
            <span
              v-if="getStatDelta(item.key) !== 0"
              class="text-[11px] font-semibold"
              :class="getStatDelta(item.key) > 0 ? 'text-emerald-600' : 'text-red-500'"
            >
              {{ getStatDelta(item.key) > 0 ? `+${getStatDelta(item.key)}` : getStatDelta(item.key) }}
            </span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
