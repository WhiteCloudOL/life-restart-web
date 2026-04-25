import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { forceExitGame, listPresets, nextGame, startGame } from '@/api/game';
import { useAuthStore } from '@/stores/useAuthStore';
import type { GamePreset, GameStepResponse, StoryEvent } from '@/types/game';

const FALLBACK_CHOICES = [
  '[高风险] 孤注一掷推进高收益计划：若成功将快速跃迁，但失败可能引发致命连锁后果并提前终局。',
  '[中风险] 采用博弈策略争取阶段收益：上限可观但容错一般，判断偏差会造成严重损失。',
  '[低风险] 选择稳健积累与资源修复：回报较慢但更可控，仍存在小概率突发终局风险。',
];

const buildChoices = (resp: GameStepResponse): string[] => {
  if (Array.isArray(resp.next_choices) && resp.next_choices.length > 0) {
    return resp.next_choices.slice(0, 3);
  }
  return FALLBACK_CHOICES;
};

const OPTIONAL_SETUP_ATTRIBUTE_KEYS = new Set(['happiness', '幸福']);

const isOptionalSetupAttribute = (key: string): boolean => OPTIONAL_SETUP_ATTRIBUTE_KEYS.has(key);

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
  const selectedCharacterSetting = ref<string | null>(null);
  const setupPrompt = ref<string>('');
  const customWorldview = ref<string>('');
  const customCharacterSetting = ref<string>('');
  const setupAttributes = ref<Record<string, number>>({});
  const statLabelMap = ref<Record<string, string>>({});
  const retryChoice = ref<string | null>(null);
  const endReason = ref<string | null>(null);
  const endSummary = ref<string | null>(null);
  const pendingStorySegments = ref<string[]>([]);

  const hasSession = computed<boolean>(() => Boolean(sessionId.value));
  const hasPendingStorySegments = computed<boolean>(() => pendingStorySegments.value.length > 0);
  const selectedPreset = computed<GamePreset | null>(() => {
    if (selectedPresetId.value === null) {
      return null;
    }
    return presets.value.find((item) => item.id === selectedPresetId.value) ?? null;
  });

  const requiredSetupAttributes = computed(() => {
    const attrs = selectedPreset.value?.attributes ?? [];
    return attrs.filter((item) => !isOptionalSetupAttribute(item.key));
  });

  const optionalDefaultPoints = computed<number>(() => {
    const attrs = selectedPreset.value?.attributes ?? [];
    return attrs
      .filter((item) => isOptionalSetupAttribute(item.key))
      .reduce((acc, item) => acc + item.default_value, 0);
  });

  const setupAttributeTotal = computed<number>(() => {
    return Object.values(setupAttributes.value).reduce((acc, cur) => acc + cur, 0);
  });

  const setupAttributeLimit = computed<number>(() => {
    const maxPoints = selectedPreset.value?.max_attribute_points ?? 0;
    return Math.max(maxPoints - optionalDefaultPoints.value, 0);
  });
  const isSetupValid = computed<boolean>(() => {
    if (!selectedPreset.value) {
      return false;
    }
    const basicValid = setupAttributeTotal.value <= setupAttributeLimit.value;
    if (!basicValid) {
      return false;
    }
    if (selectedPreset.value.is_custom) {
      return customWorldview.value.trim().length > 0 && customCharacterSetting.value.trim().length > 0;
    }
    return true;
  });

  const resetSession = (): void => {
    sessionId.value = null;
    isEnded.value = false;
    currentStats.value = {};
    storyEvents.value = [];
    nextChoices.value = FALLBACK_CHOICES;
    sequence.value = 0;
    retryChoice.value = null;
    pendingStorySegments.value = [];
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

  const revealNextStorySegment = (): boolean => {
    if (pendingStorySegments.value.length === 0) {
      return false;
    }
    const segment = pendingStorySegments.value.shift();
    if (!segment) {
      return false;
    }
    pushStoryEvent('assistant', segment);
    return true;
  };

  const applyStepResponse = (resp: GameStepResponse): void => {
    sessionId.value = resp.session_id;
    currentStats.value = resp.current_stats ?? {};
    isEnded.value = resp.is_ended;
    endReason.value = resp.end_reason ?? null;
    endSummary.value = resp.end_summary ?? null;
    nextChoices.value = buildChoices(resp);

    const authStore = useAuthStore();
    authStore.syncQuota(
      resp.world_entry_limit,
      resp.world_entries_used_today,
      resp.model_call_limit,
      resp.model_calls_used_today,
    );

    pendingStorySegments.value = Array.isArray(resp.event_segments)
      ? [...resp.event_segments]
      : ['故事继续推进。'];
    revealNextStorySegment();
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
    const preset = presets.value.find((item) => item.id === presetId) ?? null;
    selectedPresetId.value = presetId;
    selectedCharacterSetting.value = preset?.character_options[0] ?? null;
    setupPrompt.value = '';
    customWorldview.value = preset?.is_custom ? preset.worldview : '';
    customCharacterSetting.value = '';
    setupAttributes.value = {};
    statLabelMap.value = {};

    if (!preset) {
      return;
    }
    preset.attributes.forEach((item) => {
      statLabelMap.value[item.key] = item.label;
    });
    requiredSetupAttributes.value.forEach((item) => {
      setupAttributes.value[item.key] = item.default_value;
    });
  };

  const setSetupAttribute = (key: string, value: number): void => {
    setupAttributes.value[key] = value;
  };

  const randomizeSetupAttributes = (): void => {
    if (!selectedPreset.value) {
      return;
    }
    const attrs = requiredSetupAttributes.value;
    const totalLimit = setupAttributeLimit.value;
    const result: Record<string, number> = {};
    let remaining = totalLimit;

    attrs.forEach((item, index) => {
      const rest = attrs.length - index - 1;
      const minNeed = attrs
        .slice(index + 1)
        .reduce((acc, cur) => acc + Math.max(0, cur.min_value), 0);
      const upperBound = Math.max(
        item.min_value,
        Math.min(item.max_value, remaining - minNeed),
      );
      const lowerBound = Math.max(
        item.min_value,
        remaining - attrs.slice(index + 1).reduce((acc, cur) => acc + cur.max_value, 0),
      );
      const start = Math.min(lowerBound, upperBound);
      const end = Math.max(lowerBound, upperBound);
      const value = rest === 0
        ? Math.max(item.min_value, Math.min(item.max_value, remaining))
        : Math.floor(Math.random() * (end - start + 1)) + start;
      result[item.key] = value;
      remaining -= value;
    });

    setupAttributes.value = result;
  };

  const startSelectedWorld = async (): Promise<number> => {
    if (!selectedPreset.value || !isSetupValid.value) {
      throw new Error('当前开局配置无效');
    }

    isActionPending.value = true;
    resetSession();
    try {
      const resp = await startGame({
        preset_id: selectedPreset.value.id,
        selected_character_setting: selectedCharacterSetting.value,
        custom_worldview: selectedPreset.value.is_custom ? customWorldview.value.trim() || null : null,
        custom_character_setting: selectedPreset.value.is_custom ? customCharacterSetting.value.trim() || null : null,
        allocated_attributes: setupAttributes.value,
        custom_prompt: setupPrompt.value.trim() || null,
      });
      pushStoryEvent('system', `进入世界：${selectedPreset.value.title}`);
      applyStepResponse(resp);
      return resp.session_id;
    } finally {
      isActionPending.value = false;
    }
  };

  const runNextStep = async (choice: string, isRetry = false): Promise<void> => {
    if (!sessionId.value) {
      return;
    }
    if (hasPendingStorySegments.value) {
      throw new Error('请先手动点击继续，阅读完当前剧情段落后再做下一次选择');
    }

    isActionPending.value = true;
    const previousLength = storyEvents.value.length;
    try {
      pushStoryEvent('user', choice);
      const resp = await nextGame({
        session_id: sessionId.value,
        user_choice: choice,
      });
      applyStepResponse(resp);
      retryChoice.value = null;
    } catch (error) {
      storyEvents.value = storyEvents.value.slice(0, previousLength);
      if (!isRetry) {
        retryChoice.value = choice;
      }
      throw error;
    } finally {
      isActionPending.value = false;
    }
  };

  const retryLastStep = async (): Promise<void> => {
    if (!retryChoice.value) {
      return;
    }
    await runNextStep(retryChoice.value, true);
  };

  const forceExitCurrentSession = async (): Promise<void> => {
    if (!sessionId.value) {
      return;
    }
    isActionPending.value = true;
    try {
      const resp = await forceExitGame({ session_id: sessionId.value });
      isEnded.value = true;
      endReason.value = resp.end_reason ?? 'forced_exit';
      endSummary.value = resp.end_summary ?? '本次会话已结束。';
      nextChoices.value = [];
      pendingStorySegments.value = [];
      retryChoice.value = null;
      if (endSummary.value) {
        pushStoryEvent('assistant', endSummary.value);
      }
    } finally {
      isActionPending.value = false;
    }
  };

  return {
    presets,
    isLoadingPresets,
    isActionPending,
    sessionId,
    isEnded,
    currentStats,
    storyEvents,
    nextChoices,
    hasSession,
    selectedPresetId,
    selectedPreset,
    selectedCharacterSetting,
    setupPrompt,
    customWorldview,
    customCharacterSetting,
    setupAttributes,
    statLabelMap,
    setupAttributeTotal,
    setupAttributeLimit,
    isSetupValid,
    retryChoice,
    endReason,
    endSummary,
    pendingStorySegments,
    hasPendingStorySegments,
    resetSession,
    fetchPresets,
    preparePreset,
    setSetupAttribute,
    randomizeSetupAttributes,
    startSelectedWorld,
    runNextStep,
    retryLastStep,
    forceExitCurrentSession,
    revealNextStorySegment,
    pushStoryEvent,
  };
});
