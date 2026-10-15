<script setup lang="ts">
  import { useThemeMode } from 'bs-blueprint'

  // Applies the kit theme once for the app. The demo is light-only (see the
  // alignment plan's non-goals); a dark-mode switch would expose isDark here.
  useThemeMode('light')
</script>

<template>
  <router-view />
</template>
