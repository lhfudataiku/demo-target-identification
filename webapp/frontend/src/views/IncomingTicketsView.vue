<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { ArrowRight, Inbox, Network, Route } from 'lucide-vue-next'
import { ticketFlowSample } from '@/data/mock/ticket-flow'
import { useFlowStore } from '@/stores/flow'
import { responseWorkflowTiers, todayTickets } from '@/data/mock/medical-info-tickets'

defineOptions({ name: 'IncomingTicketsView' })

const store = useFlowStore()

onMounted(() => {
  if (!store.sample && !store.loading) {
    void store.loadSample()
  }
})

const resolvedSample = computed(() => store.sample ?? ticketFlowSample)

const stages = computed(() =>
  [...resolvedSample.value.nodes].sort((left, right) => left.x - right.x || left.y - right.y),
)

const totalVisible = computed(() =>
  stages.value.reduce((sum, stage) => sum + (stage.queue_count ?? 0), 0),
)

const rerouted = computed(() =>
  stages.value.find((stage) => stage.node_type === 'reroute')?.queue_count ?? 0,
)

function stageTone(nodeType: string): string {
  if (nodeType === 'source') return 'border-chart-2/20 bg-chart-2/8'
  if (nodeType === 'transform') return 'border-primary/15 bg-primary/6'
  if (nodeType === 'enrich') return 'border-chart-4/18 bg-chart-4/8'
  if (nodeType === 'reroute') return 'border-destructive/12 bg-destructive/6'
  if (nodeType === 'output') return 'border-chart-1/18 bg-chart-1/8'
  return 'border-border bg-card'
}

function stageBadgeTone(nodeType: string): string {
  if (nodeType === 'source') return 'bg-chart-2/12 text-foreground'
  if (nodeType === 'transform') return 'bg-primary/12 text-foreground'
  if (nodeType === 'enrich') return 'bg-chart-4/12 text-foreground'
  if (nodeType === 'reroute') return 'bg-destructive/8 text-destructive'
  if (nodeType === 'output') return 'bg-chart-1/12 text-foreground'
  return 'bg-muted text-muted-foreground'
}

function urgencyClass(urgency: string): string {
  if (urgency === 'High') return 'border border-destructive/12 bg-destructive/8 text-destructive'
  if (urgency === 'Medium') return 'border border-chart-4/20 bg-chart-4/10 text-foreground'
  return 'border border-border bg-muted text-muted-foreground'
}

function recommendationClass(recommendation: string): string {
  if (recommendation === 'Medical Information') return 'border border-primary/15 bg-primary/12 text-foreground'
  if (recommendation === 'Pharmacovigilance') return 'border border-destructive/12 bg-destructive/8 text-destructive'
  if (recommendation === 'Product Quality') return 'border border-chart-4/20 bg-chart-4/10 text-foreground'
  return 'border border-chart-2/20 bg-chart-2/10 text-foreground'
}

function statusClass(status: string): string {
  if (status === 'Ready to answer') return 'border border-chart-2/20 bg-chart-2/10 text-foreground'
  if (status === 'Needs reroute') return 'border border-chart-3/20 bg-chart-3/10 text-foreground'
  return 'border border-border bg-muted text-muted-foreground'
}

function ticketRowClass(status: string): string {
  if (status === 'Ready to answer') return 'bg-chart-2/4'
  if (status === 'Needs reroute') return 'bg-chart-3/4'
  return 'bg-chart-4/4'
}
</script>

