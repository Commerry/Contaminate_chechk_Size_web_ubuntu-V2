// Toast Notification Composable
// ใช้สำหรับแสดง popup notification มุมขวาล่าง

import { ref } from 'vue'

const toasts = ref([])
let toastId = 0

export function useToast() {
  const showToast = (message, type = 'info', duration = 3000) => {
    const id = ++toastId
    const toast = {
      id,
      message,
      type,
      duration
    }
    
    toasts.value.push(toast)
    
    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration + 500) // Add 500ms for animation
    }
    
    return id
  }
  
  const removeToast = (id) => {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }
  
  // Convenience methods
  const success = (message, duration = 3000) => showToast(message, 'success', duration)
  const error = (message, duration = 5000) => showToast(message, 'error', duration)
  const warning = (message, duration = 4000) => showToast(message, 'warning', duration)
  const info = (message, duration = 3000) => showToast(message, 'info', duration)
  
  return {
    toasts,
    showToast,
    removeToast,
    success,
    error,
    warning,
    info
  }
}
