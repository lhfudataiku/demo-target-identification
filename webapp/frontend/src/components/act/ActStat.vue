<script setup lang="ts">
  /** The mockup's `stat()` block: label, big mono number, sub-caption. */
  defineOptions({ name: 'ActStat' })
  defineProps<{ label: string; value: string | number; sub?: string }>()
</script>

<template>
  <div class="flex flex-col gap-0.5">
    <span class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">{{ label }}</span>
    <span class="font-mono text-2xl font-medium tabular-nums leading-tight">{{ value }}</span>
    <span v-if="sub" class="text-[11px] leading-snug text-muted-foreground">{{ sub }}</span>
  </div>
</template>
