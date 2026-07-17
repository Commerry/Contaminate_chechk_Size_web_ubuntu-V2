"""
Measurement Session Manager
Handles multi-measurement sessions and finds maximum value
"""

from datetime import datetime
import uuid

class MeasurementSession:
    """Manages measurement sessions with multiple triggers"""
    
    def __init__(self, max_triggers=10):
        """
        Initialize measurement session
        
        Args:
            max_triggers (int): Number of measurements per session
        """
        self.session_id = str(uuid.uuid4())[:8]
        self.max_triggers = max_triggers
        self.measurements = []
        self.start_time = None
        self.object_name = None
        self.is_active = False
    
    def start(self, object_name):
        """
        Start new measurement session
        
        Args:
            object_name (str): Expected object name
        """
        self.session_id = str(uuid.uuid4())[:8]
        self.measurements = []
        self.start_time = datetime.now()
        self.object_name = object_name
        self.is_active = True
        return self.session_id
    
    def add_measurement(self, object_name, size):
        """
        Add measurement to current session
        
        Args:
            object_name (str): Detected object name
            size (float): Measured size in mm
        
        Returns:
            dict: Status with keys:
                - success (bool)
                - message (str)
                - is_complete (bool)
                - current_count (int)
        """
        if not self.is_active:
            return {
                'success': False,
                'message': 'No active session',
                'is_complete': False,
                'current_count': 0
            }
        
        # Check if object name matches
        if object_name != self.object_name:
            return {
                'success': False,
                'message': f'Object name mismatch. Expected: {self.object_name}, Got: {object_name}',
                'is_complete': False,
                'current_count': len(self.measurements)
            }
        
        # Add measurement
        self.measurements.append({
            'object_name': object_name,
            'size': size,
            'timestamp': datetime.now()
        })
        
        current_count = len(self.measurements)
        is_complete = current_count >= self.max_triggers
        
        return {
            'success': True,
            'message': f'Measurement {current_count}/{self.max_triggers} recorded',
            'is_complete': is_complete,
            'current_count': current_count
        }
    
    def get_max_measurement(self):
        """
        Get measurement with maximum size
        
        Returns:
            dict: Maximum measurement data or None
        """
        if not self.measurements:
            return None
        
        max_measurement = max(self.measurements, key=lambda x: x['size'])
        return {
            'session_id': self.session_id,
            'obj': max_measurement['object_name'],
            'size': max_measurement['size'],
            'measurement_count': len(self.measurements),
            'timestamp': max_measurement['timestamp']
        }
    
    def complete(self):
        """
        Complete the session and return max measurement
        
        Returns:
            dict: Maximum measurement or None if session invalid
        """
        self.is_active = False
        
        if len(self.measurements) < self.max_triggers:
            return None
        
        return self.get_max_measurement()
    
    def cancel(self):
        """Cancel current session"""
        self.is_active = False
        self.measurements = []
        return True
    
    def get_status(self):
        """Get current session status"""
        return {
            'session_id': self.session_id,
            'is_active': self.is_active,
            'object_name': self.object_name,
            'current_count': len(self.measurements),
            'max_triggers': self.max_triggers,
            'progress': len(self.measurements) / self.max_triggers if self.max_triggers > 0 else 0,
            'measurements': [
                {'size': m['size'], 'timestamp': m['timestamp'].isoformat()}
                for m in self.measurements
            ]
        }
