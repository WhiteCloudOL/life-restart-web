<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import BaseButton from '@/components/BaseButton.vue';
import BaseModal from '@/components/BaseModal.vue';
import TypewriterText from '@/components/TypewriterText.vue';
import { useGameStore } from '@/stores/useGameStore';

const gameStore = useGameStore();
const router = useRouter();

const customChoice = ref<string>('');
const isRetryConfirmVisible = ref<boolean>(false);
const changedStats = ref<Set<string>>(new Set());
const statTrend = ref<Record<string, 'up' | 'down' | 'none'>>({});
const previousStats = ref<Record<string, number>>({});
const displayedStats = ref<Record<string, number>>({});
const typedAssistantIds = ref<Set<number>>(new Set());
const activeChoice = ref<string | null>(null);
const isSubmittingCustom = ref<boolean>(false);
const feedRef = ref<HTMLElement | null>(null);
const autoScrollTimer = ref<number | null>(null);

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
    if (!item) {
      continue;
    }
    if (item.role === 'assistant') {
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
  return compact.length > 40 ? `${compact.slice(0, 40)}...` : compact;
});

const parsedChoices = computed<Array<{ raw: string; action: string; meta: string }>>(() => {
  const limitActionText = (value: string, max = 50): string => {
    const chars = Array.from(value);
    if (chars.length <= max) {
      return value;
    }
    return `${chars.slice(0, max).join('')}...`;
  };

  return gameStore.nextChoices.map((choice) => {
    const text = choice.replace(/\s+/g, ' ').trim();
    let action = text;
    let meta = '难度/机会信息待探索';

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

    // 主文本仅保留行动描述，去除残留中括号标签，并限制 50 字。
    action = action.replace(/\[[^\]]*\]/g, '').replace(/（[^）]*）/g, '').replace(/\([^)]*\)/g, '').trim();
    action = limitActionText(action, 50);

    return {
      raw: choice,
      action,
      meta,
    };
  });
});

