// Design-system rules from bs-blueprint (see DESIGN.md). Add your own config after the spread.
import { designConfig } from 'bs-blueprint/eslint'

export default [
  { ignores: ['node_modules/**', 'dist/**'] },
  ...designConfig({ entryPoint: 'src/style.css' }),
]
