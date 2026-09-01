<script setup lang="ts">
  /**
   * The demo deck's card.
   *
   * Information contract from DASHBOARD_MOCKUP_V3.html's `card()` — title,
   * description, chips, body, source footer. Visual treatment from the
   * bs-blueprint idiom (KpiCard / ChartsView): an accent-tinted gradient
   * surface, a per-card accent colour, rounded-xl, shadow-sm.
   *
   * The `src` footer is a guardrail, not decoration: the design doc requires
   * every number to name the dataset it came from.
   */
  import { computed } from 'vue'
  import type { LucideIcon } from 'lucide-vue-next'

  defineOptions({ name: 'ActCard' })

  const props = withDefaults(
    defineProps<{
      title: string
      desc?: string
      /** [label, kind] — live | mock | port */
      chips?: [string, string][]
      /** Tailwind col-span on the 12-column act grid */
      span?: string
      /** Source dataset names, rendered as a provenance footer */
      src?: string[]
      icon?: LucideIcon
      /** Any CSS colour; defaults to the brand accent. */
      accent?: string
    }>(),
    { span: 'col-span-12', accent: 'var(--primary)' },
  )

  // Mirrors the template's KpiCard: a wash of the accent at the top edge that
  // resolves into the card surface, plus a border tinted the same way.
  const cardStyle = computed(() => ({
    borderColor: `color-mix(in oklab, ${props.accent} 22%, var(--border))`,
    background:
      `linear-gradient(180deg, color-mix(in oklab, ${props.accent} 9%, var(--card)) 0%, var(--card) 26%)`,
  }))
  const iconStyle = computed(() => ({
    backgroundColor: `color-mix(in oklab, ${props.accent} 20%, var(--card))`,
    color: `color-mix(in oklab, ${props.accent} 70%, var(--foreground))`,
  }))

  const DSS = 'https://design.solutions.dataiku-dss.io/projects/DEMO_TARGET_IDENTIFICATION/datasets'
</script>

<template>
  <section :class="span" :style="cardStyle"
           class="flex flex-col overflow-hidden rounded-xl border shadow-sm">
    <header class="flex flex-wrap items-start justify-between gap-2 px-5 pt-4 pb-2">
      <div class="flex items-start gap-3">
        <span v-if="icon" :style="iconStyle"
              class="mt-0.5 grid size-8 flex-none place-items-center rounded-lg">
          <component :is="icon" class="size-4" />
        </span>
        <div class="flex flex-col gap-0.5">
          <h2 class="font-serif text-[17px] font-semibold leading-snug tracking-tight">{{ title }}</h2>
          <p v-if="desc" class="max-w-2xl text-[13px] leading-relaxed text-muted-foreground">{{ desc }}</p>
        </div>
      </div>
      <div v-if="chips?.length" class="flex flex-none gap-1.5">
        <span v-for="[label, kind] in chips" :key="label"
              class="rounded-md px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide"
              :class="{
                'bg-primary/25 text-primary-foreground': kind === 'live',
                'bg-muted text-muted-foreground': kind === 'mock',
                'bg-accent text-accent-foreground': kind === 'port',
              }">{{ label }}</span>
      </div>
    </header>

    <div class="px-5 pb-4 pt-1"><slot /></div>

    <footer v-if="src?.length"
            class="mt-auto flex flex-wrap items-center gap-2 border-t px-5 py-2"
            :style="{ borderColor: `color-mix(in oklab, ${accent} 14%, var(--border))` }">
      <span class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">src</span>
      <a v-for="s in src" :key="s" :href="`${DSS}/${s}/explore/`" target="_blank" rel="noopener"
         class="font-mono text-[11px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline">{{ s }}</a>
    </footer>
  </section>
</template>
