<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import BaseModal from '@/components/BaseModal.vue';
import TypewriterText from '@/components/TypewriterText.vue';
import { useGameStore } from '@/stores/useGameStore';

const gameStore = useGameStore();
const router = useRouter();

const customChoice = ref<string>('');
const isRetryConfirmVisible = ref<boolean>(false);
const changedStats = ref<Set<string>>(new Set());
const statTrend = ref<Record<string, 'up' | 'down' | 'none'>>({});
const statDelta = ref<Record<string, number>>({});
const previousStats = ref<Record<string, number>>({});
const displayedStats = ref<Record<string, number>>({});
const typedAssistantIds = ref<Set<number>>(new Set());
const activeChoice = ref<string | null>(null);
const isSubmittingCustom = ref<boolean>(false);
const feedRef = ref<HTMLElement | null>(null);
const autoScrollTimer = ref<number | null>(null);
const elapsedTicker = ref<number>(Date.now());
const elapsedTimer = ref<number | null>(null);
const startProcessingSince = ref<number | null>(null);
const gameplayProcessingSince = ref<number | null>(null);
const optionalAttributeKeys = new Set(['happiness', '幸福']);

type ChoiceTone = 'high' | 'medium' | 'low';

const getElapsedSeconds = (since: number | null): number => {
  if (!since) {
    return 0;
  }
  return Math.max(1, Math.floor((elapsedTicker.value - since) / 1000));
};

const startEtaText = computed<string>(() => {
  if (!startProcessingSince.value) {
    return '预计处理 10-25 秒';
  }
  return `正在处理，已处理 ${getElapsedSeconds(startProcessingSince.value)} 秒`;
});

const executeEtaText = computed<string>(() => {
  if (!gameplayProcessingSince.value) {
    return '预计处理 8-20 秒';
  }
  return `正在处理，已处理 ${getElapsedSeconds(gameplayProcessingSince.value)} 秒`;
});

const latestEventId = computed<number | null>(() => {
  const list = gameStore.storyEvents;
  if (list.length === 0) {
    return null;
  }
  return list[list.length - 1]?.id ?? null;
});

const latestAssistantId = computed<number | null>(() => {
  const list = gameStore.storyEvents;
  for (let i = list.length - 1; i >= 0; i -= 1) {
    const item = list[i];
    if (item?.role === 'assistant') {
      return item.id;
    }
  }
  return null;
});

const currentSituation = computed<string>(() => {
  const latestAssistant = [...gameStore.storyEvents].reverse().find((item) => item.role === 'assistant');
  if (!latestAssistant?.content) {
    return '当前面临情况';
  }
  const compact = latestAssistant.content.replace(/\s+/g, ' ').trim();
  if (!compact) {
    return '当前面临情况';
  }
  return compact.length > 56 ? `${compact.slice(0, 56)}...` : compact;
});

const parseChoiceTone = (value: string): ChoiceTone => {
  if (/(高风险|危险|致命|孤注一掷|巨大代价)/.test(value)) {
    return 'high';
  }
  if (/(中风险|博弈|不确定|代价|权衡)/.test(value)) {
    return 'medium';
  }
  return 'low';
};

const toneClasses: Record<ChoiceTone, string> = {
  high: 'bg-red-50 text-red-600 ring-1 ring-red-100',
  medium: 'bg-amber-50 text-amber-600 ring-1 ring-amber-100',
  low: 'bg-emerald-50 text-emerald-600 ring-1 ring-emerald-100',
};