<template>
  <div class="h-full flex flex-col">
    <header class="shrink-0 border-b px-8 py-4 bg-background">
      <h1 class="text-xl font-semibold tracking-tight">Incoming Tickets</h1>
      <p class="text-sm text-muted-foreground mt-0.5">
        Live intake visualized from the same flow data used by the pipeline view.
      </p>
    </header>

    <div v-if="store.loading" class="flex-1 flex items-center justify-center">
      <div class="w-8 h-8 rounded-full bg-muted animate-pulse" />
    </div>

    <div v-else class="flex-1 overflow-auto bg-muted/20">
      <div class="max-w-7xl mx-auto p-8 space-y-6">
        <div
          v-if="store.error"
          class="rounded-xl border border-chart-2/20 bg-chart-2/8 px-4 py-3 flex items-start gap-3"
        >
          <Inbox class="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
          <div>
            <p class="text-xs text-muted-foreground">
              Live flow API unavailable ({{ store.error }}). The tab is rendering the local ticket-flow sample.
            </p>
          </div>
        </div>
        <section class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <article class="rounded-xl border border-chart-2/20 bg-chart-2/8 p-5">
            <p class="text-xs uppercase tracking-wide text-muted-foreground">Visible volume</p>
            <p class="mt-2 text-3xl font-semibold">{{ totalVisible }}</p>
            <p class="mt-1 text-sm text-muted-foreground">Tickets currently represented across the intake flow.</p>
          </article>
          <article class="rounded-xl border border-primary/15 bg-primary/6 p-5">
            <p class="text-xs uppercase tracking-wide text-muted-foreground">Decision point</p>
            <p class="mt-2 text-3xl font-semibold">Triage</p>
            <p class="mt-1 text-sm text-muted-foreground">The key step that decides whether MI answers or reroutes the request.</p>
          </article>
          <article class="rounded-xl border border-destructive/12 bg-destructive/6 p-5">
            <p class="text-xs uppercase tracking-wide text-muted-foreground">Rerouted now</p>
            <p class="mt-2 text-3xl font-semibold">{{ rerouted }}</p>
            <p class="mt-1 text-sm text-muted-foreground">Tickets that should move out of the MI queue to another team.</p>
          </article>
        </section>

        <section class="rounded-xl border bg-card p-5">
          <header class="mb-4 flex items-center gap-2">
            <Network class="w-4 h-4 text-muted-foreground" />
            <div>
              <h2 class="text-base font-semibold">Ticket Journey</h2>
              <p class="text-xs text-muted-foreground mt-0.5">A stage-by-stage view derived from the Flow block payload.</p>
            </div>
          </header>
          <div class="grid grid-cols-1 xl:grid-cols-5 gap-4">
            <article
              v-for="stage in stages"
              :key="stage.id"
              class="rounded-xl border p-4"
              :class="stageTone(stage.node_type)"
            >
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-xs uppercase tracking-wide text-muted-foreground">{{ stage.owner }}</p>
                  <h3 class="mt-2 text-lg font-semibold">{{ stage.label }}</h3>
                </div>
                <span
                  class="inline-flex rounded-md px-2 py-1 text-xs font-medium"
                  :class="stageBadgeTone(stage.node_type)"
                >
                  {{ stage.queue_count ?? 0 }} open
                </span>
              </div>
              <p class="mt-3 text-sm text-muted-foreground leading-relaxed">{{ stage.note }}</p>
              <div class="mt-4 rounded-lg bg-background/70 px-3 py-2">
                <p class="text-[11px] uppercase tracking-wide text-muted-foreground">SLA marker</p>
                <p class="mt-1 text-sm font-medium">{{ stage.sla }}</p>
              </div>
            </article>
          </div>
        </section>

        <section class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <article class="rounded-xl border border-primary/15 bg-primary/5 p-5">
            <header class="mb-4 flex items-center gap-2">
              <Route class="w-4 h-4 text-muted-foreground" />
              <div>
                <h2 class="text-base font-semibold">Agent Response And References</h2>
                <p class="text-xs text-muted-foreground mt-0.5">How the agent escalates from routine answers to bespoke medical review.</p>
              </div>
            </header>
            <div class="space-y-3">
              <div
                v-for="tier in responseWorkflowTiers"
                :key="tier.tier"
                class="rounded-lg border border-border/70 bg-background/80 px-4 py-3"
              >
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-xs uppercase tracking-wide text-muted-foreground">{{ tier.tier }}</p>
                    <p class="mt-1 text-sm font-medium">{{ tier.title }}</p>
                  </div>
                  <ArrowRight class="w-4 h-4 text-muted-foreground shrink-0 mt-1" />
                </div>
                <p class="mt-2 text-sm text-muted-foreground">{{ tier.description }}</p>
                <div class="mt-3">
                  <p class="text-[11px] uppercase tracking-wide text-muted-foreground">References</p>
                  <div class="mt-2 flex flex-wrap gap-2">
                    <span
                      v-for="reference in tier.references"
                      :key="reference"
                      class="inline-flex rounded-md border border-border bg-muted/50 px-2 py-1 text-xs text-foreground"
                    >
                      {{ reference }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </article>

          <article class="rounded-xl border border-chart-4/18 bg-chart-4/8 p-5">
            <header class="mb-4">
              <h2 class="text-base font-semibold">Today's ticket list</h2>
              <p class="text-xs text-muted-foreground mt-0.5">
                Intake items that need answering, rerouting, or more intake detail before response.
              </p>
            </header>
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b text-left text-xs uppercase tracking-wide text-muted-foreground bg-muted/30">
                    <th class="py-3 pr-4 font-medium">Ticket</th>
                    <th class="py-3 pr-4 font-medium">Topic</th>
                    <th class="py-3 pr-4 font-medium">Urgency</th>
                    <th class="py-3 pr-4 font-medium">Owner</th>
                    <th class="py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="ticket in todayTickets"
                    :key="ticket.id"
                    class="border-b last:border-b-0 align-top transition-colors"
                    :class="ticketRowClass(ticket.status)"
                  >
                    <td class="py-3 pr-4 min-w-[135px]">
                      <p class="font-medium">{{ ticket.id }}</p>
                      <p class="text-xs text-muted-foreground mt-1">{{ ticket.receivedAt }} · {{ ticket.channel }}</p>
                    </td>
                    <td class="py-3 pr-4 min-w-[220px]">
                      <p class="font-medium">{{ ticket.topic }}</p>
                      <p class="text-xs text-muted-foreground mt-1">{{ ticket.summary }}</p>
                    </td>
                    <td class="py-3 pr-4">
                      <span class="inline-flex rounded-md px-2 py-1 text-xs font-medium" :class="urgencyClass(ticket.urgency)">
                        {{ ticket.urgency }}
                      </span>
                    </td>
                    <td class="py-3 pr-4 min-w-[150px]">
                      <span class="inline-flex rounded-md px-2 py-1 text-xs font-medium" :class="recommendationClass(ticket.recommendation)">
                        {{ ticket.recommendation }}
                      </span>
                    </td>
                    <td class="py-3">
                      <span class="inline-flex rounded-md px-2 py-1 text-xs font-medium" :class="statusClass(ticket.status)">
                        {{ ticket.status }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
        </section>
      </div>
    </div>
  </div>
</template>
