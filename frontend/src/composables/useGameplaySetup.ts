import { computed, ref, watch } from 'vue';
import type { Router } from 'vue-router';
import { useGameStore } from '@/stores/useGameStore';
import type { GamePreset, StartGamePayload } from '@/types/game';

const normalizePromptInput = (value: string, maxLength: number): string => {
  return value.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '').replace(/\s+/g, ' ').trim().slice(0, maxLength);
};

export function useGameplaySetup(gameStore: ReturnType<typeof useGameStore>, router: Router) {
  const optionalAttributeKeys = new Set(['happiness', '幸福']);
  const selectedCharacterSetting = ref<string | null>(null);
  const setupPrompt = ref<string>('');
  const customWorldview = ref<string>('');
  const customCharacterSetting = ref<string>('');
  const setupAttributes = ref<Record<string, number>>({});

  const setupRows = computed(() => {
    const attributes = gameStore.selectedPreset?.attributes ?? [];
    return attributes.filter((item) => !optionalAttributeKeys.has(item.key));
  });

  const isCustomPreset = computed<boolean>(() => Boolean(gameStore.selectedPreset?.is_custom));

  const requiredSetupAttributes = computed(() => {
    const attributes = gameStore.selectedPreset?.attributes ?? [];
    return attributes.filter((item) => !optionalAttributeKeys.has(item.key));
  });

  const optionalDefaultPoints = computed<number>(() => {
    const attributes = gameStore.selectedPreset?.attributes ?? [];
    return attributes
      .filter((item) => optionalAttributeKeys.has(item.key))
      .reduce((accumulator, item) => accumulator + item.default_value, 0);
  });

  const setupAttributeTotal = computed<number>(() => {
    return Object.values(setupAttributes.value).reduce((accumulator, current) => accumulator + current, 0);
  });

  const setupAttributeLimit = computed<number>(() => {
    const maxPoints = gameStore.selectedPreset?.max_attribute_points ?? 0;
    return Math.max(maxPoints - optionalDefaultPoints.value, 0);
  });

  const isSetupValid = computed<boolean>(() => {
    if (!gameStore.selectedPreset) {
      return false;
    }
    if (setupAttributeTotal.value > setupAttributeLimit.value) {
      return false;
    }
    if (gameStore.selectedPreset.is_custom) {
      return (
        normalizePromptInput(customWorldview.value, 2000).length > 0 &&
        normalizePromptInput(customCharacterSetting.value, 500).length > 0
      );
    }
    return true;
  });

  const hydrateSetupState = (preset: GamePreset | null): void => {
    selectedCharacterSetting.value = preset?.character_options[0] ?? null;
    setupPrompt.value = '';
    customWorldview.value = preset?.is_custom ? preset.worldview : '';
    customCharacterSetting.value = '';
    setupAttributes.value = {};

    if (!preset) {
      return;
    }

    requiredSetupAttributes.value.forEach((item) => {
      setupAttributes.value[item.key] = item.default_value;
    });
  };

  watch(
    () => gameStore.selectedPreset,
    (preset) => {
      hydrateSetupState(preset);
    },
    { immediate: true },
  );

  const adjustSetupAttribute = (key: string, delta: number, minValue: number, maxValue: number): void => {
    const currentValue = setupAttributes.value[key] ?? minValue;
    const nextValue = Math.min(maxValue, Math.max(minValue, currentValue + delta));
    setupAttributes.value[key] = nextValue;
  };

  const randomizeAttributes = (): void => {
    if (!gameStore.selectedPreset) {
      return;
    }

    const attributes = requiredSetupAttributes.value;
    const totalLimit = setupAttributeLimit.value;
    const result: Record<string, number> = {};
    let remaining = totalLimit;

    attributes.forEach((item, index) => {
      const restCount = attributes.length - index - 1;
      const minNeededForRest = attributes
        .slice(index + 1)
        .reduce((accumulator, current) => accumulator + Math.max(0, current.min_value), 0);
      const maxAllowed = Math.max(item.min_value, Math.min(item.max_value, remaining - minNeededForRest));
      const minAllowed = Math.max(
        item.min_value,
        remaining - attributes.slice(index + 1).reduce((accumulator, current) => accumulator + current.max_value, 0),
      );
      const rangeStart = Math.min(minAllowed, maxAllowed);
      const rangeEnd = Math.max(minAllowed, maxAllowed);
      const value = restCount === 0
        ? Math.max(item.min_value, Math.min(item.max_value, remaining))
        : Math.floor(Math.random() * (rangeEnd - rangeStart + 1)) + rangeStart;
      result[item.key] = value;
      remaining -= value;
    });

    setupAttributes.value = result;
  };

  const backToHome = async (): Promise<void> => {
    await router.push('/');
  };

  const buildStartPayload = (): StartGamePayload => {
    const preset = gameStore.selectedPreset;
    if (!preset) {
      throw new Error('未选择世界预设');
    }

    return {
      preset_id: preset.id,
      selected_character_setting: selectedCharacterSetting.value,
      custom_worldview: preset.is_custom ? normalizePromptInput(customWorldview.value, 2000) || null : null,
      custom_character_setting: preset.is_custom
        ? normalizePromptInput(customCharacterSetting.value, 500) || null
        : null,
      allocated_attributes: setupAttributes.value,
      custom_prompt: normalizePromptInput(setupPrompt.value, 200) || null,
    };
  };

  return {
    adjustSetupAttribute,
    backToHome,
    buildStartPayload,
    customCharacterSetting,
    customWorldview,
    isCustomPreset,
    isSetupValid,
    randomizeAttributes,
    selectedCharacterSetting,
    setupAttributes,
    setupAttributeLimit,
    setupAttributeTotal,
    setupPrompt,
    setupRows,
  };
}
