<script setup lang="ts">
  /**
   * Info affordance next to a column header or filter.
   *
   * The tooltip is `position: fixed` and positioned on hover rather than a
   * child of the icon. Two reasons: the ranked list scrolls horizontally, and
   * `overflow-x: auto` clips descendants in BOTH axes — an absolutely
   * positioned bubble inside the table would be cut off. Native `title` was
   * tried first and technically worked, but a 13px target with a ~1s browser
   * delay reads as broken.
   */
  import { ref } from 'vue'

  defineOptions({ name: 'ActInfo' })
  defineProps<{ text: string }>()

  const open = ref(false)
  const x = ref(0)
  const y = ref(0)

  function show(e: Event) {
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect()
    // Clamp so a tooltip near the right edge stays on screen.
    x.value = Math.min(r.left + r.width / 2, window.innerWidth - 150)
    y.value = r.bottom + 6
    open.value = true
  }
</script>

<template>
  <span
    class="ml-1 inline-grid size-[13px] cursor-help place-items-center rounded-full border
           border-current align-[1px] font-sans text-[9px] leading-none opacity-45
           transition-opacity hover:opacity-100 focus:opacity-100"
    tabindex="0" role="note" :aria-label="text"
    @mouseenter="show" @focus="show" @mouseleave="open = false" @blur="open = false"
  >i</span>

  <Teleport to="body">
    <span
      v-if="open"
      class="pointer-events-none fixed z-[9999] max-w-[280px] -translate-x-1/2 rounded-md border
             border-border bg-popover px-2.5 py-1.5 text-[12px] font-normal normal-case leading-snug
             tracking-normal text-popover-foreground shadow-lg"
      :style="{ left: x + 'px', top: y + 'px' }"
      role="tooltip"
    >{{ text }}</span>
  </Teleport>
</template>
