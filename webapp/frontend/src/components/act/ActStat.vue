<script setup lang="ts">
  /** The mockup's `stat()` block: label, big mono number, sub-caption.
   *
   *  A stat label is four words of monospace over a big number — the densest
   *  place in the app and the one most likely to be a term of art ("Macro AUC",
   *  "Positive rate", "Base rate"). `t` attaches the glossary entry; `info`
   *  carries a one-off explanation that is not a glossary term.
   */
  import ActTerm from './ActTerm.vue'
  import ActInfo from './ActInfo.vue'

  defineOptions({ name: 'ActStat' })
  defineProps<{
    label: string
    value: string | number
    sub?: string
    /** Glossary key, when the label names a defined term. */
    t?: string
    /** A one-off note, when it does not. */
    info?: string
  }>()
</script>

<template>
  <div class="flex flex-col gap-0.5">
    <span class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
      <ActTerm v-if="t" :t="t" plain>{{ label }}</ActTerm>
      <template v-else>{{ label }}<ActInfo v-if="info" :text="info" /></template>
    </span>
    <span class="font-mono text-2xl font-medium tabular-nums leading-tight">{{ value }}</span>
    <span v-if="sub" class="text-[11px] leading-snug text-muted-foreground">{{ sub }}</span>
  </div>
</template>
