<script setup lang="ts">
import type { GamePreset, PresetAttributeOption } from '@/types/game';

defineProps<{
  canStart: boolean;
  currentPrompt: string;
  currentWorldview: string;
  currentCharacterSetting: string;
  currentSelectedOption: string | null;
  isActionPending: boolean;
  isCustomPreset: boolean;
  preset: GamePreset | null;
  setupAttributeLimit: number;
  setupAttributeTotal: number;
  setupRows: PresetAttributeOption[];
  setupValues: Record<string, number>;
  startEtaText: string;
}>();

const emit = defineEmits<{
  'begin-world': [];
  'back-home': [];
  'randomize-attributes': [];
  'update:prompt': [value: string];
  'update:worldview': [value: string];
  'update:character-setting': [value: string];
  'update:selected-option': [value: string];
  'adjust-attribute': [payload: { key: string; delta: number; minValue: number; maxValue: number }];
}>();
</script>

<template>
  <section class="px-4 pb-16 pt-6 lg:pt-10">
    <div
      class="mx-auto mt-10 max-w-3xl rounded-3xl border border-zinc-100 bg-white/90 p-8 shadow-2xl shadow-zinc-200/50 backdrop-blur-2xl lg:p-12"
    >
      <header class="mb-10 space-y-3">
        <p class="text-xs font-semibold uppercase tracking-[0.28em] text-zinc-500">World Configuration</p>
        <h1 class="text-3xl font-bold tracking-tight text-zinc-900">开局配置</h1>
        <p v-if="preset" class="text-sm leading-7 text-zinc-500">
          {{ preset.title }} · {{ preset.worldview }}
        </p>
        <p v-else class="text-sm leading-7 text-zinc-500">未选择预设，正在返回大厅...</p>
      </header>

      <div v-if="preset" class="space-y-8">
        <div class="grid gap-6">
          <label class="grid gap-2 text-sm font-medium text-zinc-600">
            <span>人物设定</span>
            <select
              v-if="!isCustomPreset"
              :value="currentSelectedOption ?? ''"
              class="w-full rounded-xl border border-zinc-200 bg-zinc-50/50 px-4 py-3 text-sm text-zinc-700 placeholder-zinc-400 transition-all focus:border-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-800/20"
              @change="emit('update:selected-option', ($event.target as HTMLSelectElement).value)"
            >
              <option v-for="option in preset.character_options" :key="option" :value="option">
                {{ option }}
              </option>
            </select>
            <input
              v-else
              :value="currentCharacterSetting"
              maxlength="500"
              class="w-full rounded-xl border border-zinc-200 bg-zinc-50/50 px-4 py-3 text-sm text-zinc-700 placeholder-zinc-400 transition-all focus:border-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-800/20"
              placeholder="输入你的角色设定（如：没背景但极度理性）"
              @input="emit('update:character-setting', ($event.target as HTMLInputElement).value)"
            />
          </label>

          <label v-if="isCustomPreset" class="grid gap-2 text-sm font-medium text-zinc-600">
            <span>自定义世界设定</span>
            <textarea
              :value="currentWorldview"
              maxlength="2000"
              rows="5"
              class="w-full rounded-xl border border-zinc-200 bg-zinc-50/50 px-4 py-3 text-sm text-zinc-700 placeholder-zinc-400 transition-all focus:border-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-800/20"
              placeholder="输入世界观、时代背景、规则与氛围"
              @input="emit('update:worldview', ($event.target as HTMLTextAreaElement).value)"
            />
          </label>

          <label class="grid gap-2 text-sm font-medium text-zinc-600">
            <span>自定义提示词（可选）</span>
            <input
              :value="currentPrompt"
              maxlength="200"
              class="w-full rounded-xl border border-zinc-200 bg-zinc-50/50 px-4 py-3 text-sm text-zinc-700 placeholder-zinc-400 transition-all focus:border-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-800/20"
              placeholder="例如：希望剧情更偏成长线与现实主义"
              @input="emit('update:prompt', ($event.target as HTMLInputElement).value)"
            />
          </label>
        </div>

        <section class="space-y-5 rounded-[1.75rem] border border-zinc-200/60 bg-zinc-50/70 p-6 ring-1 ring-zinc-900/5">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p class="text-sm font-semibold text-zinc-800">
                可分配属性：{{ setupAttributeTotal }} / {{ setupAttributeLimit }}
              </p>
              <p class="mt-1 text-xs text-zinc-500">每一点都将影响你被世界回应的方式。</p>
            </div>
            <button
              type="button"
              class="inline-flex items-center justify-center rounded-xl border border-zinc-200/60 bg-white px-4 py-2 text-sm font-medium text-zinc-600 transition-all hover:border-zinc-300 hover:bg-zinc-100"
              :disabled="isActionPending"
              @click="emit('randomize-attributes')"
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
                  @click="emit('adjust-attribute', { key: item.key, delta: -1, minValue: item.min_value, maxValue: item.max_value })"
                >
                  -
                </button>
                <span class="min-w-[2.5rem] text-center text-base font-bold text-zinc-800">
                  {{ setupValues[item.key] }}
                </span>
                <button
                  type="button"
                  class="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-100 text-zinc-600 transition-colors hover:bg-zinc-200"
                  @click="emit('adjust-attribute', { key: item.key, delta: 1, minValue: item.min_value, maxValue: item.max_value })"
                >
                  +
                </button>
              </div>
            </div>
          </div>
        </section>

        <p v-if="!canStart" class="text-sm text-red-500">
          当前配置未满足要求，请检查属性总点与自定义输入内容。
        </p>

        <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
            <button
              type="button"
              class="rounded-xl bg-zinc-800 px-6 py-3 text-sm font-medium text-white transition-all duration-300 hover:bg-zinc-900 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="!canStart || isActionPending"
              @click="emit('begin-world')"
            >
              {{ isActionPending ? '正在进入...' : '开始人生' }}
            </button>
            <span class="text-xs text-zinc-500">{{ startEtaText }}</span>
          </div>
          <button
            type="button"
            class="text-sm font-medium text-zinc-500 transition-colors hover:text-zinc-900"
            @click="emit('back-home')"
          >
            返回大厅
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
