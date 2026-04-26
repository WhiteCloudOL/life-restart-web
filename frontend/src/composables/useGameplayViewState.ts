import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import type { Router } from 'vue-router';
import { useGameStore } from '@/stores/useGameStore';
import type { StartGamePayload } from '@/types/game';

type ChoiceTone = 'high' | 'medium' | 'low';

const OPTIONAL_ATTRIBUTE_KEYS = new Set(['happiness', '幸福']);

export function useGameplayViewState(gameStore: ReturnType<typeof useGameStore>, router: Router) {
  const customChoice = ref<string>('');
  const isRetryConfirmVisible = ref<boolean>(false);
  const changedStats = ref<Set<string>>(new Set());
  const statTrend = ref<Record<string, 'up' | 'down' | 'none'>>({});
  const statDelta = ref<Record<string, number>>({});
  const previousStats = ref<Record<string, number>>({});
  const displayedStats = ref<Record<string, number>>({});
  const typedAssistantIds = ref<Set<number>>(new Set());
  const retryChoiceValue = ref<string | null>(null);
  const pendingStorySegments = ref<string[]>([]);
  const activeChoice = ref<string | null>(null);
  const isSubmittingCustom = ref<boolean>(false);
  const feedRef = ref<HTMLElement | null>(null);
  const autoScrollTimer = ref<number | null>(null);
  const elapsedTicker = ref<number>(Date.now());
  const elapsedTimer = ref<number | null>(null);
  const startProcessingSince = ref<number | null>(null);
  const gameplayProcessingSince = ref<number | null>(null);

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
    for (let index = list.length - 1; index >= 0; index -= 1) {
      const item = list[index];
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
    low: 'bg-emerald-50 text-emerald-600 ring-1 ring-emerald-100',
    medium: 'bg-amber-50 text-amber-600 ring-1 ring-amber-100',
  };

  const parsedChoices = computed<Array<{ raw: string; action: string; meta: string; tone: ChoiceTone }>>(() => {
    const limitActionText = (value: string, max = 60): string => {
      const characters = Array.from(value);
      if (characters.length <= max) {
        return value;
      }
      return `${characters.slice(0, max).join('')}...`;
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
      .filter((key) => !OPTIONAL_ATTRIBUTE_KEYS.has(key))
      .sort((left, right) => left.localeCompare(right))
      .map((key) => ({
        key,
        value: Math.round(displayedStats.value[key] ?? gameStore.currentStats[key] ?? 0),
      }));
  });

  const canOperate = computed<boolean>(() => {
    return gameStore.hasSession && !gameStore.isEnded && !gameStore.isActionPending && pendingStorySegments.value.length === 0;
  });

  const formatStatLabel = (key: string): string => {
    if (key === 'age') {
      return '当前年龄';
    }
    if (key === 'health') {
      return '健康';
    }
    const attribute = gameStore.selectedPreset?.attributes.find((item) => item.key === key);
    return attribute?.label ?? key;
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
        detail: { message, type: 'error' },
      }),
    );
  };

  const scrollFeedToBottom = (behavior: ScrollBehavior = 'smooth'): void => {
    const element = feedRef.value;
    if (!element) {
      return;
    }
    element.scrollTo({
      behavior,
      top: element.scrollHeight,
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
    const startedAt = performance.now();
    const tick = (currentTime: number): void => {
      const progress = Math.min((currentTime - startedAt) / duration, 1);
      displayedStats.value[key] = from + delta * progress;
      if (progress < 1) {
        window.requestAnimationFrame(tick);
        return;
      }
      displayedStats.value[key] = to;
    };
    window.requestAnimationFrame(tick);
  };

  const revealNextSegment = (): void => {
    const segment = pendingStorySegments.value.shift();
    if (!segment) {
      return;
    }
    gameStore.pushStoryEvent('assistant', segment);
    nextTick(() => {
      scrollFeedToBottom('smooth');
    });
  };

  const beginWorld = async (payload: StartGamePayload): Promise<void> => {
    startProcessingSince.value = Date.now();
    try {
      const eventSegments = await gameStore.startSelectedWorld(payload);
      pendingStorySegments.value = eventSegments;
      revealNextSegment();
    } catch (error) {
      notifyError('进入世界失败，请稍后重试', error);
    } finally {
      startProcessingSince.value = null;
    }
  };

  const runChoice = async (choice: string): Promise<void> => {
    if (!choice.trim() || !canOperate.value) {
      return;
    }
    customChoice.value = '';
    activeChoice.value = choice;
    gameplayProcessingSince.value = Date.now();
    try {
      const eventSegments = await gameStore.runNextStep(choice.trim());
      pendingStorySegments.value = eventSegments;
      revealNextSegment();
      retryChoiceValue.value = null;
    } catch (error) {
      retryChoiceValue.value = choice;
      notifyError('推进失败，请稍后重试', error);
    } finally {
      gameplayProcessingSince.value = null;
      activeChoice.value = null;
    }
  };

  const retryChoice = async (): Promise<void> => {
    isRetryConfirmVisible.value = false;
    if (!retryChoiceValue.value) {
      return;
    }
    try {
      await runChoice(retryChoiceValue.value);
    } catch (error) {
      notifyError('重试失败，请稍后重试', error);
    }
  };

  const askRetryChoice = (): void => {
    if (!retryChoiceValue.value || !canOperate.value) {
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
      pendingStorySegments.value = [];
      retryChoiceValue.value = null;
      window.dispatchEvent(
        new CustomEvent('app:toast', {
          detail: { message: '会话已结束，已生成总结。', type: 'info' },
        }),
      );
    } catch (error) {
      notifyError('强制退出失败，请稍后重试', error);
    }
  };

  const backToLobby = async (): Promise<void> => {
    gameStore.resetSession();
    pendingStorySegments.value = [];
    retryChoiceValue.value = null;
    await router.replace('/');
  };

  const markAssistantTyped = (eventId: number): void => {
    const nextIds = new Set(typedAssistantIds.value);
    nextIds.add(eventId);
    typedAssistantIds.value = nextIds;
    stopAutoScrollWhileTyping();
    scrollFeedToBottom('smooth');
  };

  watch(
    () => gameStore.currentStats,
    (latest) => {
      const changed = new Set<string>();
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
        changed.add(key);
        nextTrend[key] = delta > 0 ? 'up' : 'down';
        nextDelta[key] = delta;
      });

      changedStats.value = changed;
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

  return {
    activeChoice,
    askRetryChoice,
    backToLobby,
    beginWorld,
    canOperate,
    currentSituation,
    customChoice,
    executeEtaText,
    feedRef,
    forceExitSession,
    formatStatLabel,
    getEventAccent,
    getStatDelta,
    getStatTextTone,
    isRetryConfirmVisible,
    isSubmittingCustom,
    latestAssistantId,
    latestEventId,
    markAssistantTyped,
    onSubmitCustomChoice,
    parsedChoices,
    pendingStorySegments,
    revealNextSegment,
    retryChoice,
    retryChoiceValue,
    runChoice,
    sortedStats,
    startEtaText,
    toneClasses,
    typedAssistantIds,
  };
}
