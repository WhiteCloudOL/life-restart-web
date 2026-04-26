import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { forceExitGame, listPresets, nextGame, startGame } from '@/api/game';
import { useAuthStore } from '@/stores/useAuthStore';
import type { GamePreset, GameStepResponse, StartGamePayload, StoryEvent } from '@/types/game';

const FALLBACK_CHOICES = [
  '[高风险] 孤注一掷推进高收益计划：若成功将快速跃迁，但失败可能引发致命连锁后果并提前终局。',
  '[中风险] 采用博弈策略争取阶段收益：上限可观但容错一般，判断偏差会造成严重损失。',
  '[低风险] 选择稳健积累与资源修复：回报较慢但更可控，仍存在小概率突发终局风险。',
];

const buildChoices = (response: GameStepResponse): string[] => {
  if (Array.isArray(response.next_choices) && response.next_choices.length > 0) {
    return response.next_choices.slice(0, 3);
  }
  return FALLBACK_CHOICES;
};

export const useGameStore = defineStore('game', () => {
  const presets = ref<GamePreset[]>([]);
  const isLoadingPresets = ref<boolean>(false);
  const isActionPending = ref<boolean>(false);
  const sessionId = ref<number | null>(null);
  const isEnded = ref<boolean>(false);
  const currentStats = ref<Record<string, number>>({});
  const storyEvents = ref<StoryEvent[]>([]);
  const nextChoices = ref<string[]>(FALLBACK_CHOICES);
  const sequence = ref<number>(0);
  const selectedPresetId = ref<number | null>(null);
  const endReason = ref<string | null>(null);
  const endSummary = ref<string | null>(null);

  const hasSession = computed<boolean>(() => Boolean(sessionId.value));
  const selectedPreset = computed<GamePreset | null>(() => {
    if (selectedPresetId.value === null) {
      return null;
    }
    return presets.value.find((item) => item.id === selectedPresetId.value) ?? null;
  });

  const resetSession = (): void => {
    sessionId.value = null;
    isEnded.value = false;
    currentStats.value = {};
    storyEvents.value = [];
    nextChoices.value = FALLBACK_CHOICES;
    sequence.value = 0;
    endReason.value = null;
    endSummary.value = null;
  };

  const pushStoryEvent = (role: StoryEvent['role'], content: string): void => {
    sequence.value += 1;
    storyEvents.value.push({
      id: sequence.value,
      role,
      content,
    });
  };

  const applyStepResponse = (response: GameStepResponse): string[] => {
    sessionId.value = response.session_id;
    currentStats.value = response.current_stats ?? {};
    isEnded.value = response.is_ended;
    endReason.value = response.end_reason ?? null;
    endSummary.value = response.end_summary ?? null;
    nextChoices.value = buildChoices(response);

    const authStore = useAuthStore();
    authStore.syncQuota(
      response.world_entry_limit,
      response.world_entries_used_today,
      response.model_call_limit,
      response.model_calls_used_today,
    );

    return Array.isArray(response.event_segments) ? [...response.event_segments] : ['故事继续推进。'];
  };

  const fetchPresets = async (): Promise<void> => {
    isLoadingPresets.value = true;
    try {
      presets.value = await listPresets();
      if (selectedPresetId.value && !presets.value.some((item) => item.id === selectedPresetId.value)) {
        selectedPresetId.value = null;
      }
    } finally {
      isLoadingPresets.value = false;
    }
  };

  const preparePreset = (presetId: number): void => {
    selectedPresetId.value = presetId;
  };

  const startSelectedWorld = async (payload: StartGamePayload): Promise<string[]> => {
    isActionPending.value = true;
    resetSession();
    try {
      const presetSnapshot = selectedPreset.value;
      const response = await startGame(payload);
      pushStoryEvent('system', `进入世界：${presetSnapshot?.title ?? '未知世界'}`);
      return applyStepResponse(response);
    } finally {
      isActionPending.value = false;
    }
  };

  const runNextStep = async (choice: string): Promise<string[]> => {
    if (!sessionId.value) {
      return [];
    }

    isActionPending.value = true;
    try {
      pushStoryEvent('user', choice);
      const response = await nextGame({
        session_id: sessionId.value,
        user_choice: choice,
      });
      return applyStepResponse(response);
    } catch (error) {
      storyEvents.value = storyEvents.value.slice(0, Math.max(storyEvents.value.length - 1, 0));
      throw error;
    } finally {
      isActionPending.value = false;
    }
  };

  const forceExitCurrentSession = async (): Promise<void> => {
    if (!sessionId.value) {
      return;
    }

    isActionPending.value = true;
    try {
      const response = await forceExitGame({ session_id: sessionId.value });
      isEnded.value = true;
      endReason.value = response.end_reason ?? 'forced_exit';
      endSummary.value = response.end_summary ?? '本次会话已结束。';
      nextChoices.value = [];
      if (endSummary.value) {
        pushStoryEvent('assistant', endSummary.value);
      }
    } finally {
      isActionPending.value = false;
    }
  };

  return {
    currentStats,
    endReason,
    endSummary,
    fetchPresets,
    forceExitCurrentSession,
    hasSession,
    isActionPending,
    isEnded,
    isLoadingPresets,
    nextChoices,
    preparePreset,
    presets,
    pushStoryEvent,
    resetSession,
    runNextStep,
    selectedPreset,
    selectedPresetId,
    sessionId,
    startSelectedWorld,
    storyEvents,
  };
});
