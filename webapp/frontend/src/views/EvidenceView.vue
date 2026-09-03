<script setup lang="ts">
  /**
   * Act 1 — the evidence base.
   *
   * "What went in?" — public biomedical knowledge, assembled, with provenance
   * on every node and edge.
   *
   * Two things this act must NOT do:
   *  - claim quality. Faithful assembly is a lineage property, not an accuracy
   *    one; whether the ranking is any good is act 2's job.
   *  - imply discovery. The opening card states the reconstruction claim and
   *    the five things we are explicitly not claiming, because that framing is
   *    what keeps the rest of the demo honest.
   *
   * COPY CONTRACT (2026-09-03). Titles name the card and never argue; the
   * subtitle carries the finding; the insight that will not fit goes in #note;
   * methodology and internal references go in the collapsed #method; presenter
   * script goes in #presenter and is hidden in client mode. Every data-science
   * and biology term is an <ActTerm>, defined once in utils/glossary.ts.
   *
   * Two things were removed here rather than reworded. The subtitle on the
   * evidence-type card forward-referenced "Act 5", and this app has four acts.
   * The relation card cited `GRAPH_BUILDING.md §7.1` at a client; the claim it
   * makes is worth keeping, so it moved into #method phrased against the
   * reference rather than against the document that records it.
   */
  import { computed, onMounted, ref } from 'vue'
  import { apiUrl } from '@/utils/api'
  import ActCard from '@/components/act/ActCard.vue'
  import ActStat from '@/components/act/ActStat.vue'
  import ActBar from '@/components/act/ActBar.vue'
  import ActDonut from '@/components/act/ActDonut.vue'
  import ActTerm from '@/components/act/ActTerm.vue'
  import ActInfo from '@/components/act/ActInfo.vue'
  import VisualGraphExplorerCard from '@/components/graph/VisualGraphExplorerCard.vue'
  import { ACT1_EXPLORER_QUERIES } from '@/utils/a1ExplorerQueries'
  import { Database, GitBranch, Layers, FileText } from 'lucide-vue-next'

  defineOptions({ name: 'EvidenceView' })

  interface Bar { label: string; count: number }
  interface Payload {
    node_types: Bar[]; relations: Bar[]; node_sources: Bar[]
    ppi_provenance: Bar[]; label_evidence: Bar[]
    totals: Record<string, number>
  }

  const data = ref<Payload | null>(null)
  const error = ref<string | null>(null)

  const fmt = (n: number) => n.toLocaleString()

  // v3 colours these two cards by GROUP, not by a cycle:
  //   PPI provenance  — corroborated by 2+ interactomes vs a single source
  //   node sources    — the six external vocabularies vs the one we derived
  const ppiRows = computed(() => (data.value?.ppi_provenance ?? []).map((r) => ({
    ...r, colour: r.label.includes('+') ? 'var(--chart-2)' : 'var(--chart-1)',
  })))
  const sourceRows = computed(() => (data.value?.node_sources ?? []).map((r) => ({
    ...r, colour: /grouped/i.test(r.label) ? 'var(--muted-foreground)' : 'var(--chart-2)',
  })))

  /** EXTERNAL sources only. `totals.sources` counts rows in
      graph_node_source_counts, which is 7: the six published vocabularies plus
      `MONDO_grouped`, a grouping we derived. Rendering 7 under a subtitle that
      says six is the contradiction the presenter note existed to manage, so the
      tile now counts what it claims to count. Same /grouped/i test the bar
      colouring already uses. */
  const externalSources = computed(() => {
    const rows = data.value?.node_sources ?? []
    return rows.length ? rows.filter((r) => !/grouped/i.test(r.label)).length : null
  })

  /** Share of PPI edges asserted by more than one interactome — the finding the
      provenance card's subtitle states, derived rather than typed. */
  const corroboratedPct = computed(() => {
    const rows = data.value?.ppi_provenance ?? []
    const total = rows.reduce((a, r) => a + r.count, 0)
    if (!total) return null
    const multi = rows.filter((r) => r.label.includes('+')).reduce((a, r) => a + r.count, 0)
    return Math.round((100 * multi) / total)
  })

  /** The largest evidence type, named in the subtitle so the card says which
      kind of evidence the model's label is actually made of. The dataset stores
      these as column values (`genetic_association`), which must not reach a
      client's screen as typed. */
  const humanise = (s: string) => s.replace(/_/g, ' ').replace(/\+/g, ' + ')
  const topEvidence = computed(() => {
    const rows = [...(data.value?.label_evidence ?? [])].sort((a, b) => b.count - a.count)
    if (!rows.length) return null
    const total = rows.reduce((a, r) => a + r.count, 0)
    return { label: humanise(rows[0].label), pct: Math.round((100 * rows[0].count) / total) }
  })

  // The six external vocabularies, in one line each. A client reads bare
  // acronyms as noise and an engineer reads them as unverifiable.
  const SOURCES: [string, string][] = [
    ['GO', 'Gene Ontology — what a protein does, where it does it, and which process it belongs to.'],
    ['MONDO', 'A curated disease vocabulary that reconciles the names different registries use for the same disease.'],
    ['NCBI', 'The US national sequence and gene registry — the canonical identifier for a human gene.'],
    ['HPO', 'Human Phenotype Ontology — the observable signs and symptoms clinicians record.'],
    ['DrugBank', 'A curated catalogue of drugs, what they target and what they are approved for.'],
    ['REACTOME', 'An expert-curated catalogue of biological pathways — the chains of molecular steps cells run.'],
  ]

  onMounted(async () => {
    try {
      const res = await fetch(apiUrl('/api/evidence'))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      data.value = await res.json()
    } catch (e) {
      error.value = `Could not load the evidence base: ${e instanceof Error ? e.message : String(e)}`
    }
  })

  const totals = computed(() => data.value?.totals)
