<template>
  <div class="relative min-h-screen overflow-hidden bg-zinc-50 px-4 py-6 md:px-8 md:py-8">
    <div
      class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(255,255,255,0.95),transparent_24%),radial-gradient(circle_at_82%_14%,rgba(244,244,245,0.9),transparent_24%),linear-gradient(180deg,#fcfcfb_0%,#fafafa_52%,#f6f6f5_100%)]"
    />
    <div
      class="pointer-events-none absolute left-[22%] top-1/2 h-[28rem] w-[28rem] -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(24,24,27,0.06),transparent_68%)] blur-3xl"
    />
    <div class="relative z-10 mx-auto flex min-h-[calc(100vh-3rem)] w-full max-w-6xl items-center">
      <div class="grid w-full items-center gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(26rem,32rem)] lg:gap-16">
        <section class="hidden lg:block">
          <div class="max-w-2xl space-y-6">
            <p class="text-xs font-semibold uppercase tracking-[0.32em] text-zinc-500">AI Life Restart Simulator</p>
            <h1 class="text-5xl font-bold tracking-tight text-zinc-900 leading-[1.08]">
              以更宽的视野，
              <br />
              重新进入一段人生。
            </h1>
            <p class="max-w-xl text-[15px] leading-8 text-zinc-500">
              在这里，你不是匆忙点击下一步的玩家，而是站在命运上方的观测者。设定角色、进入世界，再看每一次选择如何缓慢改变故事纹理。
            </p>
            <div class="grid max-w-lg grid-cols-3 gap-4 pt-4">
              <div class="rounded-2xl border border-zinc-200/60 bg-white/70 p-4 ring-1 ring-zinc-900/5">
                <p class="text-[11px] uppercase tracking-[0.22em] text-zinc-400">Observe</p>
                <p class="mt-2 text-sm leading-6 text-zinc-600">记录属性起伏与剧情分叉。</p>
              </div>
              <div class="rounded-2xl border border-zinc-200/60 bg-white/70 p-4 ring-1 ring-zinc-900/5">
                <p class="text-[11px] uppercase tracking-[0.22em] text-zinc-400">Choose</p>
                <p class="mt-2 text-sm leading-6 text-zinc-600">在风险与收益之间做判断。</p>
              </div>
              <div class="rounded-2xl border border-zinc-200/60 bg-white/70 p-4 ring-1 ring-zinc-900/5">
                <p class="text-[11px] uppercase tracking-[0.22em] text-zinc-400">Rewrite</p>
                <p class="mt-2 text-sm leading-6 text-zinc-600">让世界回应你的意志与偏好。</p>
              </div>
            </div>
          </div>
        </section>

        <main class="mx-auto w-full max-w-xl lg:mx-0 lg:max-w-none">
          <RouterView />
        </main>
      </div>
    </div>
  </div>
</template>
