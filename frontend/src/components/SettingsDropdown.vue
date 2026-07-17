<template>
  <div class="settings-dropdown" @mouseenter="showMenu = true" @mouseleave="showMenu = false">
    <button class="settings-trigger" :class="{ 'active': showMenu }">
      <IconSvg name="settings" :size="20" />
      <span class="settings-label">Settings</span>
      <svg class="chevron" :class="{ 'open': showMenu }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6 9 12 15 18 9"></polyline>
      </svg>
    </button>

    <transition name="dropdown">
      <div v-if="showMenu" class="dropdown-menu">
        <button class="menu-item" @click="handleAction('settings')">
          <IconSvg name="settings" :size="18" />
          <span>General Settings</span>
          <span class="badge">Main</span>
        </button>

        <button class="menu-item" @click="handleAction('calibration')">
          <IconSvg name="target" :size="18" />
          <span>Calibration</span>
        </button>

        <button class="menu-item" @click="handleAction('database')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
            <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
          </svg>
          <span>Database Connection</span>
        </button>

        <div class="menu-divider"></div>

        <button class="menu-item" @click="handleAction('machines')">
          <IconSvg name="grid" :size="18" />
          <span>Machines</span>
        </button>

        <button class="menu-item" @click="handleAction('lots')">
          <IconSvg name="package" :size="18" />
          <span>LOT Management</span>
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import IconSvg from './IconSvg.vue'

const showMenu = ref(false)

const emit = defineEmits([
  'open-settings',
  'open-calibration',
  'open-database',
  'open-machines',
  'open-lots'
])

const handleAction = (action) => {
  showMenu.value = false
  
  switch(action) {
    case 'settings':
      emit('open-settings')
      break
    case 'calibration':
      emit('open-calibration')
      break
    case 'database':
      emit('open-database')
      break
    case 'machines':
      emit('open-machines')
      break
    case 'lots':
      emit('open-lots')
      break
  }
}
</script>

<style scoped>
.settings-dropdown {
  position: relative;
  display: inline-block;
}

.settings-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.settings-trigger:hover,
.settings-trigger.active {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.4);
}

.settings-label {
  font-weight: 500;
}

.chevron {
  transition: transform 0.2s ease;
}

.chevron.open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 250px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  padding: 8px;
  z-index: 99999;
  animation: slideDown 0.2s ease;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  text-align: left;
  cursor: pointer;
  transition: all 0.15s ease;
}

.menu-item:hover {
  background: var(--primary-color);
  color: white;
}

.menu-item svg {
  flex-shrink: 0;
  opacity: 0.7;
}

.menu-item:hover svg {
  opacity: 1;
}

.menu-item span:first-of-type {
  flex: 1;
}

.badge {
  padding: 2px 8px;
  background: var(--primary-color);
  color: white;
  font-size: 11px;
  font-weight: 600;
  border-radius: 4px;
  text-transform: uppercase;
}

.menu-item:hover .badge {
  background: rgba(255, 255, 255, 0.25);
}

.menu-divider {
  height: 1px;
  background: var(--border-color);
  margin: 8px 0;
}

/* Animations */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s ease;
}

.dropdown-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Dark mode support */
/* Light theme - force white background */
.settings-dropdown {
  position: relative;
  display: inline-block;
}

/* Remove dark theme overrides */
</style>
