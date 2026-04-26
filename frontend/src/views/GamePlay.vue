<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import BaseModal from '@/components/BaseModal.vue';
import GameplayActionPanel from '@/components/gameplay/GameplayActionPanel.vue';
import GameplaySetupPanel from '@/components/gameplay/GameplaySetupPanel.vue';
import GameplayStatsPanel from '@/components/gameplay/GameplayStatsPanel.vue';
import GameplayStoryFeed from '@/components/gameplay/GameplayStoryFeed.vue';
import { useGameplaySetup } from '@/composables/useGameplaySetup';
import { useGameplayViewState } from '@/composables/useGameplayViewState';
import { useGameStore } from '@/stores/useGameStore';

const gameStore = useGameStore();
const router = useRouter();

const {
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
} = useGameplaySetup(gameStore, router);

const {
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
} = useGameplayViewState(gameStore, router);

const handleBeginWorld = async (): Promise<void> => {
  await beginWorld(buildStartPayload());
};

const handleFeedBind = (element: HTMLElement | null): void => {
  feedRef.value = element;
};

const handlePromptUpdate = (value: string): void => {
  setupPrompt.value = value;
};

const handleWorldviewUpdate = (value: string): void => {
  customWorldview.value = value;
};

const handleCharacterSettingUpdate = (value: string): void => {
  customCharacterSetting.value = value;
};

const handleSelectedOptionUpdate = (value: string): void => {
  selectedCharacterSetting.value = value;
};

const handleCustomChoiceUpdate = (value: string): void => {
  customChoice.value = value;
};

const closeRetryConfirm = (): void => {
  isRetryConfirmVisible.value = false;
};

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
  <GameplaySetupPanel
    v-if="!gameStore.hasSession"
    :can-start="isSetupValid"
    :current-character-setting="customCharacterSetting"
    :current-prompt="setupPrompt"
    :current-selected-option="selectedCharacterSetting"
    :current-worldview="customWorldview"
    :is-action-pending="gameStore.isActionPending"
    :is-custom-preset="isCustomPreset"
    :preset="gameStore.selectedPreset"
    :setup-attribute-limit="setupAttributeLimit"
    :setup-attribute-total="setupAttributeTotal"
    :setup-rows="setupRows"
    :setup-values="setupAttributes"
    :start-eta-text="startEtaText"
    @adjust-attribute="adjustSetupAttribute($event.key, $event.delta, $event.minValue, $event.maxValue)"
    @back-home="backToHome"
    @begin-world="handleBeginWorld"
    @randomize-attributes="randomizeAttributes"
    @update:character-setting="handleCharacterSettingUpdate"
    @update:prompt="handlePromptUpdate"
    @update:selected-option="handleSelectedOptionUpdate"
    @update:worldview="handleWorldviewUpdate"
  />

  <section v-else class="px-4 pb-20 pt-6 lg:pt-10">
    <div class="mx-auto flex max-w-7xl gap-6">
      <GameplayStatsPanel
        :format-stat-label="formatStatLabel"
        :get-stat-delta="getStatDelta"
        :get-stat-text-tone="getStatTextTone"
        :sorted-stats="sortedStats"
      />

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
          </header>

          <div class="flex flex-col gap-8 lg:flex-row">
            <GameplayStoryFeed
              :events="gameStore.storyEvents"
              :get-event-accent="getEventAccent"
              :is-action-pending="gameStore.isActionPending"
              :latest-assistant-id="latestAssistantId"
              :latest-event-id="latestEventId"
              :typed-assistant-ids="typedAssistantIds"
              @assistant-done="markAssistantTyped"
              @bind-feed="handleFeedBind"
            />

            <GameplayActionPanel
              :active-choice="activeChoice"
              :can-operate="canOperate"
              :current-situation="currentSituation"
              :custom-choice="customChoice"
              :end-summary="gameStore.endSummary"
              :execute-eta-text="executeEtaText"
              :has-pending-story-segments="pendingStorySegments.length > 0"
              :is-action-pending="gameStore.isActionPending"
              :is-ended="gameStore.isEnded"
              :is-submitting-custom="isSubmittingCustom"
              :next-pending-segments-count="pendingStorySegments.length"
              :parsed-choices="parsedChoices"
              :retry-choice-value="retryChoiceValue"
              :tone-classes="toneClasses"
              @ask-retry="askRetryChoice"
              @back-lobby="backToLobby"
              @force-exit="forceExitSession"
              @reveal-segment="revealNextSegment"
              @run-choice="runChoice"
              @submit-custom="onSubmitCustomChoice"
              @update:custom-choice="handleCustomChoiceUpdate"
            />
          </div>
        </div>
      </main>
    </div>
  </section>

  <BaseModal :visible="isRetryConfirmVisible" title="确认重试本次推进？" @close="closeRetryConfirm">
    <div class="space-y-5">
      <p class="text-sm leading-7 text-zinc-500">
        重试将基于相同选择重新生成剧情，结果可能与上次不同。是否继续？
      </p>
      <div class="grid grid-cols-2 gap-3">
        <button
          type="button"
          class="rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm font-medium text-zinc-600 transition-all hover:bg-zinc-50"
          @click="closeRetryConfirm"
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
