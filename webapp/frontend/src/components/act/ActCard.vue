<script setup lang="ts">
  /**
   * The demo deck's card, on Dataiku brand tokens.
   *
   * Mirrors the `card()` helper in DASHBOARD_MOCKUP_V3.html: title, optional
   * description, status chips, body, and a source footer.
   *
   * The `src` footer is a guardrail, not decoration — the design doc requires
   * every number to name the dataset it came from, because a figure with no
   * provenance undercuts the platform claim the demo closes on.
   */
  defineOptions({ name: 'ActCard' })

  withDefaults(
    defineProps<{
      title: string
      desc?: string
      /** [label, kind] — kind drives the tint: live | mock | port */
      chips?: [string, string][]
      /** Tailwind col-span on the 12-column act grid */
      span?: string
      /** Source dataset names, rendered as a provenance footer */
      src?: string[]
    }>(),
    { span: 'col-span-12' },
  )

  const DSS = 'https://design.solutions.dataiku-dss.io/projects/DEMO_TARGET_IDENTIFICATION/datasets'
</script>

<template>
  <section
    :class="span"
    class="flex flex-col overflow-hidden rounded-lg border border-border bg-card shadow-sm"
  >
    <header class="flex flex-wrap items-start justify-between gap-2 px-5 pt-4 pb-2">
      <div class="flex flex-col gap-0.5">
        <h2 class="font-serif text-[17px] font-semibold leading-snug tracking-tight">
          {{ title }}
        </h2>
        <p v-if="desc" class="max-w-2xl text-[13px] leading-relaxed text-muted-foreground">
          {{ desc }}
        </p>
      </div>
      <div v-if="chips?.length" class="flex flex-none gap-1.5">
        <span
          v-for="[label, kind] in chips"
          :key="label"
          class="rounded font-mono text-[10px] uppercase tracking-wide px-1.5 py-0.5"
          :class="{
            'bg-primary/25 text-primary-foreground': kind === 'live',
            'bg-muted text-muted-foreground': kind === 'mock',
            'bg-accent text-accent-foreground': kind === 'port',
          }"
        >{{ label }}</span>
      </div>
    </header>

    <div class="px-5 pb-4 pt-1"><slot /></div>

    <footer
      v-if="src?.length"
      class="mt-auto flex flex-wrap items-center gap-2 border-t border-border bg-secondary/40 px-5 py-2"
    >
      <span class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">src</span>
      <a
        v-for="s in src"
        :key="s"
        :href="`${DSS}/${s}/explore/`"
        target="_blank"
        rel="noopener"
        class="font-mono text-[11px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
      >{{ s }}</a>
    </footer>
  </section>
</template>
