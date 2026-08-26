<script setup lang="ts">
  /** Segmented control — v3's `.seg` tab switch (By disease / By family, All / Novel only). */
  defineOptions({ name: 'ActTabs' })
  defineProps<{ modelValue: string; options: { value: string; label: string }[] }>()
  defineEmits<{ (e: 'update:modelValue', v: string): void }>()
</script>

<template>
  <div class="inline-flex rounded-lg border border-border bg-secondary/60 p-0.5">
    <button
      v-for="o in options" :key="o.value" type="button"
      class="rounded-md px-3 py-1 text-[12px] transition-colors"
      :class="o.value === modelValue
        ? 'bg-card font-medium text-foreground shadow-sm'
        : 'text-muted-foreground hover:text-foreground'"
      :aria-selected="o.value === modelValue"
      @click="$emit('update:modelValue', o.value)"
    >{{ o.label }}</button>
  </div>
</template>
