<script setup lang="ts">
defineProps<{
  title: string;
  subtitle: string;
}>();
</script>

<template>
  <section class="card">
    <header class="head">
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>
    </header>
    <slot />
  </section>
</template>

<style scoped>
.card {
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 24px;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(14px);
  box-shadow: var(--shadow-soft);
}

.head {
  margin-bottom: 18px;
}

h1 {
  margin: 0 0 8px;
  font-size: 28px;
  letter-spacing: 0.2px;
  color: var(--title);
  font-family: var(--font-serif);
}

p {
  margin: 0;
  color: var(--subtext);
  font-size: 14px;
}
</style>
