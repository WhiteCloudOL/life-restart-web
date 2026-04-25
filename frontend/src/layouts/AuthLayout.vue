<template>
  <div class="auth-shell">
    <div class="aurora" />
    <main class="auth-content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.auth-shell {
  min-height: 100vh;
  position: relative;
  display: grid;
  place-items: center;
  padding: 24px;
}

.aurora {
  position: absolute;
  width: min(700px, 95vw);
  aspect-ratio: 1.2;
  background:
    radial-gradient(circle at 30% 30%, rgba(132, 169, 140, 0.22), transparent 60%),
    radial-gradient(circle at 70% 70%, rgba(232, 208, 162, 0.2), transparent 65%);
  filter: blur(28px);
  pointer-events: none;
}

.auth-content {
  width: min(440px, 100%);
  position: relative;
  z-index: 1;
}
</style>
