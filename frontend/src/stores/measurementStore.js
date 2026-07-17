import { defineStore } from 'pinia'
import measurementService from '../services/measurementService'

export const useMeasurementStore = defineStore('measurement', {
  state: () => ({
    isConnected: false,
    isCameraActive: false,
    currentFrame: null,
    currentMeasurements: {
      width: 0,
      height: 0,
      depth: 0,
      volume: 0,
      hasObject: false
    },
    detections: [],
    settings: {
      resolution: '1080p',
      fpsLimit: 30,
      showDepthMap: false,
      measurementUnit: 'mm',
      minDepth: 300,
      maxDepth: 3000,
      autoCapture: true,
      confidenceThreshold: 0.5,
      minObjectSize: 50,
      showBoundingBoxes: true,
      referenceSize: 100
    },
    statistics: {
      totalMeasurements: 0,
      avgWidth: 0,
      avgHeight: 0,
      avgDepth: 0
    },
    measurementHistory: [],
    error: null
  }),

  getters: {
    hasActiveObject: (state) => state.currentMeasurements.hasObject,
    
    formattedMeasurements: (state) => {
      const unit = state.settings.measurementUnit
      return {
        width: `${state.currentMeasurements.width.toFixed(1)} ${unit}`,
        height: `${state.currentMeasurements.height.toFixed(1)} ${unit}`,
        depth: `${state.currentMeasurements.depth.toFixed(1)} ${unit}`,
        volume: `${state.currentMeasurements.volume.toFixed(1)} ${unit}³`
      }
    }
  },

  actions: {
    async connectCamera() {
      try {
        const response = await measurementService.connectCamera()
        
        if (response.success) {
          this.isConnected = true
          this.isCameraActive = true
          this.error = null
        } else {
          this.isConnected = false
          this.isCameraActive = false
          this.error = response.message
        }
        
        return response
      } catch (error) {
        this.error = error.message
        this.isConnected = false
        this.isCameraActive = false
        return {
          success: false,
          message: error.message || 'Failed to connect camera'
        }
      }
    },

    async disconnectCamera() {
      try {
        const response = await measurementService.disconnectCamera()
        this.isConnected = false
        this.isCameraActive = false
        this.error = null
        return response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async getMeasurementData(options = {}) {
      try {
        const data = await measurementService.getCurrentData(options)
        
        // Update current measurements
        if (data.measurements) {
          this.currentMeasurements = {
            width: data.measurements.width || 0,
            height: data.measurements.height || 0,
            depth: data.measurements.depth || 0,
            volume: data.measurements.volume || 0,
            hasObject: data.measurements.hasObject || false
          }
          
          // Update statistics if object detected
          if (data.measurements.hasObject) {
            this.updateStatistics(data.measurements)
          }
        }
        
        // Update frame
        if (data.frame) {
          this.currentFrame = data.frame
        }
        
        // Update detections
        if (data.detections) {
          this.detections = data.detections
        }
        
        this.error = null
        return data
      } catch (error) {
        // Don't throw error, just log and return empty data
        if (error.response?.status !== 400) {
          console.warn('getMeasurementData error:', error.message)
        }
        this.error = error.message
        
        // Return empty data structure
        return {
          frame: this.currentFrame || { image: null, timestamp: new Date().toISOString() },
          measurements: this.currentMeasurements,
          detections: this.detections || []
        }
      }
    },

    async updateSettings(newSettings) {
      try {
        const response = await measurementService.updateSettings(newSettings)
        this.settings = { ...this.settings, ...newSettings }
        this.error = null
        return response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async loadSettings() {
      try {
        const settings = await measurementService.getSettings()
        this.settings = { ...this.settings, ...settings }
        this.error = null
        return settings
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async captureSnapshot() {
      try {
        const response = await measurementService.captureSnapshot()
        
        // Add to history
        if (response.measurement) {
          this.measurementHistory.push({
            timestamp: new Date().toISOString(),
            ...response.measurement
          })
        }
        
        this.error = null
        return response
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async resetMeasurements() {
      try {
        await measurementService.resetMeasurements()
        
        this.currentMeasurements = {
          width: 0,
          height: 0,
          depth: 0,
          volume: 0,
          hasObject: false
        }
        
        this.statistics = {
          totalMeasurements: 0,
          avgWidth: 0,
          avgHeight: 0,
          avgDepth: 0
        }
        
        this.measurementHistory = []
        this.error = null
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    updateStatistics(measurement) {
      const history = this.measurementHistory
      const total = history.length + 1
      
      this.statistics = {
        totalMeasurements: total,
        avgWidth: (this.statistics.avgWidth * (total - 1) + measurement.width) / total,
        avgHeight: (this.statistics.avgHeight * (total - 1) + measurement.height) / total,
        avgDepth: (this.statistics.avgDepth * (total - 1) + measurement.depth) / total
      }
    },

    clearError() {
      this.error = null
    }
  }
})