const parsedChoices = computed<Array<{ raw: string; action: string; meta: string; tone: ChoiceTone }>>(() => {
  const limitActionText = (value: string, max = 60): string => {
    const chars = Array.from(value);
    if (chars.length <= max) {
      return value;
    }
    return `${chars.slice(0, max).join('')}...`;
  };

  return gameStore.nextChoices.map((choice) => {
    const text = choice.replace(/\s+/g, ' ').trim();
    let action = text;
    let meta = '命运影响待显现';

    const bracket = text.match(/^\[([^\]]+)\]\s*(.+)$/);
    if (bracket) {
      meta = (bracket[1] ?? '').trim();
      action = (bracket[2] ?? '').trim();
    }

    const fullParen = action.match(/^(.+?)（(.+)）$/);
    if (fullParen) {
      action = (fullParen[1] ?? '').trim();
      meta = `${meta} · ${(fullParen[2] ?? '').trim()}`;
    } else {
      const halfParen = action.match(/^(.+?)\((.+)\)$/);
      if (halfParen) {
        action = (halfParen[1] ?? '').trim();
        meta = `${meta} · ${(halfParen[2] ?? '').trim()}`;
      }
    }

    action = action.replace(/\[[^\]]*\]/g, '').replace(/（[^）]*）/g, '').replace(/\([^)]*\)/g, '').trim();

    return {
      raw: choice,
      action: limitActionText(action, 60),
      meta,
      tone: parseChoiceTone(text),
    };
  });
});

const sortedStats = computed<Array<{ key: string; value: number }>>(() => {
  return Object.keys(gameStore.currentStats)
    .filter((key) => !optionalAttributeKeys.has(key))
    .sort((a, b) => a.localeCompare(b))
    .map((key) => ({
      key,
      value: Math.round(displayedStats.value[key] ?? gameStore.currentStats[key] ?? 0),
    }));
});

const setupRows = computed(() => {
  const attrs = gameStore.selectedPreset?.attributes ?? [];
  return attrs.filter((item) => !optionalAttributeKeys.has(item.key));
});

const isCustomPreset = computed<boolean>(() => Boolean(gameStore.selectedPreset?.is_custom));

const canOperate = computed<boolean>(() => {
  return (
    gameStore.hasSession &&
    !gameStore.isEnded &&
    !gameStore.isActionPending &&
    !gameStore.hasPendingStorySegments
  );
});

const formatStatLabel = (key: string): string => {
  if (key === 'age') {
    return '当前年龄';
  }
  if (key === 'health') {
    return '健康';
  }
  return gameStore.statLabelMap[key] ?? key;
};

const getStatDelta = (key: string): number => Math.round(statDelta.value[key] ?? 0);

const getEventAccent = (content: string, role: 'system' | 'assistant' | 'user'): string => {
  if (role === 'user') {
    return 'bg-zinc-300';
  }
  if (role === 'system') {
    return 'bg-zinc-200';
  }
  if (/(成功|治愈|幸福|改善|收获|赢得|突破)/.test(content)) {
    return 'bg-green-200';
  }
  if (/(失败|死亡|崩溃|受伤|失去|破产|终局)/.test(content)) {
    return 'bg-red-200';
  }
  return 'bg-zinc-200';
};

const getStatTextTone = (key: string): string => {
  if (!changedStats.value.has(key)) {
    return 'text-zinc-800';
  }
  if (statTrend.value[key] === 'up') {
    return 'text-emerald-600';
  }
  if (statTrend.value[key] === 'down') {
    return 'text-red-600';
  }
  return 'text-zinc-800';
};

const notifyError = (fallback: string, error: unknown): void => {
  const message = (error as { message?: string }).message ?? fallback;
  window.dispatchEvent(
    new CustomEvent('app:toast', {
      detail: { type: 'error', message },
    }),
  );
};

const scrollFeedToBottom = (behavior: ScrollBehavior = 'smooth'): void => {
  const el = feedRef.value;
  if (!el) {
    return;
  }
  el.scrollTo({
    top: el.scrollHeight,
    behavior,
  });
};

const stopAutoScrollWhileTyping = (): void => {
  if (autoScrollTimer.value !== null) {
    window.clearInterval(autoScrollTimer.value);
    autoScrollTimer.value = null;
  }
};

