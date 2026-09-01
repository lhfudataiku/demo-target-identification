<script setup lang="ts">
/**
 * ChartsView — medical-information ticket dashboard.
 *
 * Renders a self-contained mock dashboard for the pharma medical-information
 * team: KPI cards, weekly answering trends, today's ticket queue, triage
 * guidance, and routing charts.
 *
 * All data comes from the local mock-data file
 * (frontend/src/data/mock/medical-info-tickets.ts) — no backend call, no
 * store. Replace the mock exports with real DSS dataset reads when
 * productionising.
 *
 * Enabled when ENABLE_CHARTS=1 in app.env.
 */
import { CircleAlert, Clock3, MessageSquareMore, SendToBack } from 'lucide-vue-next'
import KpiCard from '@/components/dashboard/KpiCard.vue'
import TicketTrendChart from '@/components/dashboard/TicketTrendChart.vue'
import RoutingMixDonut from '@/components/dashboard/RoutingMixDonut.vue'
import TopicRoutingBarChart from '@/components/dashboard/TopicRoutingBarChart.vue'
import {
  kpis,
  dateLabel,
  pageLabel,
  routingMix,
  ticketTrend,
  topicVolumes,
  triageLanes,
  timeWindowLabel,
} from '@/data/mock/medical-info-tickets'

defineOptions({ name: 'ChartsView' })

function triageSectionClass(title: string): string {
  if (title.includes('Medical Information')) return 'border-primary/12 bg-primary/5'
  if (title.includes('Pharmacovigilance')) return 'border-destructive/12 bg-destructive/5'
  return 'border-chart-4/18 bg-chart-4/8'
}

function takeawaySectionClass(kind: string): string {
  if (kind === 'risk') return 'border-primary/12 bg-primary/5'
  if (kind === 'reroute') return 'border-chart-3/18 bg-chart-3/6'
  return 'border-chart-2/18 bg-chart-2/8'
}
</script>

