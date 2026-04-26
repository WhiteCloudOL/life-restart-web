<script setup lang="ts">
defineProps<{
  title: string;
  subtitle: string;
}>();
</script>

<template>
  <section
    class="rounded-[2rem] border border-zinc-200/60 bg-white/90 p-8 shadow-[0_24px_80px_rgba(24,24,27,0.07)] ring-1 ring-zinc-900/5 backdrop-blur-2xl lg:p-10"
  >
    <header class="mb-8">
      <p class="text-xs font-semibold uppercase tracking-[0.28em] text-zinc-500">Access Portal</p>
      <h1 class="mt-4 text-3xl font-bold tracking-tight text-zinc-900">{{ title }}</h1>
      <p class="mt-3 text-sm leading-7 text-zinc-500">{{ subtitle }}</p>
    </header>
    <slot />
  </section>
</template>
