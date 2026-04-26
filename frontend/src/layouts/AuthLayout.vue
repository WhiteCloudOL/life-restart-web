<template>
  <div class="relative min-h-screen overflow-hidden bg-zinc-50 px-4 py-10">
    <div
      class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(255,255,255,0.95),transparent_24%),radial-gradient(circle_at_82%_14%,rgba(244,244,245,0.9),transparent_24%),linear-gradient(180deg,#fcfcfb_0%,#fafafa_52%,#f6f6f5_100%)]"
    />
    <div
      class="pointer-events-none absolute left-1/2 top-24 h-[26rem] w-[26rem] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(24,24,27,0.06),transparent_68%)] blur-3xl"
    />
    <main class="relative z-10 mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-md items-center">
      <RouterView />
    </main>
  </div>
</template>
