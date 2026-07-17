<template>
  <Transition name="toast">
    <div v-if="visible" class="toast-notification" :class="type">
      <div class="toast-icon">
        <IconSvg v-if="type === 'success'" name="check" :size="20" />
        <IconSvg v-else-if="type === 'error'" name="close" :size="20" />
        <IconSvg v-else-if="type === 'warning'" name="warning" :size="20" />
        <IconSvg v-else name="info" :size="20" />
      </div>
      <div class="toast-content">
        <p class="toast-message">{{ message }}</p>
      </div>
      <button class="toast-close" @click="close">
        <IconSvg name="close" :size="16" />
      </button>
    </div>
  </Transition>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import IconSvg from './IconSvg.vue'

const props = defineProps({
  message: {
    type: String,
    required: true
  },
  type: {
    type: String,
    default: 'info', // success, error, warning, info
    validator: (value) => ['success', 'error', 'warning', 'info'].includes(value)
  },
  duration: {
    type: Number,
    default: 3000
  }
})

const emit = defineEmits(['close'])

const visible = ref(true)

const close = () => {
  visible.value = false
  setTimeout(() => {
    emit('close')
  }, 300)
}

onMounted(() => {
  if (props.duration > 0) {
    setTimeout(close, props.duration)
  }
})
</script>

<style scoped>
.toast-notification {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: var(--bg-card);
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border-color);
  min-width: 300px;
  max-width: 500px;
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
}

.toast-notification::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--primary-color);
}

.toast-notification.success::before {
  background: var(--success-color);
}

.toast-notification.error::before {
  background: var(--danger-color);
}

.toast-notification.warning::before {
  background: var(--warning-color);
}

.toast-notification.info::before {
  background: var(--info-color);
}

.toast-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(var(--primary-rgb), 0.1);
  color: var(--primary-color);
}

.toast-notification.success .toast-icon {
  background: rgba(var(--primary-rgb), 0.1);
  color: var(--success-color);
}

.toast-notification.error .toast-icon {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger-color);
}

.toast-notification.warning .toast-icon {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
}

.toast-notification.info .toast-icon {
  background: rgba(var(--primary-rgb), 0.1);
  color: var(--info-color);
}

.toast-content {
  flex: 1;
}

.toast-message {
  margin: 0;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
}

.toast-close {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.toast-close:hover {
  background: var(--bg-card-hover);
  color: var(--text-primary);
}

/* Transitions */
.toast-enter-active {
  animation: slideInRight 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-leave-active {
  animation: slideOutRight 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slideOutRight {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(100%);
    opacity: 0;
  }
}

/* Responsive */
@media (max-width: 768px) {
  .toast-notification {
    min-width: 280px;
    max-width: calc(100vw - 32px);
    padding: 12px 16px;
  }
  
  .toast-message {
    font-size: 13px;
  }
}
</style>
