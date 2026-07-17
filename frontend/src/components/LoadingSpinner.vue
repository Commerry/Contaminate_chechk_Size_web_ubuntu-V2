<template>
  <div class="loading-spinner" :class="{ 'small': size === 'small', 'large': size === 'large' }">
    <div class="spinner-ring">
      <div></div>
      <div></div>
      <div></div>
      <div></div>
    </div>
    <p v-if="text" class="loading-text">{{ text }}</p>
  </div>
</template>

<script setup>
defineProps({
  size: {
    type: String,
    default: 'medium', // small, medium, large
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  text: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.spinner-ring {
  display: inline-block;
  position: relative;
  width: 64px;
  height: 64px;
}

.loading-spinner.small .spinner-ring {
  width: 32px;
  height: 32px;
}

.loading-spinner.large .spinner-ring {
  width: 96px;
  height: 96px;
}

.spinner-ring div {
  box-sizing: border-box;
  display: block;
  position: absolute;
  width: 100%;
  height: 100%;
  border: 4px solid var(--primary-color);
  border-radius: 50%;
  animation: spinner-ring 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
  border-color: var(--primary-color) transparent transparent transparent;
}

.spinner-ring div:nth-child(1) {
  animation-delay: -0.45s;
}

.spinner-ring div:nth-child(2) {
  animation-delay: -0.3s;
}

.spinner-ring div:nth-child(3) {
  animation-delay: -0.15s;
}

@keyframes spinner-ring {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.loading-text {
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  margin: 0;
  animation: pulse 2s ease-in-out infinite;
}

.loading-spinner.small .loading-text {
  font-size: 12px;
}

.loading-spinner.large .loading-text {
  font-size: 16px;
}
</style>
