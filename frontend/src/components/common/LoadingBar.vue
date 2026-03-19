<template>
  <transition name="loading-bar-fade">
    <div v-if="isLoading" class="loading-bar-container">
      <div class="loading-bar" :style="{ width: `${progress}%` }"></div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

// Props
const props = withDefaults(
  defineProps<{
    duration?: number
  }>(),
  {
    duration: 300
  }
)

// State
const isLoading = ref(false)
const progress = ref(0)
let progressInterval: number | null = null

// Methods
const start = () => {
  isLoading.value = true
  progress.value = 0

  // Simulate progress with easing
  const step = () => {
    if (progress.value < 90) {
      // Slow down as it approaches 90%
      const increment = (90 - progress.value) * 0.1
      progress.value += Math.max(increment, 1)
    }
  }

  progressInterval = window.setInterval(step, 100)
}

const finish = () => {
  if (progressInterval) {
    clearInterval(progressInterval)
    progressInterval = null
  }

  progress.value = 100

  setTimeout(() => {
    isLoading.value = false
    progress.value = 0
  }, props.duration)
}

const fail = () => {
  if (progressInterval) {
    clearInterval(progressInterval)
    progressInterval = null
  }

  isLoading.value = false
  progress.value = 0
}

// Cleanup
onUnmounted(() => {
  if (progressInterval) {
    clearInterval(progressInterval)
  }
})

// Expose methods to parent
defineExpose({
  start,
  finish,
  fail
})
</script>

<style scoped>
.loading-bar-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  z-index: 9999;
  pointer-events: none;
}

.loading-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color) 0%, var(--primary-lighter) 100%);
  box-shadow: 0 0 10px var(--primary-color);
  transition: width 0.2s ease-out;
}

.loading-bar-fade-enter-active,
.loading-bar-fade-leave-active {
  transition: opacity 0.3s ease;
}

.loading-bar-fade-enter-from,
.loading-bar-fade-leave-to {
  opacity: 0;
}
</style>
