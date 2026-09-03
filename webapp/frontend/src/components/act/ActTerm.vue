<script setup lang="ts">
  /**
   * A term, with its definition one hover away.
   *
   *   <ActTerm t="auc-macro" />                 -> "macro AUC" + tooltip
   *   <ActTerm t="auc-macro">macro</ActTerm>    -> "macro"     + the same tooltip
   *
   * The slot exists because the same definition has to attach to whatever the
   * sentence needed to call the thing. What must NOT vary is the definition, so
   * the wording comes from utils/glossary.ts and never from the call site.
   *
   * A key that is not in the glossary renders as plain text with no affordance,
   * rather than throwing or drawing an empty tooltip in front of an audience.
   */
  import { computed } from 'vue'
  import ActInfo from './ActInfo.vue'
  import { GLOSSARY } from '@/utils/glossary'

  defineOptions({ name: 'ActTerm' })

  const props = defineProps<{
    /** Glossary key. */
    t: string
    /** Underline the term itself. Off inside dense chart furniture. */
    plain?: boolean
  }>()

  const entry = computed(() => GLOSSARY[props.t] ?? null)
</script>

<template>
  <span class="whitespace-nowrap">
    <span :class="entry && !plain
            ? 'underline decoration-dotted decoration-muted-foreground/50 underline-offset-2'
            : ''"><slot>{{ entry?.term ?? t }}</slot></span><ActInfo v-if="entry" :text="entry.def" />
  </span>
</template>
