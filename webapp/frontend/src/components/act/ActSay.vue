<script setup lang="ts">
  /**
   * The mockup's `.say` block — the line to actually say out loud, or the
   * caveat that must travel with a number. Visually distinct from body copy
   * because in the room it is a different kind of statement.
   */
  defineOptions({ name: 'ActSay' })
</script>

<template>
  <div class="rounded-lg border-l-2 border-primary bg-secondary/70 px-3.5 py-2.5 text-[13px] leading-relaxed">
    <slot />
  </div>
</template>