const sortedStats = computed<Array<{ key: string; value: number }>>(() => {
  return Object.keys(gameStore.currentStats)
    .sort((a, b) => a.localeCompare(b))
    .map((key) => ({
      key,
      value: Math.round(displayedStats.value[key] ?? gameStore.currentStats[key] ?? 0),
    }));
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

const setupRows = computed(() => gameStore.selectedPreset?.attributes ?? []);
const isCustomPreset = computed<boolean>(() => Boolean(gameStore.selectedPreset?.is_custom));

const canOperate = computed<boolean>(() => {
  return (
    gameStore.hasSession &&
    !gameStore.isEnded &&
    !gameStore.isActionPending &&
    !gameStore.hasPendingStorySegments
  );
});

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

const beginWorld = async (): Promise<void> => {
  if (!gameStore.selectedPreset) {
    return;
  }
  try {
    await gameStore.startSelectedWorld();
  } catch (error) {
    notifyError('进入世界失败，请稍后重试', error);
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
  try {
    await gameStore.runNextStep(choice.trim());
  } catch (error) {
    notifyError('推进失败，请稍后重试', error);
  } finally {
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

    Object.entries(latest).forEach(([key, value]) => {
      const previous = previousStats.value[key];
      const from = displayedStats.value[key] ?? previous ?? value;
      animateNumber(key, from, value);
      if (previous === undefined || previous === value) {
        nextTrend[key] = 'none';
        return;
      }
      diff.add(key);
      nextTrend[key] = value > previous ? 'up' : 'down';
    });

    changedStats.value = diff;
    statTrend.value = nextTrend;
    previousStats.value = { ...latest };

    if (diff.size > 0) {
      window.setTimeout(() => {
        changedStats.value = new Set();
        statTrend.value = {};
      }, 650);
    }
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
    if (!assistantId) {
      stopAutoScrollWhileTyping();
      return;
    }
    if (typedAssistantIds.value.has(assistantId)) {
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

onBeforeUnmount(() => {
  stopAutoScrollWhileTyping();
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
  <section v-if="!gameStore.hasSession" class="setup-panel">
    <header>
      <h2>开局配置</h2>
      <p v-if="gameStore.selectedPreset">
        {{ gameStore.selectedPreset.title }} · {{ gameStore.selectedPreset.worldview }}
      </p>
      <p v-else>未选择预设，正在返回大厅...</p>
    </header>

    <div v-if="gameStore.selectedPreset" class="setup-grid">
      <label>
        人物设定
        <select v-if="!isCustomPreset" v-model="gameStore.selectedCharacterSetting">
          <option v-for="option in gameStore.selectedPreset.character_options" :key="option" :value="option">
            {{ option }}
          </option>
        </select>
        <input
          v-else
          v-model="gameStore.customCharacterSetting"
          maxlength="500"
          placeholder="输入你的角色设定（如：没背景但极度理性）"
        />
      </label>

      <label v-if="isCustomPreset">
        自定义世界设定
        <textarea
          v-model="gameStore.customWorldview"
          maxlength="2000"
          rows="4"
          placeholder="输入世界观、时代背景、规则与氛围"
        />
      </label>

      <label>
        自定义提示词（可选）
        <input v-model="gameStore.setupPrompt" maxlength="200" placeholder="例如：希望剧情更偏成长线与现实主义" />
      </label>

      <div class="attrs">
        <p class="attrs-title">
          可分配属性：{{ gameStore.setupAttributeTotal }} / {{ gameStore.setupAttributeLimit }}
        </p>
        <div class="attr-tools">
          <button type="button" class="ghost" :disabled="gameStore.isActionPending" @click="randomizeAttributes">
            随机分配
          </button>
        </div>
        <div class="attr-row" v-for="item in setupRows" :key="item.key">
          <span>{{ item.label }}</span>
          <input
            type="number"
            :min="item.min_value"
            :max="item.max_value"
            :value="gameStore.setupAttributes[item.key]"
            @change="
              (event) => {
                const value = Number((event.target as HTMLInputElement).value);
                gameStore.setSetupAttribute(item.key, Number.isFinite(value) ? value : item.default_value);
              }
            "
          />
        </div>
      </div>

      <p v-if="!gameStore.isSetupValid" class="warn">当前配置未满足要求，请检查属性总点与自定义输入内容。</p>

      <div class="setup-actions">
        <BaseButton :loading="gameStore.isActionPending" :disabled="!gameStore.isSetupValid" @click="beginWorld">
          开始人生
        </BaseButton>
        <button type="button" class="ghost" @click="router.push('/')">返回大厅</button>
      </div>
    </div>
  </section>

  <section v-else class="session-shell">
    <aside class="stats-panel">
      <h3>实时属性</h3>
      <ul>
        <li
          v-for="item in sortedStats"
          :key="item.key"
          :class="[
            changedStats.has(item.key) ? 'changed' : '',
            statTrend[item.key] === 'up' ? 'is-up' : '',
            statTrend[item.key] === 'down' ? 'is-down' : '',
          ]"
        >
          <span>{{ formatStatLabel(item.key) }}</span>
          <strong>{{ item.value }}</strong>
        </li>
      </ul>
    </aside>

    <main class="story-panel">
      <h3>人生轨迹</h3>
      <p v-if="gameStore.isActionPending" class="status-text">AI 正在推进故事，请稍候...</p>

      <div ref="feedRef" class="feed">
        <article
          v-for="event in gameStore.storyEvents"
          :key="event.id"
          class="bubble"
          :class="[
            `is-${event.role}`,
            latestEventId === event.id ? 'is-latest' : 'is-past',
          ]"
        >
          <TypewriterText
            v-if="event.role === 'assistant'"
            :text="event.content"
            :speed="18"
            :immediate="typedAssistantIds.has(event.id) || latestAssistantId !== event.id"
            @done="markAssistantTyped(event.id)"
          />
          <span v-else>{{ event.content }}</span>
        </article>
      </div>

      <footer class="action-bar">
        <div v-if="gameStore.hasPendingStorySegments" class="segment-actions">
          <BaseButton type="button" @click="revealNextSegment">
            继续阅读下一段（剩余 {{ gameStore.pendingStorySegments.length }} 段）
          </BaseButton>
        </div>

        <p class="situation-title">当前面临情况</p>
        <p class="situation-text">{{ currentSituation }}</p>

        <div v-if="!gameStore.isEnded" class="choices">
          <button
            v-for="choice in parsedChoices"
            :key="choice.raw"
            type="button"
            :disabled="!canOperate"
            @click="runChoice(choice.raw)"
          >
            <span class="choice-main">{{ choice.action }}</span>
            <span class="choice-meta">{{ choice.meta }}</span>
            <span v-if="activeChoice === choice.raw" class="mini-loading" />
          </button>
        </div>

        <div v-if="!gameStore.isEnded && gameStore.retryChoice" class="retry-wrap">
          <button type="button" :disabled="!canOperate" @click="askRetryChoice">重试上一次推进</button>
        </div>

        <div class="retry-wrap">
          <button
            v-if="!gameStore.isEnded"
            type="button"
            :disabled="gameStore.isActionPending"
            @click="forceExitSession"
          >
            强制退出当前游戏
          </button>
        </div>

        <div v-if="gameStore.isEnded" class="end-summary">
          <p class="end-title">人生总结</p>
          <p class="end-text">{{ gameStore.endSummary || '本次人生已结束。' }}</p>
          <div class="end-actions">
            <BaseButton type="button" @click="backToLobby">返回大厅</BaseButton>
          </div>
        </div>

        <form v-if="!gameStore.isEnded" class="custom-form" @submit.prevent="onSubmitCustomChoice">
          <input
            v-model="customChoice"
            :disabled="!canOperate"
            maxlength="200"
            placeholder="或输入你的自定义行动（最多 200 字）"
          />
          <BaseButton type="submit" :loading="isSubmittingCustom" :disabled="!canOperate || !customChoice.trim()">
            执行
          </BaseButton>
        </form>
      </footer>
    </main>
  </section>

  <BaseModal :visible="isRetryConfirmVisible" title="确认重试本次推进？" @close="isRetryConfirmVisible = false">
    <p class="confirm-text">
      重试将基于相同选择重新生成剧情，结果可能与上次不同。是否继续？
    </p>
    <div class="confirm-actions">
      <button type="button" class="ghost" @click="isRetryConfirmVisible = false">取消</button>
      <BaseButton type="button" :loading="gameStore.isActionPending" @click="retryChoice">确认重试</BaseButton>
    </div>
  </BaseModal>
</template>

<style scoped>
.setup-panel {
  padding: 22px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: var(--panel);
  backdrop-filter: blur(14px);
  display: grid;
  gap: 12px;
  box-shadow: var(--shadow-soft);
}

.setup-panel h2 {
  margin: 0;
  color: var(--title);
  font-family: var(--font-serif);
}

.setup-grid {
  display: grid;
  gap: 12px;
}

.setup-grid label {
  display: grid;
  gap: 6px;
}

.setup-grid select,
.setup-grid input {
  height: 42px;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 0 12px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--text);
}

.setup-grid textarea {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--text);
  resize: vertical;
}

.setup-grid select:focus,
.setup-grid input:focus {
  outline: 2px solid rgba(42, 157, 143, 0.3);
  outline-offset: 1px;
}

.attrs {
  display: grid;
  gap: 8px;
}

.attrs-title {
  margin: 0;
  color: var(--subtext);
}

.attr-tools {
  display: flex;
}

.attr-row {
  display: grid;
  grid-template-columns: 100px 1fr;
  align-items: center;
  gap: 8px;
}

.warn {
  margin: 0;
  color: var(--danger);
}

.setup-actions {
  display: flex;
  gap: 8px;
}

.ghost {
  border: 1px solid var(--line);
  color: var(--text);
  background: rgba(255, 255, 255, 0.82);
  height: 42px;
  padding: 0 14px;
  border-radius: 14px;
  transition: transform 0.3s ease, background-color 0.3s ease;
}

.ghost:hover {
  transform: scale(1.02);
  background: rgba(233, 246, 239, 0.95);
}

.confirm-text {
  margin: 0;
  color: var(--subtext);
  line-height: 1.8;
}

.confirm-actions {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.session-shell {
  position: relative;
  display: grid;
  gap: 18px;
  grid-template-columns: 280px minmax(0, 1fr);
}

.stats-panel,
.story-panel {
  border: 1px solid var(--line);
  border-radius: 24px;
  background: var(--panel);
  backdrop-filter: blur(14px);
  box-shadow: var(--shadow-soft);
}

.stats-panel {
  padding: 16px;
  position: sticky;
  top: 84px;
  height: fit-content;
}

.stats-panel h3,
.story-panel h3 {
  margin: 0 0 12px;
  color: var(--title);
  font-family: var(--font-serif);
}

.stats-panel ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.stats-panel li {
  display: flex;
  justify-content: space-between;
  padding: 9px 11px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(15, 23, 42, 0.1);
  transition: transform 0.3s ease;
}

.stats-panel li strong {
  font-variant-numeric: tabular-nums;
  color: var(--title);
}

.stats-panel li.changed {
  transform: translateY(-1px);
}

.stats-panel li.is-up {
  animation: stat-up 0.6s ease;
}

.stats-panel li.is-down {
  animation: stat-down 0.6s ease;
}

@keyframes stat-up {
  0% {
    background: rgba(255, 255, 255, 0.8);
  }
  50% {
    background: rgba(232, 208, 162, 0.42);
  }
  100% {
    background: rgba(255, 255, 255, 0.8);
  }
}

@keyframes stat-down {
  0% {
    background: rgba(255, 255, 255, 0.8);
  }
  50% {
    background: rgba(255, 107, 129, 0.22);
  }
  100% {
    background: rgba(255, 255, 255, 0.8);
  }
}

.story-panel {
  padding: 18px;
  display: grid;
  grid-template-rows: auto 1fr auto;
  height: calc(100vh - 130px);
}

.feed {
  overflow: auto;
  display: grid;
  gap: 12px;
  align-content: start;
  padding: 4px 8px 4px 2px;
  min-height: 0;
}

.bubble {
  padding: 12px 14px;
  border-radius: 18px;
  max-width: min(760px, 96%);
  white-space: pre-wrap;
  line-height: 1.9;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.bubble.is-past {
  opacity: 0.85;
}

.bubble.is-latest {
  color: var(--title);
  font-size: 1.06rem;
}

.bubble.is-system {
  background: rgba(228, 239, 251, 0.7);
  border: 1px solid rgba(56, 116, 185, 0.2);
}

.bubble.is-assistant {
  background: rgba(220, 242, 232, 0.76);
  border: 1px solid rgba(42, 157, 143, 0.24);
}

.bubble.is-user {
  justify-self: end;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(15, 23, 42, 0.14);
}

.action-bar {
  border-top: 1px solid var(--line);
  margin-top: 12px;
  padding-top: 10px;
  display: grid;
  gap: 8px;
  background: rgba(255, 255, 255, 0.78);
  border-radius: 18px;
  padding: 10px 12px;
  position: sticky;
  bottom: 0;
  backdrop-filter: blur(10px);
}

.status-text {
  margin: 0 0 10px;
  color: var(--accent);
  font-size: 13px;
}

.segment-actions {
  display: flex;
}

.retry-wrap button {
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  color: var(--text);
  padding: 8px 14px;
  cursor: pointer;
  transition: transform 0.3s ease, background-color 0.3s ease;
}

.retry-wrap button:hover:enabled {
  transform: scale(1.02);
  background: rgba(227, 246, 238, 0.95);
}

.choices {
  display: grid;
  gap: 6px;
}

.choices button {
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.84);
  color: var(--text);
  padding: 8px 12px;
  text-align: left;
  white-space: normal;
  line-height: 1.7;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  gap: 4px;
  transition: border-color 0.3s ease, transform 0.3s ease, box-shadow 0.3s ease, background-color 0.3s ease;
  position: relative;
}

.choices button:hover:enabled {
  border-color: var(--line-strong);
  background: rgba(230, 246, 239, 0.96);
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 12px 22px rgba(0, 0, 0, 0.05);
}

.choices button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.mini-loading {
  position: absolute;
  right: 12px;
  top: 12px;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(42, 157, 143, 0.25);
  border-top-color: rgba(42, 157, 143, 0.95);
  border-radius: 999px;
  animation: spin 0.7s linear infinite;
}

.choice-main {
  color: var(--title);
  font-weight: 600;
  line-height: 1.6;
}

.choice-meta {
  font-size: 12px;
  color: var(--subtext);
  line-height: 1.5;
}

.situation-title {
  margin: 0;
  font-size: 12px;
  color: var(--subtext);
}

.situation-text {
  margin: 0;
  color: var(--title);
  font-weight: 600;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.custom-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 110px;
  gap: 8px;
}

.custom-form input {
  height: 42px;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 0 12px;
  background: rgba(255, 255, 255, 0.95);
  color: var(--text);
}

.end-summary {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.9);
  display: grid;
  gap: 8px;
}

.end-title {
  margin: 0;
  color: var(--title);
  font-weight: 700;
}

.end-text {
  margin: 0;
  line-height: 1.8;
  color: var(--text);
}

.end-actions {
  display: flex;
}

@media (max-width: 980px) {
  .session-shell {
    grid-template-columns: 1fr;
  }

  .stats-panel {
    position: static;
  }

  .story-panel {
    height: auto;
    min-height: calc(100vh - 110px);
    grid-template-rows: auto minmax(58vh, 1fr) auto;
  }

  .feed {
    max-height: 64vh;
  }

  .action-bar {
    position: static;
    bottom: auto;
    backdrop-filter: none;
    background: rgba(255, 255, 255, 0.92);
    margin-top: 8px;
  }

}

@media (max-width: 640px) {
  .story-panel {
    min-height: calc(100vh - 94px);
    grid-template-rows: auto minmax(62vh, 1fr) auto;
  }

  .feed {
    max-height: 68vh;
  }

  .choices button {
    padding: 7px 10px;
  }
}
</style>
