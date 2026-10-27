<script setup lang="ts">
  /**
   * The evidence assistant for the selected pair (scope D1, workplan Phase 7a). Questions go to
   * `POST /api/assistant`, which answers as a stream: the text as it is written and each search as it
   * runs, then one checked answer that replaces the text. In the checked answer every sentence shows
   * the sources it cites; a sentence with none, or tagged by the model as general knowledge, is marked
   * "not from a retrieved source"; every graph result shows its Cypher.
   *
   * Nothing is stored: the conversation lives here and is sent with each question. It resets when the
   * selected pair changes.
   */
  import { computed, ref, watch } from 'vue'
  import {
    Button, Collapsible, CollapsibleContent, CollapsibleTrigger, Sheet, SheetContent, SheetDescription,
    SheetHeader, SheetTitle, Spinner, Textarea,
  } from '@dataiku/ea-ui-kit'
  import { ArrowExternalLink, ChevronDown, ChevronRight } from '@dataiku/vue-icons'
  import { StatusBadge } from 'bs-blueprint'
  import { postStream } from '@/utils/postStream'
  import { TOOL_LABEL, type CheckedAnswer, type Citation, type ToolActivity } from './types'

  const props = defineProps<{ diseaseIndex: number; geneIndex: number; gene: string; diseaseName: string }>()
  const open = defineModel<boolean>('open', { default: false })

  interface Turn { question: string; raw: string; tools: ToolActivity[]; answer: CheckedAnswer | null; error: string | null }
  const turns = ref<Turn[]>([])
  const draft = ref('')
  const busy = ref(false)
  const openGraph = ref<Record<string, boolean>>({})
  let controller: AbortController | null = null

  watch(() => [props.diseaseIndex, props.geneIndex], () => {
    controller?.abort(); turns.value = []; draft.value = ''; busy.value = false
  })

  const starters = computed(() => [
    `What is known about ${props.gene} in ${props.diseaseName}?`,
    `Which drugs act on ${props.gene}, and for which diseases?`,
    `How is ${props.gene} connected in the graph to the genes already linked to ${props.diseaseName}?`,
    `Which trials select patients by ${props.gene}?`,
  ])

  async function ask(question: string) {
    const q = question.trim()
    if (!q || busy.value) return
    const history = turns.value.filter((t) => t.answer).flatMap((t) => [
      { role: 'user', content: t.question }, { role: 'assistant', content: t.raw },
    ])
    const turn: Turn = { question: q, raw: '', tools: [], answer: null, error: null }
    turns.value.push(turn)
    const live = turns.value[turns.value.length - 1]
    draft.value = ''; busy.value = true
    controller = new AbortController()
    try {
      await postStream('/api/assistant', { disease: props.diseaseIndex, gene: props.geneIndex, question: q, history },
        (e) => {
          if (e.type === 'text_delta') live.raw += String(e.content ?? '')
          else if (e.type === 'tool_call_started') live.tools.push({
            id: String(e.id), name: String(e.name), query: String((e.args as { query?: string })?.query ?? ''),
            done: false, ok: true, summary: '' })
          else if (e.type === 'tool_call_completed') {
            const t = live.tools.find((x) => x.id === String(e.id))
            if (t) { t.done = true; t.ok = Boolean(e.ok); t.summary = String(e.summary ?? '') }
          } else if (e.type === 'answer') live.answer = e as unknown as CheckedAnswer
          else if (e.type === 'error') live.error = String(e.message)
        }, controller.signal)
    } catch (err) {
      if (!controller.signal.aborted) live.error = err instanceof Error ? err.message : String(err)
    } finally {
      busy.value = false
    }
  }

  function citationUrl(c: Citation): string | undefined {
    if (c.url) return c.url
    if (c.kind === 'trial' && c.id) return `https://clinicaltrials.gov/study/${c.id}`
    if (c.kind === 'paper' && c.id) return `https://pubmed.ncbi.nlm.nih.gov/${c.id}/`
    return undefined
  }
</script>

