<script setup lang="ts">
  /**
   * Every term the deck uses, in one panel.
   *
   * The tooltip on an <ActTerm> answers "what is this word" where it stands.
   * This answers "what was that word three cards ago", which is the question a
   * client actually asks — and it answers it without taking them off the card
   * they were reading.
   *
   * The content is utils/glossary.ts, unmodified. This component renders; it
   * never restates a definition, because a second copy of the wording is how
   * the two would start to disagree.
   */
  import { computed, nextTick, ref, watch } from 'vue'
  import { BookOpen, Search, X } from 'lucide-vue-next'
  import { GLOSSARY, GLOSSARY_GROUPS, GROUP_LABEL } from '@/utils/glossary'
  import { useGlossaryStore } from '@/stores/glossary'

  defineOptions({ name: 'ActGlossaryDrawer' })

  const store = useGlossaryStore()
  const q = ref('')
  const panel = ref<HTMLElement | null>(null)

  const match = (key: string) => {
    const needle = q.value.trim().toLowerCase()
    if (!needle) return true
    const e = GLOSSARY[key]
    return key.includes(needle)
      || e.term.toLowerCase().includes(needle)
      || e.def.toLowerCase().includes(needle)
  }

  const sections = computed(() =>
    GLOSSARY_GROUPS
      .map(({ group, keys }) => ({ group, keys: keys.filter(match) }))
      .filter((s) => s.keys.length))

  const total = computed(() => Object.keys(GLOSSARY).length)
  const shown = computed(() => sections.value.reduce((a, s) => a + s.keys.length, 0))

  // Opening from a term scrolls to it. Deliberately instant rather than smooth:
  // the same smooth-scroll unreliability act 4's revealWhyCard() documents
  // applies here, and landing on the entry is the requirement.
  watch(() => store.isOpen, async (open) => {
    if (!open) { q.value = ''; return }
    await nextTick()
    const key = store.focusKey
    if (!key) { panel.value?.focus(); return }
    const el = document.getElementById(`glossary-${key}`)
    if (el) el.scrollIntoView({ block: 'center' })
    else panel.value?.focus()
  })
</script>

<template>
  <Teleport to="body">
    <div v-if="store.isOpen" class="fixed inset-0 z-[100] flex justify-end"
         role="dialog" aria-modal="true" aria-label="Glossary">
      <!-- Scrim. Click-through-to-close, and it dims the deck rather than
           hiding it: the card you were reading stays visible behind. -->
      <div class="absolute inset-0 bg-foreground/25" @click="store.close()" />

      <section ref="panel" tabindex="-1"
               class="relative flex h-full w-[min(30rem,100vw)] flex-col border-l border-border
                      bg-card shadow-xl outline-none"
               @keydown.esc="store.close()">
        <header class="flex flex-none items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div class="flex items-start gap-3">
            <span class="mt-0.5 grid size-8 flex-none place-items-center rounded-lg bg-primary/20 text-primary-foreground">
              <BookOpen class="size-4" />
            </span>
            <div class="flex flex-col gap-0.5">
              <h2 class="font-serif text-[17px] font-semibold leading-snug tracking-tight">Glossary</h2>
              <p class="text-[12.5px] leading-relaxed text-muted-foreground">
                Every data-science and biology term this deck uses.
              </p>
            </div>
          </div>
          <button type="button" aria-label="Close glossary"
                  class="rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent/50
                         hover:text-foreground focus-visible:outline-none focus-visible:ring-2
                         focus-visible:ring-ring/40"
                  @click="store.close()">
            <X class="size-4" />
          </button>
        </header>

        <div class="flex-none border-b border-border px-5 py-3">
          <div class="flex items-center gap-2 rounded-md border border-input bg-background px-2.5 py-1.5">
            <Search class="size-3.5 flex-none text-muted-foreground" />
            <input v-model="q" type="search" placeholder="Search a term or its definition…"
                   aria-label="Search the glossary"
                   class="w-full bg-transparent text-[13px] outline-none placeholder:text-muted-foreground" />
          </div>
          <p class="mt-1.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
            {{ shown === total ? `${total} terms` : `${shown} of ${total} terms` }}
          </p>
        </div>

        <div class="flex-1 overflow-y-auto px-5 py-4">
          <div v-for="s in sections" :key="s.group" class="mb-6 last:mb-0">
            <h3 class="mb-2 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              {{ GROUP_LABEL[s.group] }}
            </h3>
            <dl class="flex flex-col">
              <div v-for="key in s.keys" :id="`glossary-${key}`" :key="key"
                   class="border-b border-border py-2.5 last:border-b-0 scroll-mt-4"
                   :class="store.focusKey === key ? 'bg-accent/40' : ''">
                <dt class="text-[13px] font-medium leading-snug">{{ GLOSSARY[key].term }}</dt>
                <dd class="mt-0.5 text-[12.5px] leading-relaxed text-muted-foreground">
                  {{ GLOSSARY[key].def }}
                </dd>
              </div>
            </dl>
          </div>

          <p v-if="!sections.length" class="py-8 text-center text-[13px] text-muted-foreground">
            No term matches “{{ q }}”.
          </p>
        </div>
      </section>
    </div>
  </Teleport>
</template>