<template>
  <div class="h-full flex flex-col bg-[linear-gradient(180deg,var(--background)_0%,color-mix(in_oklab,var(--muted)_28%,white)_100%)]">
    <header class="shrink-0 border-b px-8 py-4 flex items-center justify-between gap-4 bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div>
        <h1 class="text-xl font-semibold tracking-tight">{{ pageLabel }}</h1>
        <p class="text-sm text-muted-foreground mt-0.5">
          Ticket flow for healthcare-professional questions sent to the pharma company's medical information team.
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border bg-card text-xs font-medium text-muted-foreground">
          <span class="w-1.5 h-1.5 rounded-full bg-primary" />
          {{ timeWindowLabel }}
        </span>
        <span class="inline-flex items-center px-2.5 py-1 rounded-md border bg-card text-xs font-medium text-muted-foreground">
          {{ dateLabel }}
        </span>
      </div>
    </header>
    <div class="flex-1 overflow-y-auto">
    <div class="max-w-[1400px] mx-auto p-8 space-y-6">

      <section class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard :kpi="kpis.ticketsReceivedToday" :icon="MessageSquareMore" accent="var(--chart-3)" />
        <KpiCard :kpi="kpis.answeredWithinSla" :icon="CircleAlert" accent="var(--chart-1)" />
        <KpiCard :kpi="kpis.firstResponseTime" :icon="Clock3" accent="var(--primary)" />
        <KpiCard :kpi="kpis.reroutedAfterTriage" :icon="SendToBack" accent="var(--chart-2)" />
      </section>

      <section class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <article class="lg:col-span-8 rounded-xl border border-primary/10 bg-[linear-gradient(180deg,color-mix(in_oklab,var(--primary)_5%,white)_0%,var(--card)_22%)] p-5 flex flex-col shadow-sm">
          <header class="mb-3">
            <h2 class="text-base font-semibold">Question answering trend</h2>
            <p class="text-xs text-muted-foreground mt-0.5">
              Weekly intake, MI-handled volume, and SLA attainment across {{ timeWindowLabel.toLowerCase() }}.
            </p>
          </header>
          <div class="flex-1 min-h-[300px]">
            <TicketTrendChart :data="ticketTrend" />
          </div>
        </article>

        <article class="lg:col-span-4 rounded-xl border border-chart-3/8 bg-[linear-gradient(180deg,hsl(338_60%_97%)_0%,var(--card)_30%)] p-5 flex flex-col shadow-sm">
          <header class="mb-3">
            <h2 class="text-base font-semibold">Today's routing split</h2>
            <p class="text-xs text-muted-foreground mt-0.5">
              Which tickets stay with medical information versus move to another team.
            </p>
          </header>
          <div class="flex-1 min-h-[300px]">
            <RoutingMixDonut :data="routingMix" />
          </div>
        </article>
      </section>

      <section>
        <article class="rounded-xl border border-primary/10 bg-[linear-gradient(180deg,color-mix(in_oklab,var(--primary)_4%,white)_0%,var(--card)_22%)] p-5 shadow-sm">
          <header class="mb-4">
            <h2 class="text-base font-semibold">Triage playbook</h2>
            <p class="text-xs text-muted-foreground mt-0.5">
              Use these routing rules to decide whether the ticket belongs with medical information.
            </p>
          </header>
          <div class="space-y-3">
            <section
              v-for="lane in triageLanes"
              :key="lane.title"
              class="rounded-lg border p-4"
              :class="triageSectionClass(lane.title)"
            >
              <div class="flex items-start justify-between gap-3">
                <div>
                  <h3 class="text-sm font-semibold">{{ lane.title }}</h3>
                  <p class="text-xs text-muted-foreground mt-1">{{ lane.description }}</p>
                </div>
                <span class="inline-flex rounded-md bg-card px-2 py-1 text-[11px] font-medium text-muted-foreground border">
                  {{ lane.badge }}
                </span>
              </div>
              <div class="mt-3">
                <p class="text-[11px] uppercase tracking-wide text-muted-foreground">Owner</p>
                <p class="text-sm font-medium mt-1">{{ lane.owner }}</p>
              </div>
              <ul class="mt-3 space-y-2 text-sm text-foreground">
                <li v-for="example in lane.examples" :key="example" class="flex gap-2">
                  <span class="mt-1 h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
                  <span>{{ example }}</span>
                </li>
              </ul>
            </section>
          </div>
        </article>
      </section>

      <section class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <article class="rounded-xl border border-chart-4/12 bg-[linear-gradient(180deg,color-mix(in_oklab,var(--chart-4)_6%,white)_0%,var(--card)_25%)] p-5 flex flex-col shadow-sm">
          <header class="mb-3">
            <h2 class="text-base font-semibold">Question themes by routing outcome</h2>
            <p class="text-xs text-muted-foreground mt-0.5">
              Topics dominated by rerouting are candidates for better intake rules or auto-forwarding.
            </p>
          </header>
          <div class="flex-1 min-h-[320px]">
            <TopicRoutingBarChart :data="topicVolumes" />
          </div>
        </article>

        <article class="rounded-xl border border-chart-2/12 bg-[linear-gradient(180deg,color-mix(in_oklab,var(--chart-2)_5%,white)_0%,var(--card)_24%)] p-5 shadow-sm">
          <header class="mb-3">
            <h2 class="text-base font-semibold">Operational takeaways</h2>
            <p class="text-xs text-muted-foreground mt-0.5">
              Where the medical information team should focus next.
            </p>
          </header>
          <div class="space-y-4">
            <section class="rounded-lg border p-4" :class="takeawaySectionClass('risk')">
              <p class="text-xs uppercase tracking-wide text-muted-foreground">Backlog risk</p>
              <p class="mt-2 text-lg font-semibold">High-urgency scientific tickets are under control</p>
              <p class="mt-1 text-sm text-muted-foreground">
                Only one high-priority ticket in today's list stays with medical information, and it is already ready for response drafting.
              </p>
            </section>
            <section class="rounded-lg border p-4" :class="takeawaySectionClass('reroute')">
              <p class="text-xs uppercase tracking-wide text-muted-foreground">Reroute opportunity</p>
              <p class="mt-2 text-lg font-semibold">Safety and quality still create avoidable MI touches</p>
              <p class="mt-1 text-sm text-muted-foreground">
                Adverse-event mentions and packaging complaints together account for most of the rerouted themes, which suggests front-door triage can be tightened.
              </p>
            </section>
            <section class="rounded-lg border p-4" :class="takeawaySectionClass('next')">
              <p class="text-xs uppercase tracking-wide text-muted-foreground">Recommended next step</p>
              <p class="mt-2 text-lg font-semibold">Add explicit intake prompts for case capture</p>
              <p class="mt-1 text-sm text-muted-foreground">
                Ask callers and portal users whether a patient event or product defect is being reported before the ticket lands in the MI queue.
              </p>
            </section>
          </div>
        </article>
      </section>
    </div>
    </div>
  </div>
</template>