</script>

<template>
  <div class="flex flex-col gap-6 p-6">
    <header class="flex flex-col gap-1.5 border-b border-border pb-5">
      <p class="font-mono text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
        Act 1 of 4 · The evidence base
      </p>
      <h1 class="font-serif text-3xl font-semibold tracking-tight">What went in?</h1>
      <p class="max-w-3xl text-sm leading-relaxed text-muted-foreground">
        Public biomedical knowledge, assembled from six external sources and accepted against a
        frozen reference. No model yet — this act is about what the machine can see, and about the
        fact that every <ActTerm t="node" /> and <ActTerm t="edge" /> can name where it came from.
      </p>
    </header>

    <p v-if="error" class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
      {{ error }}
    </p>

    <div class="grid grid-cols-12 gap-4">
      <ActCard span="col-span-12" title="The knowledge graph" :icon="Database"
               :chips="[['live', 'live']]"
               :src="['graph_node_type_counts', 'graph_relation_counts', 'graph_ppi_provenance']">
        <template #desc>
          Public biomedical knowledge from six sources, assembled into one connected
          <ActTerm t="knowledge-graph">map</ActTerm> of genes, diseases, drugs and pathways.
        </template>

        <div v-if="totals" class="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <ActStat label="Nodes" :value="fmt(totals.nodes)" :sub="`${totals.node_types} types`" />
          <ActStat label="Edges" :value="fmt(totals.edges)" :sub="`${totals.relations} relations`" />
          <ActStat label="Edges with provenance" :value="fmt(totals.edges_with_provenance)"
                   sub="protein interactions naming their source" />
          <ActStat label="External sources" :value="externalSources ?? '—'"
                   :sub="totals.sources > (externalSources ?? 0)
                     ? `plus ${totals.sources - (externalSources ?? 0)} grouping we derived`
                     : undefined" />
        </div>
        <p v-else class="py-4 text-center text-sm text-muted-foreground">Loading…</p>

        <div v-if="totals" class="mt-3 flex flex-wrap gap-x-4 gap-y-1">
          <span v-for="[name, def] in SOURCES" :key="name"
                class="font-mono text-[11px] text-muted-foreground">
            {{ name }}<ActInfo :text="def" />
          </span>
        </div>

        <template #note>
          <b>Assembled, not discovered.</b> Every number here is a claim about lineage — what we
          loaded and from where — never about accuracy. Whether the ranking built on it is any good
          is Act 2's question.
        </template>
      </ActCard>

      <!-- A prepared preset never executes in Target Prioritizer. The shared
           Explorer card copies it only after an explicit user action. -->
      <VisualGraphExplorerCard
        span="col-span-12"
        title="Explore the graph yourself"
        description="Three ready-made questions showing how a disease reaches proteins, pathways and drug context."
        :starter-queries="ACT1_EXPLORER_QUERIES"
        handoff="Create a new query in the Explorer, paste the copied Cypher, and run it. For an open-ended question, use the Explorer's query generator. Running another query replaces the current result."
        :chips="[['live', 'live']]"
        :src="['Kuzu folder (ytvuniN8)']"
        method-label="How this works"
      >
        <template #note>
          <b>The three presets are deliberately distinct.</b> They introduce disease-associated
          proteins and their interactions, pathway context, and drug context — without making a
          target or a safety claim about any of them.
        </template>
        <template #method>
          <p><b class="text-foreground">Nothing runs in this app.</b> Selecting a preset only prepares
            its <ActTerm t="knowledge-graph">graph</ActTerm> query. Visual Graph Explorer executes it
            and displays one result at a time; running another query replaces the current one.</p>
          <p class="mt-1.5">Each preset is written in <b class="text-foreground">Cypher</b>, the query
            language for graph databases, and each is ordered and bounded so the same demonstration
            returns the same result twice. For open-ended questions, the Explorer's own query
            generator writes the Cypher for you.</p>
        </template>
      </VisualGraphExplorerCard>

      <ActCard span="col-span-12 lg:col-span-5" title="What's in the graph" :icon="Layers"
               :chips="[['live', 'live']]" :src="['graph_node_type_counts']">
        <template #desc>
          Eight kinds of biological entity — genes, diseases, drugs, pathways and more.
        </template>
        <ActBar v-if="data" :rows="data.node_types" color="var(--chart-2)" />
        <template #note>
          Each bar is a <ActTerm t="node" /> type. The model only ever scores one pair of these —
          a gene against a disease.
        </template>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-7" title="How things connect" :icon="GitBranch"
               :chips="[['live', 'live']]" :src="['graph_relation_counts']">
        <template #desc>
          Eighteen <ActTerm t="relation">relationship types</ActTerm> — which protein interacts with
          which, what a drug targets, what a disease is linked to.
        </template>
        <ActBar v-if="data" :rows="data.relations" color="var(--chart-3)" />
        <template #note>
          <b>Protein–protein interactions dominate.</b> That is not an accident of this build — it is
          what the public evidence base actually looks like, and it is why most of the model's
          features read <ActTerm t="ppi">interaction</ActTerm> edges.
        </template>
        <template #method>
          <p>Counts are accepted against the frozen <ActTerm t="primekg" /> reference rather than
            trusted from the build: the seven largest relation counts reproduce it exactly. The
            reference is never rebuilt, so a drift in these numbers means a change in our assembly,
            not in the source.</p>
        </template>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-5" title="Where the data came from" :icon="Database"
               :chips="[['live', 'live']]" :src="['graph_node_source_counts']">
        <template #desc>
          Six public reference <ActTerm t="ontology">vocabularies</ActTerm>. The grey bar is our own
          grouping, not an external source.
        </template>
        <ActBar v-if="data" :rows="sourceRows" />
        <template #note>
          Using published vocabularies means the naming is <b>somebody else's standard</b>, not ours —
          which is what makes every node in this graph resolvable back to a source a client can check.
        </template>
        <template #presenter>
          <b>Say six sources, not seven.</b> One of these bars is a grouping we derived ourselves,
          not an external vocabulary — it is the grey one.
        </template>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-7" title="Provenance on every edge"
               :icon="GitBranch" accent="var(--chart-3)"
               :chips="[['live', 'live']]" :src="['graph_ppi_provenance']">
        <template #desc>
          Every protein–protein interaction names the database that asserted
          it<template v-if="corroboratedPct !== null">, and {{ corroboratedPct }}% are corroborated by
          two or more</template>.
        </template>
        <ActBar v-if="data" :rows="ppiRows" />
        <div class="mt-2 flex gap-4 font-mono text-[10.5px] text-muted-foreground">
          <span class="flex items-center gap-1.5">
            <span class="inline-block size-2.5 rounded-sm" style="background:var(--chart-1)"></span>single source</span>
          <span class="flex items-center gap-1.5">
            <span class="inline-block size-2.5 rounded-sm" style="background:var(--chart-2)"></span>corroborated by 2+ <ActTerm t="interactome">interactomes</ActTerm></span>
        </div>
        <template #note>
          <b><ActTerm t="provenance" /> is not accuracy.</b> It records where a fact came from and how
          many sources agree — not that the fact is true. Two of the model's fourteen features read
          exactly this, and they are the two it leans on most.
        </template>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-6" title="What counts as “known”"
               :icon="FileText" accent="var(--chart-4)"
               :chips="[['live', 'live']]" :src="['graph_label_evidence']">
        <template #desc>
          Every gene–disease <ActTerm t="association" /> carries an
          <ActTerm t="evidence-type" />, and they are not equally
          strong<template v-if="topEvidence"> — {{ topEvidence.pct }}% of them are
          “{{ topEvidence.label }}”</template>.
        </template>
        <ActDonut v-if="data" :rows="data.label_evidence" />
        <template #note>
          <b>This is the label the model learns.</b> It is trained to reproduce these associations, so
          everything downstream inherits whatever they are worth — including the fact that all three
          evidence types are treated as one flat “known”.
        </template>
      </ActCard>

      </div>
  </div>
</template>
