// Design-system rules from bs-blueprint (see DESIGN.md). Add your own config after the spread.
import { designConfig } from 'bs-blueprint/eslint'

export default [
  { ignores: ['node_modules/**', 'dist/**'] },
  // Chart-internal label classes, sized in their component's scoped <style>
  // (see docs/demo/WEBAPP_DESIGN.md §3.5).
  ...designConfig({ entryPoint: 'src/style.css', ignore: ['^matrix-tick$', '^grid-tick$', '^grid-gene$'] }),
]
