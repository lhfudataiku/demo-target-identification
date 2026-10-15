<script setup lang="ts">
  /** Segmented control (By disease / By family, All / Novel only), on the kit's ToggleGroup. */
  import { ToggleGroup, ToggleGroupItem } from '@dataiku/ea-ui-kit'

  defineOptions({ name: 'ActTabs' })
  defineProps<{ modelValue: string; options: { value: string; label: string }[] }>()
  const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

  // A single-choice ToggleGroup lets the user click the active item off, which
  // emits an empty value. A segmented control always has one choice, so ignore it.
  function select(v: unknown) {
    if (typeof v === 'string' && v) emit('update:modelValue', v)
  }
</script>

<template>
  <ToggleGroup type="single" variant="outline" size="sm" :model-value="modelValue"
               @update:model-value="select">
    <ToggleGroupItem v-for="o in options" :key="o.value" :value="o.value" class="px-3 text-xs">
      {{ o.label }}
    </ToggleGroupItem>
  </ToggleGroup>
</template>
