<script setup lang="ts">
defineProps<{
  activeChoice: string | null;
  canOperate: boolean;
  currentSituation: string;
  customChoice: string;
  endSummary: string | null;
  executeEtaText: string;
  hasPendingStorySegments: boolean;
  isActionPending: boolean;
  isEnded: boolean;
  isSubmittingCustom: boolean;
  nextPendingSegmentsCount: number;
  parsedChoices: Array<{ raw: string; action: string; meta: string; tone: 'high' | 'medium' | 'low' }>;
  retryChoiceValue: string | null;
  toneClasses: Record<'high' | 'medium' | 'low', string>;
}>();

const emit = defineEmits<{
  'ask-retry': [];
  'back-lobby': [];
  'force-exit': [];
  'reveal-segment': [];
  'run-choice': [choice: string];
  'submit-custom': [];
  'update:custom-choice': [value: string];
}>();
</script>

<template>
  <aside class="w-full space-y-5 lg:w-[24rem]">
    <section
      class="rounded-2xl border border-zinc-200/60 bg-zinc-50/80 p-5 ring-1 ring-zinc-900/5"
    >
      <p class="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">Current Situation</p>
      <p class="mt-3 text-[15px] leading-7 text-zinc-700">{{ currentSituation }}</p>
      <p v-if="isActionPending" class="mt-3 text-xs text-zinc-500">{{ executeEtaText }}</p>
    </section>

    <section
      v-if="hasPendingStorySegments"
      class="rounded-2xl border border-zinc-200/60 bg-white p-5 shadow-sm"
    >
      <p class="text-sm font-semibold text-zinc-800">还有 {{ nextPendingSegmentsCount }} 段剧情未展开</p>
      <button
        type="button"
        class="mt-4 w-full rounded-xl bg-zinc-800 py-3 text-sm font-medium text-white transition-all duration-300 hover:bg-zinc-900 hover:shadow-md"
        @click="emit('reveal-segment')"
      >
        继续阅读下一段
      </button>
    </section>

    <section v-if="!isEnded" class="space-y-3">
      <button
        v-for="choice in parsedChoices"
        :key="choice.raw"
        type="button"
        class="flex w-full cursor-pointer items-start gap-4 rounded-xl border border-zinc-200 bg-white p-4 text-left shadow-sm transition-all hover:border-zinc-400 hover:bg-zinc-50 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="!canOperate"
        @click="emit('run-choice', choice.raw)"
      >
        <span class="shrink-0 rounded px-2.5 py-1 text-[11px] font-bold tracking-wider" :class="toneClasses[choice.tone]">
          {{ choice.tone === 'high' ? '高风险' : choice.tone === 'medium' ? '中风险' : '低风险' }}
        </span>
        <span class="min-w-0 flex-1">
          <span class="block text-[14px] font-medium leading-snug text-zinc-700 pt-0.5">
            {{ choice.action }}
          </span>
          <span class="mt-2 block text-xs leading-6 text-zinc-500">{{ choice.meta }}</span>
        </span>
        <span
          v-if="activeChoice === choice.raw"
          class="mt-1 h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-zinc-200 border-t-zinc-800"
        />
      </button>
    </section>

    <section v-if="!isEnded" class="space-y-3">
      <button
        v-if="retryChoiceValue"
        type="button"
        class="w-full rounded-xl border border-zinc-200/70 bg-white px-4 py-3 text-sm font-medium text-zinc-600 transition-all hover:border-zinc-300 hover:bg-zinc-50 disabled:opacity-60"
        :disabled="!canOperate"
        @click="emit('ask-retry')"
      >
        重试上一次推进
      </button>

      <form class="space-y-2" @submit.prevent="emit('submit-custom')">
        <div class="relative mt-6 flex w-full items-center">
          <input
            :value="customChoice"
            :disabled="!canOperate"
            maxlength="200"
            class="w-full rounded-xl border border-zinc-300 bg-white py-3.5 pl-4 pr-24 text-sm text-zinc-700 shadow-sm transition-all focus:border-zinc-800 focus:ring-2 focus:ring-zinc-800/20"
            placeholder="或输入你的自定义行动（最多 200 字）"
            @input="emit('update:custom-choice', ($event.target as HTMLInputElement).value)"
          />
          <button
            type="submit"
            class="absolute right-1.5 rounded-lg bg-zinc-800 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-900 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="!canOperate || !customChoice.trim() || isSubmittingCustom"
          >
            {{ isSubmittingCustom ? '执行中' : '执行' }}
          </button>
        </div>
        <p class="text-xs text-zinc-500">{{ executeEtaText }}</p>
      </form>
    </section>

    <section
      v-if="isEnded"
      class="rounded-2xl border border-zinc-200/60 bg-white p-5 shadow-sm"
    >
      <p class="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">End Summary</p>
      <h3 class="mt-3 text-xl font-bold text-zinc-900">人生总结</h3>
      <p class="mt-4 text-[15px] leading-8 text-zinc-700">
        {{ endSummary || '本次人生已结束。' }}
      </p>
      <button
        type="button"
        class="mt-6 rounded-xl bg-zinc-800 px-5 py-3 text-sm font-medium text-white transition-all duration-300 hover:bg-zinc-900 hover:shadow-md"
        @click="emit('back-lobby')"
      >
        返回大厅
      </button>
    </section>

    <div v-if="!isEnded" class="flex justify-end">
      <button
        type="button"
        class="rounded-xl border border-zinc-200/70 bg-white px-4 py-2 text-sm font-medium text-zinc-600 transition-all hover:border-zinc-300 hover:bg-zinc-50"
        :disabled="isActionPending"
        @click="emit('force-exit')"
      >
        强制退出
      </button>
    </div>
  </aside>
</template>
