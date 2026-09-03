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
  import { useGlossaryStore } from '@/stores/glossary'

  defineOptions({ name: 'ActTerm' })

  const props = defineProps<{
    /** Glossary key. */
    t: string
    /** Underline the term itself. Off inside dense chart furniture. */
    plain?: boolean
  }>()

  const entry = computed(() => GLOSSARY[props.t] ?? null)

  // The tooltip answers the word where it stands; clicking opens the drawer at
  // this entry, for the reader who wants the neighbouring terms too. A term
  // with no glossary entry is inert text and gets no affordance.
  const glossary = useGlossaryStore()
</script>

<template>
  <span class="whitespace-nowrap">
    <component
      :is="entry ? 'button' : 'span'"
      v-bind="entry ? { type: 'button', title: 'Open the glossary here' } : {}"
      :class="entry
        ? ['cursor-pointer bg-transparent p-0 text-left font-[inherit] text-[length:inherit] text-inherit',
           'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40',
           plain ? '' : 'underline decoration-dotted decoration-muted-foreground/50 underline-offset-2']
        : ''"
      @click="entry && glossary.open(t)"
    ><slot>{{ entry?.term ?? t }}</slot></component><ActInfo v-if="entry" :text="entry.def" />
  </span>
</template>
