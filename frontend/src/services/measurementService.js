import axios from 'axios'

const API_BASE_URL = `${window.location.origin}/api`

class MeasurementService {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000, // 30 seconds for camera initialization
      headers: {
        'Content-Type': 'application/json'
      }
    })
  }

  // Connect to camera
  async connectCamera() {
    try {
      const response = await this.client.post('/camera/connect')
      return response.data
    } catch (error) {
      console.error('Failed to connect camera:', error)
      if (error.code === 'ERR_NETWORK' || error.code === 'ECONNREFUSED') {
        return {
          success: false,
          message: `Cannot connect to backend server. Please ensure the backend is running on ${window.location.origin}`
        }
      }
      return {
        success: false,
        message: error.response?.data?.message || error.message || 'Failed to connect camera'
      }
    }
  }

  // Disconnect camera
  async disconnectCamera() {
    try {
      const response = await this.client.post('/camera/disconnect')
      return response.data
    } catch (error) {
      console.error('Failed to disconnect camera:', error)
      throw error
    }
  }

  // Get camera status
  async getCameraStatus() {
    try {
      const response = await this.client.get('/camera/status')
      return response.data
    } catch (error) {
      console.error('Failed to get camera status:', error)
      return {
        camera_active: false,
        prediction_active: false,
        has_model: false,
        detector_type: 'none',
        hasDevice: false
      }
    }
  }

  // Get current frame and measurements with optional image enhancements
  async getCurrentData(options = {}) {
    try {
      // Build query parameters for image enhancements
      const params = new URLSearchParams()
      if (options.contrast !== undefined) {
        params.append('contrast', options.contrast ? 'true' : 'false')
      }
      if (options.colorScheme) {
        params.append('colorScheme', options.colorScheme)
      }
      
      const url = `/measurement/current${params.toString() ? '?' + params.toString() : ''}`
      const response = await this.client.get(url)
      const data = response.data
      
      // Validate and sanitize image data
      if (data.frame && data.frame.image) {
        // Check if image is valid base64
        if (!data.frame.image.startsWith('data:image/')) {
          console.warn('Invalid image format received')
          data.frame.image = null
        }
      }
      
      return data
    } catch (error) {
      // Only log actual errors, not 400 status
      if (error.response?.status !== 400) {
        console.error('Failed to get current data:', error)
      }
      
      // Return empty data instead of throwing
      return {
        frame: { image: null, timestamp: new Date().toISOString() },
        measurements: { width: 0, height: 0, depth: 0, volume: 0, hasObject: false },
        allMeasurements: [],
        detections: []
      }
    }
  }

  // Update settings
  async updateSettings(settings) {
    try {
      const response = await this.client.post('/settings/update', settings)
      return response.data
    } catch (error) {
      console.error('Failed to update settings:', error)
      throw error
    }
  }

  // Get settings
  async getSettings() {
    try {
      const response = await this.client.get('/settings')
      return response.data
    } catch (error) {
      console.error('Failed to get settings:', error)
      throw error
    }
  }

  // Start calibration
  async startCalibration(referenceSize) {
    try {
      const response = await this.client.post('/calibration/start', { referenceSize })
      return response.data
    } catch (error) {
      console.error('Failed to start calibration:', error)
      throw error
    }
  }

  // Capture snapshot
  async captureSnapshot() {
    try {
      const response = await this.client.post('/measurement/snapshot')
      return response.data
    } catch (error) {
      console.error('Failed to capture snapshot:', error)
      throw error
    }
  }

  // Export measurements
  async exportMeasurements() {
    try {
      const response = await this.client.get('/measurement/export', {
        responseType: 'blob'
      })
      return response.data
    } catch (error) {
      console.error('Failed to export measurements:', error)
      throw error
    }
  }

  // Get camera status
  async getCameraStatus() {
    try {
      const response = await this.client.get('/camera/status')
      return response.data
    } catch (error) {
      console.error('Failed to get camera status:', error)
      throw error
    }
  }

  // Reset measurements
  async resetMeasurements() {
    try {
      const response = await this.client.post('/measurement/reset')
      return response.data
    } catch (error) {
      console.error('Failed to reset measurements:', error)
      throw error
    }
  }

  // Start prediction
  async startPrediction() {
    try {
      const response = await this.client.post('/camera/prediction/start')
      return response.data
    } catch (error) {
      console.error('Failed to start prediction:', error)
      throw error
    }
  }

  // Stop prediction
  async stopPrediction() {
    try {
      const response = await this.client.post('/camera/prediction/stop')
      return response.data
    } catch (error) {
      console.error('Failed to stop prediction:', error)
      throw error
    }
  }
}

export default new MeasurementService()
