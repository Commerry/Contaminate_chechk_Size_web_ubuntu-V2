<template>
  <div class="lot-manager-section">
    <!-- Create/Edit Form (อยู่บนสุด) -->
    <div class="form-section">
      <h3>{{ editingLot ? 'แก้ไข' : 'เพิ่ม' }} LOT</h3>
      
      <div class="form-group">
        <label>รหัส LOT <span class="required">*</span></label>
        <input 
          v-model="formData.id" 
          type="text" 
          class="form-input"
          placeholder="เช่น LOT-001, BATCH-A-001"
          :disabled="!!editingLot"
        />
      </div>

      <div class="form-group">
        <label>ชื่อ LOT <span class="required">*</span></label>
        <input 
          v-model="formData.name" 
          type="text" 
          class="form-input"
          placeholder="เช่น Batch A-2024-03"
        />
      </div>

      <div class="form-group">
        <label>ประเภท (Type) <span class="required">*</span></label>
        <input 
          v-model="formData.type" 
          type="text" 
          class="form-input"
          placeholder="เช่น Rubber Type A, Plastic Type B"
        />
      </div>

      <div class="form-group">
        <label>รายละเอียด</label>
        <textarea 
          v-model="formData.description" 
          class="form-textarea"
          rows="3"
          placeholder="รายละเอียด LOT..."
        ></textarea>
      </div>

      <div class="form-group">
        <label>สถานะ</label>
        <select v-model="formData.status" class="form-select">
          <option value="active">ใช้งาน (Active)</option>
          <option value="inactive">ไม่ใช้งาน (Inactive)</option>
          <option value="completed">เสร็จสิ้น (Completed)</option>
        </select>
      </div>

      <div class="form-actions">
        <button class="btn btn-secondary" @click="cancelForm">
          ยกเลิก
        </button>
        <button 
          class="btn btn-primary" 
          @click="saveLot"
          :disabled="!formData.id || !formData.name || !formData.type"
        >
          <IconSvg name="check" :size="16" />
          {{ editingLot ? 'บันทึก' : 'เพิ่ม LOT' }}
        </button>
      </div>
    </div>

    <!-- LOT List (อยู่ล่าง) -->
    <div class="list-section">
      <div class="section-header">
        <h3>รายการ LOT</h3>
      </div>

      <div class="item-list">
        <div 
          v-for="lot in lots" 
          :key="lot.id"
          class="item-card"
        >
          <div class="item-info">
            <div class="item-name">{{ lot.name }}</div>
            <div class="item-details">
              <span class="badge badge-info">{{ lot.id }}</span>
              <span class="badge badge-warning">{{ lot.type }}</span>
              <span 
                class="status-badge" 
                :class="statusClass(lot.status)"
              >
                {{ statusText(lot.status) }}
              </span>
            </div>
            <div v-if="lot.description" class="item-description">
              {{ lot.description }}
            </div>
            <div v-if="lot.created_date" class="item-meta">
              สร้างเมื่อ: {{ formatDate(lot.created_date) }}
            </div>
          </div>
          <div class="item-actions">
            <button class="btn-icon" @click="editLot(lot)">
              <IconSvg name="edit" :size="16" />
            </button>
            <button class="btn-icon danger" @click="deleteLot(lot.id)">
              <IconSvg name="trash" :size="16" />
            </button>
          </div>
        </div>

        <div v-if="lots.length === 0" class="empty-state">
          <IconSvg name="folder" :size="48" style="opacity: 0.3; margin-bottom: 16px;" />
          <p>ยังไม่มี LOT</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import IconSvg from './IconSvg.vue'
import axios from 'axios'

const emit = defineEmits(['updated'])

const lots = ref([])
const editingLot = ref(null)
const formData = ref({
  id: '',
  name: '',
  type: '',
  description: '',
  status: 'active'
})

// 🌐 Dynamic server URL
const API_BASE = window.location.origin

