import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import { Gear, ListNumbered, ShieldCheck } from '@dataiku/vue-icons'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import ShortlistView from '@/views/ShortlistView.vue'
import TrustView from '@/views/TrustView.vue'
import SettingsView from '@/views/SettingsView.vue'

// ── The list leads (DEC-DEMO-005) ───────────────────────────────────────────
// Act 4 is the home page. Acts 1–3 are the three sections of one page, reached
// from the list's "How do we know?" links (`/trust?section=graph|reconstruction|family`).
const coreRoutes: RouteRecordRaw[] = [
  {
    path: 'shortlist',
    name: 'shortlist',
    component: ShortlistView,
    meta: { title: 'The shortlist', icon: ListNumbered, menu: 'primary', order: 1 },
  },
  {
    path: 'trust',
    name: 'trust',
    component: TrustView,
    meta: { title: 'Why trust the list', icon: ShieldCheck, menu: 'primary', order: 2 },
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

// First registered primary route, lowest `order` first (fallback: shortlist).
// Used by the home and unknown-URL redirects.
function firstEnabledRoute(): string {
  const primary = router
    .getRoutes()
    .filter((r) => r.meta?.menu === 'primary' && r.name)
    .sort((a, b) => ((a.meta?.order as number) ?? 0) - ((b.meta?.order as number) ?? 0))
  return (primary[0]?.name as string) ?? 'shortlist'
}

export default router
