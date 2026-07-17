<template>
  <div class="unified-management-overlay" @click.self="$emit('close')">
    <div class="unified-management-panel">
      <div class="panel-header">
        <h2 class="panel-title">
          <IconSvg name="settings" :size="24" />
          System Management
          <span class="subtitle">จัดการระบบ</span>
        </h2>
        <button class="close-btn" @click="$emit('close')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <!-- Tabs Navigation -->
      <div class="tabs-nav">
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'plc' }"
          @click="activeTab = 'plc'"
        >
          <IconSvg name="cpu" :size="18" />
          PLC
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'machines' }"
          @click="activeTab = 'machines'"
        >
          <IconSvg name="settings" :size="18" />
          Machines
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'configurations' }"
          @click="activeTab = 'configurations'"
        >
          <IconSvg name="sliders" :size="18" />
          Configurations
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'lots' }"
          @click="activeTab = 'lots'"
        >
          <IconSvg name="package" :size="18" />
          LOTs
        </button>
      </div>

      <!-- Tab Content -->
      <div class="panel-content">
        <!-- PLC Tab -->
        <div v-if="activeTab === 'plc'" class="tab-content">
          <PLCSettings @updated="handleUpdated" />
        </div>

        <!-- Machines Tab -->
        <div v-if="activeTab === 'machines'" class="tab-content">
          <MachineManager @updated="handleUpdated" />
        </div>

        <!-- Configurations Tab -->
        <div v-if="activeTab === 'configurations'" class="tab-content">
          <ConfigurationManager @updated="handleUpdated" />
        </div>

        <!-- LOTs Tab -->
        <div v-if="activeTab === 'lots'" class="tab-content">
          <LOTManager @updated="handleUpdated" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import IconSvg from './IconSvg.vue'
import PLCSettings from './PLCSettings.vue'
import MachineManager from './MachineManager.vue'
import ConfigurationManager from './ConfigurationManager.vue'
import LOTManager from './LOTManager.vue'

const emit = defineEmits(['close', 'updated'])

const activeTab = ref('plc') // Default to PLC tab

const handleUpdated = () => {
  emit('updated')
}
</script>

<style scoped>
.unified-management-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100001;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.unified-management-panel {
  background: var(--panel-bg, linear-gradient(135deg, #1e293b 0%, #0f172a 100%));
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  width: 90%;
  max-width: 1200px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.3s ease-out;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.panel-header {
  padding: 24px 32px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.02);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  color: var(--text-primary, #f1f5f9);
  font-size: 24px;
  font-weight: 600;
}

.subtitle {
  font-size: 14px;
  font-weight: 400;
  color: var(--text-secondary, #94a3b8);
  margin-left: 4px;
}

.close-btn {
  padding: 8px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: var(--text-secondary, #94a3b8);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 9999 !important;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.tabs-nav {
  display: flex;
  gap: 4px;
  padding: 16px 32px 0;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.tab-btn {
  padding: 12px 24px;
  background: transparent;
  border: none;
  border-radius: 8px 8px 0 0;
  color: var(--text-secondary, #94a3b8);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary, #f1f5f9);
}

.tab-btn.active {
  background: var(--card-bg, #1e293b);
  color: var(--primary-color, var(--primary-color));
  border-bottom: 2px solid var(--primary-color, var(--primary-color));
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

.tab-content {
  animation: fadeIn 0.3s ease-out;
}

/* Scrollbar styling */
.panel-content::-webkit-scrollbar {
  width: 8px;
}

.panel-content::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.panel-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.panel-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

@media (max-width: 768px) {
  .unified-management-panel {
    width: 95%;
    max-height: 95vh;
  }

  .panel-header {
    padding: 16px 20px;
  }

  .panel-title {
    font-size: 20px;
  }

  .tabs-nav {
    padding: 12px 20px 0;
    overflow-x: auto;
  }

  .tab-btn {
    padding: 10px 16px;
    font-size: 13px;
    white-space: nowrap;
  }

  .panel-content {
    padding: 16px 20px;
  }
}
</style>
