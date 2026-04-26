<script setup lang="ts">
import TypewriterText from '@/components/TypewriterText.vue';
import type { StoryEvent } from '@/types/game';

defineProps<{
  events: StoryEvent[];
  getEventAccent: (content: string, role: StoryEvent['role']) => string;
  isActionPending: boolean;
  latestAssistantId: number | null;
  latestEventId: number | null;
  typedAssistantIds: Set<number>;
}>();

const emit = defineEmits<{
  'assistant-done': [eventId: number];
  'bind-feed': [element: HTMLElement | null];
}>();
</script>

<template>
  <section class="flex-1">
    <div :ref="(element) => emit('bind-feed', element as HTMLElement | null)" class="max-h-[calc(100vh-17rem)] overflow-y-auto pr-2">
      <TransitionGroup name="list" tag="div" class="max-w-2xl mx-auto flex-grow pb-32">
        <article
          v-for="event in events"
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
              @done="emit('assistant-done', event.id)"
            />
            <span v-else>{{ event.content }}</span>
          </div>
          <p v-if="latestEventId === event.id && isActionPending" class="mt-3 text-xs text-zinc-400">
            正在推进命运分支...
          </p>
        </article>
      </TransitionGroup>
    </div>
  </section>
</template>