const startAutoScrollWhileTyping = (): void => {
  stopAutoScrollWhileTyping();
  autoScrollTimer.value = window.setInterval(() => {
    scrollFeedToBottom('auto');
  }, 80);
};

const animateNumber = (key: string, from: number, to: number): void => {
  const delta = to - from;
  if (delta === 0) {
    displayedStats.value[key] = to;
    return;
  }
  const duration = 420;
  const start = performance.now();
  const tick = (now: number): void => {
    const progress = Math.min((now - start) / duration, 1);
    displayedStats.value[key] = from + delta * progress;
    if (progress < 1) {
      window.requestAnimationFrame(tick);
      return;
    }
    displayedStats.value[key] = to;
  };
  window.requestAnimationFrame(tick);
};

const adjustSetupAttribute = (key: string, delta: number, minValue: number, maxValue: number): void => {
  const currentValue = gameStore.setupAttributes[key] ?? minValue;
  const nextValue = Math.min(maxValue, Math.max(minValue, currentValue + delta));
  gameStore.setSetupAttribute(key, nextValue);
};

const beginWorld = async (): Promise<void> => {
  if (!gameStore.selectedPreset) {
    return;
  }
  startProcessingSince.value = Date.now();
  try {
    await gameStore.startSelectedWorld();
  } catch (error) {
    notifyError('进入世界失败，请稍后重试', error);
  } finally {
    startProcessingSince.value = null;
  }
};

const randomizeAttributes = (): void => {
  gameStore.randomizeSetupAttributes();
};

const runChoice = async (choice: string): Promise<void> => {
  if (!choice.trim() || !canOperate.value) {
    return;
  }
  customChoice.value = '';
  activeChoice.value = choice;
  gameplayProcessingSince.value = Date.now();
  try {
    await gameStore.runNextStep(choice.trim());
  } catch (error) {
    notifyError('推进失败，请稍后重试', error);
  } finally {
    gameplayProcessingSince.value = null;
    activeChoice.value = null;
  }
};

const retryChoice = async (): Promise<void> => {
  isRetryConfirmVisible.value = false;
  try {
    await gameStore.retryLastStep();
  } catch (error) {
    notifyError('重试失败，请稍后重试', error);
  }
};

const askRetryChoice = (): void => {
  if (!gameStore.retryChoice || !canOperate.value) {
    return;
  }
  isRetryConfirmVisible.value = true;
};

const onSubmitCustomChoice = async (): Promise<void> => {
  if (!customChoice.value.trim() || !canOperate.value) {
    return;
  }
  isSubmittingCustom.value = true;
  try {
    await runChoice(customChoice.value);
  } finally {
    isSubmittingCustom.value = false;
  }
};

const forceExitSession = async (): Promise<void> => {
  try {
    await gameStore.forceExitCurrentSession();
    window.dispatchEvent(
      new CustomEvent('app:toast', {
        detail: { type: 'info', message: '会话已结束，已生成总结。' },
      }),
    );
  } catch (error) {
    notifyError('强制退出失败，请稍后重试', error);
  }
};

const backToLobby = async (): Promise<void> => {
  gameStore.resetSession();
  await router.replace('/');
};

const revealNextSegment = (): void => {
  const revealed = gameStore.revealNextStorySegment();
  if (!revealed) {
    return;
  }
  nextTick(() => {
    scrollFeedToBottom('smooth');
  });
};

const markAssistantTyped = (eventId: number): void => {
  const next = new Set(typedAssistantIds.value);
  next.add(eventId);
  typedAssistantIds.value = next;
  stopAutoScrollWhileTyping();
  scrollFeedToBottom('smooth');
};

