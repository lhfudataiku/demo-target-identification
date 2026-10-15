import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import { Dataset, Flow, Gear, ListNumbered, Odometer } from '@dataiku/vue-icons'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import ShortlistView from '@/views/ShortlistView.vue'
import EvidenceView from '@/views/EvidenceView.vue'
import TherapeuticAreaView from '@/views/TherapeuticAreaView.vue'
import CalibrationView from '@/views/CalibrationView.vue'
import SettingsView from '@/views/SettingsView.vue'

// ── The four acts ───────────────────────────────────────────────────────────
const coreRoutes: RouteRecordRaw[] = [
  {
    path: 'evidence',
    name: 'evidence',
    component: EvidenceView,
    meta: { title: 'The evidence base', icon: Dataset, menu: 'primary', order: 1 },
  },
  {
    path: 'calibration',
    name: 'calibration',
    component: CalibrationView,
    meta: { title: 'Calibration', icon: Odometer, menu: 'primary', order: 2 },
  },
  {
    path: 'therapeutic-area',
    name: 'therapeutic-area',
    component: TherapeuticAreaView,
    meta: { title: 'The therapeutic area', icon: Flow, menu: 'primary', order: 3 },
  },
  {
    path: 'shortlist',
    name: 'shortlist',
    component: ShortlistView,
    meta: { title: 'The list', icon: ListNumbered, menu: 'primary', order: 4 },
  },
]

// Footer (tertiary) routes.
const footerRoutes: RouteRecordRaw[] = [
  {
    path: 'settings',
    name: 'settings',
    component: SettingsView,
    meta: { title: 'Settings', icon: Gear, menu: 'tertiary', order: 1 },
  },
]

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: DefaultLayout,
    children: [
      // Root redirects to the first enabled primary route (see below).
      {
        path: '',
        name: 'home',
        redirect: () => ({ name: firstEnabledRoute() }),
        meta: { hiddenInMenu: true },
      },
      ...coreRoutes,
      ...footerRoutes,
      // Unknown URLs fall through to a valid page.
      {
        path: ':pathMatch(.*)*',
        name: 'notFound',
        redirect: () => ({ name: firstEnabledRoute() }),
        meta: { hiddenInMenu: true },
      },
    ],
  },
]

// DSS owns the page URL, so routes live after the hash (`…/webapps/view#/shortlist`).
const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// First registered primary route, lowest `order` first (fallback: evidence).
// Used by the home and unknown-URL redirects.
function firstEnabledRoute(): string {
  const primary = router
    .getRoutes()
    .filter((r) => r.meta?.menu === 'primary' && r.name)
    .sort((a, b) => ((a.meta?.order as number) ?? 0) - ((b.meta?.order as number) ?? 0))
  return (primary[0]?.name as string) ?? 'evidence'
}

export default router
