<script setup lang="ts">
import { RouterLink } from 'vue-router';
</script>

<template>
  <section class="panel">
    <h1>404</h1>
    <p>页面不存在，返回首页继续人生重开。</p>
    <RouterLink class="link" to="/">返回首页</RouterLink>
  </section>
</template>

<style scoped>
.panel {
  width: min(560px, 100%);
  margin: 70px auto 0;
  text-align: center;
  padding: 24px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
}

.link {
  color: var(--accent);
}
</style>