watch(
  () => gameStore.currentStats,
  (latest) => {
    const diff = new Set<string>();
    const nextTrend: Record<string, 'up' | 'down' | 'none'> = {};
    const nextDelta: Record<string, number> = {};

    Object.entries(latest).forEach(([key, value]) => {
      const previous = previousStats.value[key];
      const from = displayedStats.value[key] ?? previous ?? value;
      animateNumber(key, from, value);
      if (previous === undefined || previous === value) {
        nextTrend[key] = 'none';
        nextDelta[key] = 0;
        return;
      }
      const delta = value - previous;
      diff.add(key);
      nextTrend[key] = delta > 0 ? 'up' : 'down';
      nextDelta[key] = delta;
    });

    changedStats.value = diff;
    statTrend.value = nextTrend;
    statDelta.value = nextDelta;
    previousStats.value = { ...latest };
  },
  { deep: true, immediate: true },
);

watch(
  () => gameStore.storyEvents.length,
  () => {
    nextTick(() => {
      scrollFeedToBottom('smooth');
    });
  },
);

watch(
  latestAssistantId,
  (assistantId) => {
    if (!assistantId || typedAssistantIds.value.has(assistantId)) {
      stopAutoScrollWhileTyping();
      return;
    }
    nextTick(() => {
      scrollFeedToBottom('auto');
      startAutoScrollWhileTyping();
    });
  },
  { immediate: true },
);

watch(
  [startProcessingSince, gameplayProcessingSince],
  () => {
    const hasProcessing = Boolean(startProcessingSince.value || gameplayProcessingSince.value);
    if (hasProcessing && elapsedTimer.value === null) {
      elapsedTicker.value = Date.now();
      elapsedTimer.value = window.setInterval(() => {
        elapsedTicker.value = Date.now();
      }, 1000);
      return;
    }
    if (!hasProcessing && elapsedTimer.value !== null) {
      window.clearInterval(elapsedTimer.value);
      elapsedTimer.value = null;
    }
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  stopAutoScrollWhileTyping();
  if (elapsedTimer.value !== null) {
    window.clearInterval(elapsedTimer.value);
    elapsedTimer.value = null;
  }
});

onMounted(async () => {
  if (gameStore.hasSession) {
    return;
  }
  if (!gameStore.selectedPreset) {
    await router.replace('/');
  }
});
</script>