<template>
  <Sheet v-model:open="open">
    <SheetContent side="right" class="flex w-full flex-col gap-4 overflow-y-auto sm:max-w-2xl">
      <SheetHeader>
        <SheetTitle>Ask about {{ gene }} in {{ diseaseName }}</SheetTitle>
        <SheetDescription>
          Answers cite the model's numbers, the drug records, the trials and papers, and the graph queries they
          rely on. A sentence marked <i>not from a retrieved source</i> comes from the model's general knowledge.
          Nothing is stored.
        </SheetDescription>
      </SheetHeader>

      <div v-if="!turns.length" class="flex flex-col gap-2">
        <p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Start with</p>
        <Button v-for="s in starters" :key="s" variant="outline" size="sm" class="h-auto justify-start whitespace-normal py-2 text-left"
                :disabled="busy" @click="ask(s)">{{ s }}</Button>
      </div>

      <div v-for="(t, i) in turns" :key="i" class="flex flex-col gap-3">
        <p class="self-end rounded-lg bg-muted px-3 py-2 text-sm">{{ t.question }}</p>

        <ul v-if="t.tools.length" class="flex flex-col gap-1">
          <li v-for="a in t.tools" :key="a.id" class="flex items-center gap-2 text-xs text-muted-foreground">
            <Spinner v-if="!a.done" class="size-3" />
            <StatusBadge v-else :status="a.ok ? 'muted' : 'destructive'">{{ a.ok ? 'done' : 'failed' }}</StatusBadge>
            <span><b class="text-foreground">{{ TOOL_LABEL[a.name] ?? a.name }}</b> · {{ a.query }}<template v-if="a.summary"> — {{ a.summary }}</template></span>
          </li>
        </ul>

        <p v-if="t.error" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{{ t.error }}</p>

        <!-- The checked answer replaces the streamed text -->
        <div v-if="t.answer" class="flex flex-col gap-2 text-sm leading-relaxed">
          <p v-for="(s, j) in t.answer.sentences" :key="j" :class="s.general_knowledge ? 'text-muted-foreground' : ''">
            {{ s.text }}
            <template v-for="c in s.citations" :key="c.ref">
              <a v-if="citationUrl(c)" :href="citationUrl(c)" target="_blank" rel="noopener" :title="c.label ?? c.ref"
                 class="mx-0.5 inline-flex items-center gap-0.5 rounded bg-primary/10 px-1 font-mono text-2xs text-primary hover:underline">
                {{ c.ref }}<ArrowExternalLink class="size-2.5" /></a>
              <span v-else :title="c.label ?? c.ref" class="mx-0.5 rounded bg-primary/10 px-1 font-mono text-2xs text-primary">{{ c.ref }}</span>
            </template>
            <StatusBadge v-if="s.general_knowledge" status="muted" class="ml-1">not from a retrieved source</StatusBadge>
            <StatusBadge v-if="s.unresolved.length" status="warning" class="ml-1">citation removed: {{ s.unresolved.join(', ') }}</StatusBadge>
            <StatusBadge v-if="s.prescriptive" status="warning" class="ml-1">prescriptive</StatusBadge>
          </p>

          <Collapsible v-for="g in t.answer.graph" :key="g.id" v-model:open="openGraph[`${i}-${g.id}`]">
            <CollapsibleTrigger as-child>
              <Button variant="ghost" size="sm" class="-ml-2 h-auto justify-start whitespace-normal text-left">
                <component :is="openGraph[`${i}-${g.id}`] ? ChevronDown : ChevronRight" class="size-4 shrink-0" />
                <span class="font-mono text-2xs">{{ g.id }}</span> {{ g.title ?? g.query }} · {{ g.rows }} rows
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent class="flex flex-col gap-2 pl-6">
              <pre class="overflow-x-auto rounded-md bg-muted p-2 font-mono text-2xs">{{ g.cypher }}</pre>
              <p v-for="(names, type) in g.names" :key="type" class="text-xs">
                <span class="text-muted-foreground">{{ type }} ({{ g.distinct[type] }}):</span> {{ names.join(', ') }}<template
                  v-if="g.distinct[type] > names.length"> …</template>
              </p>
            </CollapsibleContent>
          </Collapsible>

          <p class="font-mono text-2xs text-muted-foreground">
            {{ t.answer.counts.cited }} of {{ t.answer.counts.sentences }} sentences cited · {{ t.answer.seconds }} s<template
              v-if="t.answer.tool_errors.length"> · {{ t.answer.tool_errors.length }} search failed</template>
          </p>
        </div>
        <p v-else-if="t.raw" class="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">{{ t.raw }}</p>
        <Spinner v-else-if="busy && i === turns.length - 1 && !t.error" class="size-4" />
      </div>

      <form class="mt-auto flex flex-col gap-2" @submit.prevent="ask(draft)">
        <Textarea v-model="draft" rows="2" :disabled="busy" :placeholder="`Ask about ${gene} in ${diseaseName}`"
                  @keydown.enter.exact.prevent="ask(draft)" />
        <Button type="submit" size="sm" class="self-end" :disabled="busy || !draft.trim()">Ask</Button>
      </form>
    </SheetContent>
  </Sheet>
</template>
