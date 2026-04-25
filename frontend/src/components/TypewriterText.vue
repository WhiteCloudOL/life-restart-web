<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue';

const props = withDefaults(
  defineProps<{
    text: string;
    speed?: number;
    immediate?: boolean;
  }>(),
  {
    speed: 22,
    immediate: false,
  },
);

const emit = defineEmits<{
  (event: 'done'): void;
}>();

const rendered = ref<string>('');
let timer: number | null = null;

const stopTimer = (): void => {
  if (timer !== null) {
    window.clearInterval(timer);
    timer = null;
  }
};

const start = (): void => {
  stopTimer();
  if (props.immediate || !props.text) {
    rendered.value = props.text;
    emit('done');
    return;
  }

  let index = 0;
  rendered.value = '';
  timer = window.setInterval(() => {
    index += 1;
    rendered.value = props.text.slice(0, index);
    if (index >= props.text.length) {
      stopTimer();
      emit('done');
    }
  }, props.speed);
};

watch(
  () => props.text,
  () => {
    start();
  },
);

onMounted(start);
onUnmounted(stopTimer);
</script>

<template>
  <span>{{ rendered }}</span>
</template>