<template>
  <section v-if="!gameStore.hasSession" class="px-4 pb-16 pt-6 lg:pt-10">
    <div
      class="mx-auto mt-10 max-w-3xl rounded-3xl border border-zinc-100 bg-white/90 p-8 shadow-2xl shadow-zinc-200/50 backdrop-blur-2xl lg:p-12"
    >
      <header class="mb-10 space-y-3">
        <p class="text-xs font-semibold uppercase tracking-[0.28em] text-zinc-500">World Configuration</p>
        <h1 class="text-3xl font-bold tracking-tight text-zinc-900">开局配置</h1>
        <p v-if="gameStore.selectedPreset" class="text-sm leading-7 text-zinc-500">
          {{ gameStore.selectedPreset.title }} · {{ gameStore.selectedPreset.worldview }}
        </p>
        <p v-else class="text-sm leading-7 text-zinc-500">未选择预设，正在返回大厅...</p>
      </header>

      <div v-if="gameStore.selectedPreset" class="space-y-8">
        <div class="grid gap-6">
          <label class="grid gap-2 text-sm font-medium text-zinc-600">
            <span>人物设定</span>
            <select
              v-if="!isCustomPreset"
              v-model="gameStore.selectedCharacterSetting"
              class="w-full rounded-xl border border-zinc-200 bg-zinc-50/50 px-4 py-3 text-sm text-zinc-700 placeholder-zinc-400 transition-all focus:border-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-800/20"
            >
              <option v-for="option in gameStore.selectedPreset.character_options" :key="option" :value="option">
                {{ option }}
              </option>
            </select>
            <input
              v-else
              v-model="gameStore.customCharacterSetting"
              maxlength="500"
              class="w-full rounded-xl border border-zinc-200 bg-zinc-50/50 px-4 py-3 text-sm text-zinc-700 placeholder-zinc-400 transition-all focus:border-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-800/20"
              placeholder="输入你的角色设定（如：没背景但极度理性）"
            />
          </label>

          <label v-if="isCustomPreset" class="grid gap-2 text-sm font-medium text-zinc-600">
            <span>自定义世界设定</span>
            <textarea
              v-model="gameStore.customWorldview"
              maxlength="2000"
              rows="5"
              class="w-full rounded-xl border border-zinc-200 bg-zinc-50/50 px-4 py-3 text-sm text-zinc-700 placeholder-zinc-400 transition-all focus:border-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-800/20"
              placeholder="输入世界观、时代背景、规则与氛围"
            />
          </label>

          <label class="grid gap-2 text-sm font-medium text-zinc-600">
            <span>自定义提示词（可选）</span>
            <input
              v-model="gameStore.setupPrompt"
              maxlength="200"
              class="w-full rounded-xl border border-zinc-200 bg-zinc-50/50 px-4 py-3 text-sm text-zinc-700 placeholder-zinc-400 transition-all focus:border-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-800/20"
              placeholder="例如：希望剧情更偏成长线与现实主义"
            />
          </label>
        </div>

        <section class="space-y-5 rounded-[1.75rem] border border-zinc-200/60 bg-zinc-50/70 p-6 ring-1 ring-zinc-900/5">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p class="text-sm font-semibold text-zinc-800">
                可分配属性：{{ gameStore.setupAttributeTotal }} / {{ gameStore.setupAttributeLimit }}
              </p>
              <p class="mt-1 text-xs text-zinc-500">每一点都将影响你被世界回应的方式。</p>
            </div>
            <button
              type="button"
              class="inline-flex items-center justify-center rounded-xl border border-zinc-200/60 bg-white px-4 py-2 text-sm font-medium text-zinc-600 transition-all hover:border-zinc-300 hover:bg-zinc-100"
              :disabled="gameStore.isActionPending"
              @click="randomizeAttributes"
            >
              随机分配
            </button>
          </div>

          <div class="space-y-3">
            <div
              v-for="item in setupRows"
              :key="item.key"
              class="flex items-center justify-between rounded-2xl bg-white/80 px-4 py-3 ring-1 ring-zinc-900/5"
            >
              <div>
                <p class="text-sm font-medium text-zinc-700">{{ item.label }}</p>
                <p class="mt-1 text-xs text-zinc-400">范围 {{ item.min_value }} - {{ item.max_value }}</p>
              </div>
              <div class="flex items-center gap-3">
                <button
                  type="button"
                  class="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-100 text-zinc-600 transition-colors hover:bg-zinc-200"
                  @click="adjustSetupAttribute(item.key, -1, item.min_value, item.max_value)"
                >
                  -
                </button>
                <span class="min-w-[2.5rem] text-center text-base font-bold text-zinc-800">
                  {{ gameStore.setupAttributes[item.key] }}
                </span>
                <button
                  type="button"
                  class="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-100 text-zinc-600 transition-colors hover:bg-zinc-200"
                  @click="adjustSetupAttribute(item.key, 1, item.min_value, item.max_value)"
                >
                  +
                </button>
              </div>
            </div>
          </div>
        </section>

        <p v-if="!gameStore.isSetupValid" class="text-sm text-red-500">
          当前配置未满足要求，请检查属性总点与自定义输入内容。
        </p>

        <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
            <button
              type="button"
              class="rounded-xl bg-zinc-800 px-6 py-3 text-sm font-medium text-white transition-all duration-300 hover:bg-zinc-900 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="!gameStore.isSetupValid || gameStore.isActionPending"
              @click="beginWorld"
            >
              {{ gameStore.isActionPending ? '正在进入...' : '开始人生' }}
            </button>
            <span class="text-xs text-zinc-500">{{ startEtaText }}</span>
          </div>
          <button
            type="button"
            class="text-sm font-medium text-zinc-500 transition-colors hover:text-zinc-900"
            @click="router.push('/')"
          >
            返回大厅
          </button>
        </div>
      </div>
    </div>
  </section>

  <section v-else class="px-4 pb-20 pt-6 lg:pt-10">
    <div class="mx-auto flex max-w-7xl gap-6">
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

      <main class="min-w-0 flex-1">
        <div class="rounded-[2rem] border border-zinc-200/60 bg-white/75 p-5 shadow-[0_18px_60px_rgba(24,24,27,0.06)] ring-1 ring-zinc-900/5 backdrop-blur-xl lg:p-8">
          <header class="mb-8 flex flex-col gap-5 border-b border-zinc-100 pb-6 lg:flex-row lg:items-end lg:justify-between">
            <div class="space-y-2">
              <p class="text-xs font-semibold uppercase tracking-[0.28em] text-zinc-500">Observer Chronicle</p>
              <h1 class="text-3xl font-bold tracking-tight text-zinc-900">人生轨迹</h1>
              <p class="max-w-2xl text-sm leading-7 text-zinc-500">
                {{ gameStore.selectedPreset?.title }} ·
                {{ gameStore.selectedPreset?.worldview || '世界正在生成自己的命运纹理。' }}
              </p>
            </div>

            <div class="flex flex-wrap items-center gap-3">
              <button
                v-if="!gameStore.isEnded"
                type="button"
                class="rounded-xl border border-zinc-200/70 bg-white px-4 py-2 text-sm font-medium text-zinc-600 transition-all hover:border-zinc-300 hover:bg-zinc-50"
                :disabled="gameStore.isActionPending"
                @click="forceExitSession"
              >
                强制退出
              </button>
              <button
                type="button"
                class="rounded-xl bg-zinc-800 px-4 py-2 text-sm font-medium text-white transition-all duration-300 hover:bg-zinc-900 hover:shadow-md"
                @click="backToLobby"
              >
                返回大厅
              </button>
            </div>
          </header>

          <div class="flex flex-col gap-8 lg:flex-row">
            <section class="flex-1">
              <div ref="feedRef" class="max-h-[calc(100vh-17rem)] overflow-y-auto pr-2">
                <TransitionGroup name="list" tag="div" class="max-w-2xl mx-auto flex-grow pb-32">
                  <article
                    v-for="event in gameStore.storyEvents"
                    :key="event.id"
                    class="relative mb-8 pl-6"
                  >
                    <span
                      class="absolute bottom-1 left-0 top-1 w-[3px] rounded-full"
                      :class="getEventAccent(event.content, event.role)"
                    />
                    <p
                      v-if="event.role === 'system'"
                      class="mb-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-zinc-400"
                    >
                      SYSTEM
                    </p>
                    <p
                      v-else-if="event.role === 'user'"
                      class="mb-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-zinc-400"
                    >
                      CHOICE
                    </p>
                    <div class="text-[15px] leading-[2.2] tracking-wide text-zinc-700">
                      <TypewriterText
                        v-if="event.role === 'assistant'"
                        :text="event.content"
                        :speed="18"
                        :immediate="typedAssistantIds.has(event.id) || latestAssistantId !== event.id"
                        @done="markAssistantTyped(event.id)"
                      />
                      <span v-else>{{ event.content }}</span>
                    </div>
                    <p v-if="latestEventId === event.id && gameStore.isActionPending" class="mt-3 text-xs text-zinc-400">
                      正在推进命运分支...
                    </p>
                  </article>
                </TransitionGroup>
              </div>
            </section>

            <aside class="w-full space-y-5 lg:w-[24rem]">
              <section
                class="rounded-2xl border border-zinc-200/60 bg-zinc-50/80 p-5 ring-1 ring-zinc-900/5"
              >
                <p class="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">Current Situation</p>
                <p class="mt-3 text-[15px] leading-7 text-zinc-700">{{ currentSituation }}</p>
                <p v-if="gameStore.isActionPending" class="mt-3 text-xs text-zinc-500">{{ executeEtaText }}</p>
              </section>

              <section
                v-if="gameStore.hasPendingStorySegments"
                class="rounded-2xl border border-zinc-200/60 bg-white p-5 shadow-sm"
              >
                <p class="text-sm font-semibold text-zinc-800">还有 {{ gameStore.pendingStorySegments.length }} 段剧情未展开</p>
                <button
                  type="button"
                  class="mt-4 w-full rounded-xl bg-zinc-800 py-3 text-sm font-medium text-white transition-all duration-300 hover:bg-zinc-900 hover:shadow-md"
                  @click="revealNextSegment"
                >
                  继续阅读下一段
                </button>
              </section>

              <section v-if="!gameStore.isEnded" class="space-y-3">
                <button
                  v-for="choice in parsedChoices"
                  :key="choice.raw"
                  type="button"
                  class="flex w-full cursor-pointer items-start gap-4 rounded-xl border border-zinc-200 bg-white p-4 text-left shadow-sm transition-all hover:border-zinc-400 hover:bg-zinc-50 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="!canOperate"
                  @click="runChoice(choice.raw)"
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

              <section v-if="!gameStore.isEnded" class="space-y-3">
                <button
                  v-if="gameStore.retryChoice"
                  type="button"
                  class="w-full rounded-xl border border-zinc-200/70 bg-white px-4 py-3 text-sm font-medium text-zinc-600 transition-all hover:border-zinc-300 hover:bg-zinc-50 disabled:opacity-60"
                  :disabled="!canOperate"
                  @click="askRetryChoice"
                >
                  重试上一次推进
                </button>

                <form class="space-y-2" @submit.prevent="onSubmitCustomChoice">
                  <div class="relative mt-6 flex w-full items-center">
                    <input
                      v-model="customChoice"
                      :disabled="!canOperate"
                      maxlength="200"
                      class="w-full rounded-xl border border-zinc-300 bg-white py-3.5 pl-4 pr-24 text-sm text-zinc-700 shadow-sm transition-all focus:border-zinc-800 focus:ring-2 focus:ring-zinc-800/20"
                      placeholder="或输入你的自定义行动（最多 200 字）"
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
                v-if="gameStore.isEnded"
                class="rounded-2xl border border-zinc-200/60 bg-white p-5 shadow-sm"
              >
                <p class="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">End Summary</p>
                <h3 class="mt-3 text-xl font-bold text-zinc-900">人生总结</h3>
                <p class="mt-4 text-[15px] leading-8 text-zinc-700">
                  {{ gameStore.endSummary || '本次人生已结束。' }}
                </p>
                <button
                  type="button"
                  class="mt-6 rounded-xl bg-zinc-800 px-5 py-3 text-sm font-medium text-white transition-all duration-300 hover:bg-zinc-900 hover:shadow-md"
                  @click="backToLobby"
                >
                  返回大厅
                </button>
              </section>
            </aside>
          </div>
        </div>
      </main>
    </div>
  </section>

  <BaseModal :visible="isRetryConfirmVisible" title="确认重试本次推进？" @close="isRetryConfirmVisible = false">
    <div class="space-y-5">
      <p class="text-sm leading-7 text-zinc-500">
        重试将基于相同选择重新生成剧情，结果可能与上次不同。是否继续？
      </p>
      <div class="grid grid-cols-2 gap-3">
        <button
          type="button"
          class="rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm font-medium text-zinc-600 transition-all hover:bg-zinc-50"
          @click="isRetryConfirmVisible = false"
        >
          取消
        </button>
        <button
          type="button"
          class="rounded-xl bg-zinc-800 px-4 py-3 text-sm font-medium text-white transition-all duration-300 hover:bg-zinc-900 hover:shadow-md"
          :disabled="gameStore.isActionPending"
          @click="retryChoice"
        >
          {{ gameStore.isActionPending ? '处理中...' : '确认重试' }}
        </button>
      </div>
    </div>
  </BaseModal>
</template>
