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
  import { computed, nextTick, ref, watch } from 'vue'
  import {
    Button, Collapsible, CollapsibleContent, CollapsibleTrigger, Sheet, SheetContent, SheetDescription,
    SheetHeader, SheetTitle, Spinner, Textarea,
  } from '@dataiku/ea-ui-kit'
  import {
    AiAgent, ArrowExternalLink, CheckmarkCircleFill, ChevronDown, ChevronRight, ErrorCircleFill, Send,
  } from '@dataiku/vue-icons'
  import { postStream } from '@/utils/postStream'
  import {
    TOOL_LABEL, type CheckedAnswer, type CheckedSentence, type Citation, type ToolActivity,
  } from './types'

  const props = defineProps<{ diseaseIndex: number; geneIndex: number; gene: string; diseaseName: string }>()
  const open = defineModel<boolean>('open', { default: false })

  interface Turn { question: string; raw: string; tools: ToolActivity[]; answer: CheckedAnswer | null; error: string | null }
  const turns = ref<Turn[]>([])
  const draft = ref('')
  const busy = ref(false)
  const openGraph = ref<Record<string, boolean>>({})
  const scroller = ref<HTMLElement | null>(null)
  let controller: AbortController | null = null

  function reset() {
    controller?.abort(); turns.value = []; draft.value = ''; busy.value = false; openGraph.value = {}
  }
  watch(() => [props.diseaseIndex, props.geneIndex], reset)

  const starters = computed(() => [
    `What is known about ${props.gene} in ${props.diseaseName}?`,
    `Which drugs act on ${props.gene}, and for which diseases?`,
    `How is ${props.gene} connected in the graph to the genes already linked to ${props.diseaseName}?`,
    `Which trials select patients by ${props.gene}?`,
  ])

  async function toBottom() {
    await nextTick()
    scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' })
  }

  async function ask(question: string) {
    const q = question.trim()
    if (!q || busy.value) return
    const history = turns.value.filter((t) => t.answer).flatMap((t) => [
      { role: 'user', content: t.question }, { role: 'assistant', content: t.raw },
    ])
    turns.value.push({ question: q, raw: '', tools: [], answer: null, error: null })
    const live = turns.value[turns.value.length - 1]
    draft.value = ''; busy.value = true
    void toBottom()
    controller = new AbortController()
    try {
      await postStream('/api/assistant', { disease: props.diseaseIndex, gene: props.geneIndex, question: q, history },
        (e) => {
          if (e.type === 'text_delta') live.raw += String(e.content ?? '')
          else if (e.type === 'tool_call_started') live.tools.push({
            id: String(e.id), name: String(e.name), query: String((e.args as { query?: string })?.query ?? ''),
            done: false, ok: true, summary: '' })
          else if (e.type === 'tool_call_completed') {
            const t = live.tools.find((x) => x.id === String(e.id) && !x.done)
            if (t) { t.done = true; t.ok = Boolean(e.ok); t.summary = String(e.summary ?? '') }
          } else if (e.type === 'answer') live.answer = e as unknown as CheckedAnswer
          else if (e.type === 'error') live.error = String(e.message)
          void toBottom()
        }, controller.signal)
    } catch (err) {
      if (!controller.signal.aborted) live.error = err instanceof Error ? err.message : String(err)
    } finally {
      // A search the stream never closed is not left spinning once the turn is over.
      for (const t of live.tools) if (!t.done) { t.done = true; t.ok = false; t.summary = t.summary || 'no result' }
      busy.value = false
    }
  }

  /** Consecutive sentences of one answer line form a paragraph; consecutive list items form one list. */
  interface Block { item: boolean; lines: CheckedSentence[][] }
  function blocks(sentences: CheckedSentence[]): Block[] {
    const out: Block[] = []
    let line = -1
    for (const s of sentences) {
      const last = out[out.length - 1]
      if (s.block === line && last) last.lines[last.lines.length - 1].push(s)
      else if (s.item && last?.item) last.lines.push([s])
      else out.push({ item: s.item, lines: [[s]] })
      line = s.block
    }
    return out
  }

  /** Bold spans the model wrote despite the prompt, rendered as text, never as HTML. */
  function segments(text: string): { text: string; bold: boolean }[] {
    return text.split(/\*\*(.+?)\*\*/).map((t, i) => ({ text: t.replace(/\*\*/g, ''), bold: i % 2 === 1 })).filter((s) => s.text)
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
    <SheetContent side="right" class="flex w-full flex-col gap-0 sm:max-w-2xl">
      <SheetHeader class="border-b border-border pr-12">
        <SheetTitle class="flex items-center gap-2">
          <AiAgent class="size-4 shrink-0 text-primary" /> Ask about {{ gene }} in {{ diseaseName }}
        </SheetTitle>
        <SheetDescription>
          Answers cite the model's numbers, the drug records, the trials and papers, and the graph queries they
          rely on. A sentence marked <i>not from a retrieved source</i> comes from the model's general knowledge.
          Nothing is stored.
        </SheetDescription>
      </SheetHeader>

      <div ref="scroller" class="flex flex-1 flex-col gap-6 overflow-y-auto p-4">
        <div v-if="!turns.length" class="flex flex-col gap-2">
          <p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Start with</p>
          <Button v-for="s in starters" :key="s" variant="outline"
                  class="h-auto justify-start whitespace-normal py-2.5 text-left font-normal" @click="ask(s)">{{ s }}</Button>
        </div>

        <section v-for="(t, i) in turns" :key="i" class="flex flex-col gap-3">
          <p class="ml-auto max-w-lg rounded-lg bg-primary/10 px-3 py-2 text-sm text-foreground">{{ t.question }}</p>

          <ul v-if="t.tools.length" class="flex flex-col divide-y divide-border rounded-md border border-border bg-muted/40">
            <li v-for="a in t.tools" :key="a.id" class="flex items-start gap-2 px-3 py-2 text-xs">
              <Spinner v-if="!a.done" class="mt-0.5 size-3.5 shrink-0" />
              <CheckmarkCircleFill v-else-if="a.ok" class="mt-0.5 size-3.5 shrink-0 text-success" />
              <ErrorCircleFill v-else class="mt-0.5 size-3.5 shrink-0 text-destructive" />
              <div class="flex min-w-0 flex-1 flex-col gap-0.5">
                <span class="font-medium text-foreground">{{ TOOL_LABEL[a.name] ?? a.name }}</span>
                <span class="text-muted-foreground">{{ a.query }}</span>
              </div>
              <span v-if="a.summary" class="shrink-0 text-muted-foreground" :class="a.ok ? '' : 'text-destructive'">{{ a.summary }}</span>
            </li>
          </ul>

          <p v-if="t.error" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{{ t.error }}</p>

          <!-- The checked answer replaces the streamed text -->
          <div v-if="t.answer" class="flex flex-col gap-3 text-sm leading-relaxed text-foreground">
            <template v-for="(b, k) in blocks(t.answer.sentences)" :key="k">
              <component :is="b.item ? 'ul' : 'div'" :class="b.item ? 'flex list-disc flex-col gap-1 pl-5' : ''">
                <component :is="b.item ? 'li' : 'p'" v-for="(line, l) in b.lines" :key="l">
                  <span v-for="(s, j) in line" :key="j" :class="s.general_knowledge ? 'text-muted-foreground' : ''">
                    <template v-for="(seg, m) in segments(s.text)" :key="m"><strong v-if="seg.bold" class="font-semibold">{{ seg.text }}</strong><template v-else>{{ seg.text }}</template></template>
                    <template v-for="c in s.citations" :key="c.ref">
                      <a v-if="citationUrl(c)" :href="citationUrl(c)" target="_blank" rel="noopener" :title="c.label ?? c.ref"
                         class="ml-1 inline-flex items-center gap-0.5 rounded bg-primary/10 px-1 align-baseline font-mono text-2xs text-primary hover:underline">{{ c.ref }}<ArrowExternalLink class="size-2.5" /></a>
                      <span v-else :title="c.label ?? c.ref"
                            class="ml-1 rounded bg-primary/10 px-1 align-baseline font-mono text-2xs text-primary">{{ c.ref }}</span>
                    </template>
                    <span v-if="s.general_knowledge"
                          class="ml-1 whitespace-nowrap rounded border border-border px-1 align-baseline text-2xs italic text-muted-foreground">not from a retrieved source</span>
                    <span v-if="s.unresolved.length"
                          class="ml-1 rounded bg-warning/15 px-1 align-baseline text-2xs text-warning">citation removed: {{ s.unresolved.join(', ') }}</span>
                    <span v-if="s.prescriptive" class="ml-1 rounded bg-warning/15 px-1 align-baseline text-2xs text-warning">prescriptive</span>
                    {{ ' ' }}
                  </span>
                </component>
              </component>
            </template>

            <div v-if="t.answer.graph.length" class="flex flex-col divide-y divide-border rounded-md border border-border">
              <Collapsible v-for="g in t.answer.graph" :key="g.id" v-model:open="openGraph[`${i}-${g.id}`]">
                <CollapsibleTrigger as-child>
                  <Button variant="ghost" class="h-auto w-full items-start justify-start gap-2 whitespace-normal rounded-none px-3 py-2 text-left text-xs font-normal">
                    <component :is="openGraph[`${i}-${g.id}`] ? ChevronDown : ChevronRight" class="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
                    <span class="rounded bg-primary/10 px-1 font-mono text-2xs text-primary">{{ g.id }}</span>
                    <span class="min-w-0 flex-1 text-foreground">{{ g.title ?? g.query }}</span>
                    <span class="shrink-0 text-muted-foreground">{{ g.rows }} rows</span>
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent class="flex flex-col gap-2 px-3 pb-3 pl-9">
                  <pre class="whitespace-pre-wrap break-words rounded-md bg-muted p-2 font-mono text-2xs">{{ g.cypher }}</pre>
                  <p v-for="(names, type) in g.names" :key="type" class="text-xs">
                    <span class="text-muted-foreground">{{ type }} ({{ g.distinct[type] }}):</span> {{ names.join(', ') }}<template
                      v-if="g.distinct[type] > names.length"> …</template>
                  </p>
                </CollapsibleContent>
              </Collapsible>
            </div>

            <p class="text-xs text-muted-foreground">
              {{ t.answer.counts.cited }} of {{ t.answer.counts.sentences }} sentences cite a source · {{ t.answer.seconds }} s<template
                v-if="t.answer.tool_errors.length"> · {{ t.answer.tool_errors.length }} search failed</template>
            </p>
          </div>
          <p v-else-if="t.raw" class="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">{{ t.raw }}</p>
          <div v-else-if="busy && i === turns.length - 1 && !t.error" class="flex items-center gap-2 text-xs text-muted-foreground">
            <Spinner class="size-3.5" /> Thinking…
          </div>
        </section>
      </div>

      <form class="flex flex-col gap-2 border-t border-border p-4" @submit.prevent="ask(draft)">
        <div class="flex items-end gap-2">
          <Textarea v-model="draft" rows="2" class="min-h-0 flex-1 resize-none" :disabled="busy"
                    :placeholder="`Ask about ${gene} in ${diseaseName}`" @keydown.enter.exact.prevent="ask(draft)" />
          <Button type="submit" size="icon" :disabled="busy || !draft.trim()" aria-label="Ask"><Send class="size-4" /></Button>
        </div>
        <div class="flex items-center justify-between text-2xs text-muted-foreground">
          <span>Enter to ask · Shift+Enter for a new line</span>
          <Button v-if="turns.length" type="button" variant="ghost" size="sm" class="h-auto px-1 py-0 text-2xs"
                  :disabled="busy" @click="reset">New conversation</Button>
        </div>
      </form>
    </SheetContent>
  </Sheet>
</template>
