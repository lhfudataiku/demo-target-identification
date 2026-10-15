<script setup lang="ts">
  import { useThemeMode } from 'bs-blueprint'

  // Applies the kit theme once for the app. The demo is light-only; a dark-mode
  // switch would expose isDark from useThemeMode() in Settings.
  useThemeMode('light')
</script>

<template>
  <router-view />
</template>
