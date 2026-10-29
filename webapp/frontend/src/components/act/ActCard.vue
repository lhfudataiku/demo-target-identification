<script setup lang="ts">
  /**
   * The demo deck's card.
   *
   * Information contract from DASHBOARD_MOCKUP_V3.html's `card()` — title,
   * description, chips, body, source footer. Visual treatment from the
   * bs-blueprint idiom (KpiCard / ChartsView): a primary-tinted gradient
   * surface, rounded-xl, shadow-sm. The tints are token classes, not inline
   * styles, so the design lint can check them.
   *
   * The `src` footer is a guardrail, not decoration: the design doc requires
   * every number to name the dataset it came from.
   *
   * ── The footer bar, and why it exists ──────────────────────────────────────
   * Titles were drifting long because they were carrying the card's argument,
   * and subtitles were carrying methodology, chart furniture and caveats at the
   * same time. Four slots now divide that work, and the division is the point:
   *
   *   title      names the card. A short noun phrase; never an argument.
   *   desc       ONE sentence, carrying the finding with its live number.
   *   #note      the insight that did not fit — always visible, in the bar.
   *   #method    "How this is computed" — COLLAPSED. Methodology, caveats,
   *              formulas, and the internal references a data scientist needs
   *              to defend the build but a client should not have to read.
   *
   * The pattern is act 4's "Why this gene?" card generalised: its percentile
   * explanation was the only methodology block in the app that read well, and
   * the only thing wrong with it was that it was always open.
   *
   * #presenter is the fourth: a line for the person demoing, not for the room.
   * It is hidden by the presenter-notes switch (stores/presenter.ts), which is
   * the whole reason one app can serve both audiences.
   */
  import { computed, ref, useSlots, type Component } from 'vue'
  import { ChevronRight, Comment } from '@dataiku/vue-icons'
    import { usePresenterStore } from '@/stores/presenter'
  import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@dataiku/ea-ui-kit'

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
      icon?: Component
      /** Label on the collapsed methodology disclosure. */
      methodLabel?: string
    }>(),
    { span: 'col-span-12', methodLabel: 'How this is computed' },
  )

  const slots = useSlots()
  const presenter = usePresenterStore()
  const open = ref(false)

  const hasNote = computed(() => Boolean(slots.note))
  const hasMethod = computed(() => Boolean(slots.method))
  const showPresenter = computed(() => Boolean(slots.presenter) && presenter.showNotes)
  const hasFooter = computed(() =>
    hasNote.value || hasMethod.value || showPresenter.value || Boolean(props.src?.length))

  // Mirrors the template's KpiCard: a wash of the primary at the top edge that
  // resolves into the card surface, plus a border tinted the same way. Every
  // card used the default accent, so the per-card colour prop went with the
  // inline styles (2026-10-26).
  const edge = 'border-primary/15'

  const DSS = 'https://design.solutions.dataiku-dss.io/projects/DEMO_TARGET_IDENTIFICATION/datasets'
</script>

<template>
  <section :class="span"
           class="flex flex-col overflow-hidden rounded-xl border border-primary/20 bg-linear-to-b
                  from-primary/10 to-card to-25% shadow-sm">
    <header class="flex flex-wrap items-start justify-between gap-2 px-5 pt-4 pb-2">
      <div class="flex items-start gap-3">
        <span v-if="icon"
              class="mt-0.5 grid size-8 flex-none place-items-center rounded-lg bg-primary/20 text-primary">
          <component :is="icon" class="size-4" />
        </span>
        <div class="flex flex-col gap-0.5">
          <h2 class="text-lg font-semibold leading-snug tracking-tight">{{ title }}</h2>
          <p v-if="desc || $slots.desc"
             class="max-w-2xl text-sm leading-relaxed text-muted-foreground">
            <slot name="desc">{{ desc }}</slot>
          </p>
        </div>
      </div>
      <div v-if="chips?.length" class="flex flex-none gap-1.5">
        <span v-for="[label, kind] in chips" :key="label"
              class="rounded-md px-1.5 py-0.5 font-mono text-2xs uppercase tracking-wide"
              :class="{
                'bg-primary/25 text-primary': kind === 'live',
                'bg-muted text-muted-foreground': kind === 'mock',
                'bg-accent text-accent-foreground': kind === 'port',
              }">{{ label }}</span>
      </div>
    </header>

    <div class="px-5 pb-4 pt-1"><slot /></div>

    <footer v-if="hasFooter" class="mt-auto flex flex-col">
      <!-- The insight that did not fit in one sentence. Always visible. -->
      <div v-if="hasNote" class="border-t px-5 py-2.5 text-xs leading-relaxed" :class="edge">
        <slot name="note" />
      </div>

      <!-- Methodology, collapsed. The disclosure is the whole point: a client
           never has to read it, and a data scientist is one click from it. -->
      <Collapsible v-if="hasMethod" v-model:open="open" class="border-t" :class="edge">
        <CollapsibleTrigger
          class="flex w-full items-center gap-1.5 px-5 py-2 text-left font-mono text-2xs
                 uppercase tracking-wide text-muted-foreground transition-colors
                 hover:text-foreground focus-visible:outline-none focus-visible:ring-2
                 focus-visible:ring-ring/40">
          <ChevronRight class="size-3 transition-transform" :class="open ? 'rotate-90' : ''" />
          {{ methodLabel }}
        </CollapsibleTrigger>
        <CollapsibleContent class="px-5 pb-3 text-2xs leading-relaxed text-muted-foreground">
          <slot name="method" />
        </CollapsibleContent>
      </Collapsible>

      <!-- For the person demoing, not for the room. -->
      <div v-if="showPresenter"
           class="flex items-start gap-2 border-t bg-secondary/60 px-5 py-2.5 text-xs
                  leading-relaxed"
           :class="edge">
        <Comment class="mt-0.5 size-3.5 flex-none text-muted-foreground" />
        <div><slot name="presenter" /></div>
      </div>

      <div v-if="src?.length"
           class="flex flex-wrap items-center gap-2 border-t px-5 py-2" :class="edge">
        <span class="font-mono text-2xs uppercase tracking-wide text-muted-foreground">src</span>
        <a v-for="s in src" :key="s" :href="`${DSS}/${s}/explore/`" target="_blank" rel="noopener"
           class="font-mono text-2xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline">{{ s }}</a>
      </div>
    </footer>
  </section>
</template>