const loadLots = async () => {
  try {
    const response = await axios.get(`${API_BASE}/api/lots`)
    if (response.data.success) {
      lots.value = response.data.lots
    }
  } catch (error) {
    console.error('Failed to load LOTs:', error)
  }
}

const saveLot = async () => {
  try {
    if (editingLot.value) {
      // Update existing LOT
      await axios.put(`${API_BASE}/api/lots/${formData.value.id}`, formData.value)
    } else {
      // Add new LOT
      await axios.post(`${API_BASE}/api/lots`, formData.value)
    }
    
    await loadLots()
    cancelForm()
    emit('updated')
  } catch (error) {
    console.error('Failed to save LOT:', error)
    alert(`เกิดข้อผิดพลาด: ${error.response?.data?.message || error.message}`)
  }
}

const editLot = (lot) => {
  editingLot.value = lot
  formData.value = { ...lot }
}

const deleteLot = async (lotId) => {
  if (!confirm('ต้องการลบ LOT นี้ใช่หรือไม่?')) return
  
  try {
    await axios.delete(`${API_BASE}/api/lots/${lotId}`)
    await loadLots()
    emit('updated')
  } catch (error) {
    console.error('Failed to delete LOT:', error)
    alert(`เกิดข้อผิดพลาด: ${error.response?.data?.message || error.message}`)
  }
}

const cancelForm = () => {
  editingLot.value = null
  formData.value = {
    id: '',
    name: '',
    type: '',
    description: '',
    status: 'active'
  }
}

const statusClass = (status) => {
  const classes = {
    'active': 'status-active',
    'inactive': 'status-inactive',
    'completed': 'status-completed'
  }
  return classes[status] || ''
}

const statusText = (status) => {
  const texts = {
    'active': 'ใช้งาน',
    'inactive': 'ไม่ใช้งาน',
    'completed': 'เสร็จสิ้น'
  }
  return texts[status] || status
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('th-TH', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  loadLots()
})
</script>

<style scoped>
.lot-manager-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-section,
.list-section {
  background: var(--bg-dark-secondary);
  border-radius: 12px;
  padding: 24px;
  border: 1px solid var(--border-color);
}

.form-section h3,
.list-section h3 {
  margin: 0 0 20px 0;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 600;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
}

.required {
  color: #dc2626;
}

.form-input,
.form-textarea,
.form-select {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  transition: all 0.2s;
}

.form-input:focus,
.form-textarea:focus,
.form-select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(var(--primary-rgb), 0.1);
}

.form-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--bg-dark-secondary);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-color);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-dark-secondary);
  color: var(--text-secondary);
}

.btn-secondary:hover {
  background: var(--bg-card-hover);
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.item-card {
  background: var(--bg-dark-secondary);
  border: 2px solid transparent;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  transition: all 0.2s;
}

.item-card:hover {
  background: var(--bg-card-hover);
  border-color: var(--primary-color);
}

.item-info {
  flex: 1;
}

.item-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.item-details {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.badge {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.badge-info {
  background: #dbeafe;
  color: var(--primary-dark);
}

.badge-warning {
  background: #fef3c7;
  color: #b45309;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-active {
  background: #d1fae5;
  color: var(--primary-dark);
}

.status-inactive {
  background: #f3f4f6;
  color: #6b7280;
}

.status-completed {
  background: #dbeafe;
  color: var(--primary-dark);
}

.item-description {
  color: var(--text-secondary);
  font-size: 13px;
  margin-top: 4px;
  line-height: 1.5;
}

.item-meta {
  color: var(--text-tertiary);
  font-size: 12px;
  margin-top: 8px;
}

.item-actions {
  display: flex;
  gap: 8px;
}

.btn-icon {
  padding: 8px;
  background: var(--bg-dark-secondary);
  border: none;
  border-radius: 8px;
  width: 32px;
  height: 32px;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: #dbeafe;
  color: var(--primary-dark);
}

.btn-icon.danger:hover {
  background: #fee2e2;
  color: #dc2626;
}

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-tertiary);
}

.empty-state p {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary);
}
</style>
