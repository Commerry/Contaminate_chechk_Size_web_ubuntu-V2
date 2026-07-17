"""
System Configuration Manager
Manages persistent settings for camera, UI state, and calibration
"""

import json
import os
from pathlib import Path
from datetime import datetime


class SystemConfig:
    """Manages system configuration with auto-save"""
    
    DEFAULT_CONFIG = {
        # Camera State
        "camera_active": 0,  # 0 = off, 1 = on
        "prediction_active": 0,  # 0 = off, 1 = on
        
        # Camera Settings
        "zoom_level": 1.0,  # 1.0 = no zoom, 2.0 = 2x zoom
        "preview_width": 1920,
        "preview_height": 1080,
        "fps": 30,
        "network_camera_ip": "",  # Network/PoE camera IP (empty = auto-detect CSI/USB only)
        "oak_ip_config_on_startup": True,  # Flash OAK PoE static IP at startup when network_camera_ip is set
        "oak_static_ip_mask": "255.255.255.0",
        "oak_static_ip_gateway": "",
        "oak_ip_config_settle_seconds": 5,
        
        # Auto Controls
        "auto_focus": 1,  # 0 = off, 1 = on
        "auto_exposure": 1,
        "auto_white_balance": 1,
        
        # Image Enhancement
        "height_on": 1,  # 0 = off, 1 = on
        "contrast_mode": 0,  # 0 = off, 1 = on
        "depth_color_scheme": "gray",  # gray, turbo, jet, viridis, plasma
        
        # Ground Distance
        "ground_distance_mm": 500,  # Distance from camera to ground
        
        # Calibration Settings
        "calibration_file": "",  # Path to calibration file
        "focal_length_px": 1075.0,  # RGB camera focal length
        
        # Detection Settings
        "confidence_threshold": 0.3,  # AI model confidence threshold
        "min_area": 0,  # Minimum object area in pixels (0 = allow very small objects)
        
        # Model Selection
        "active_model": "",  # Name of active model
        "detector_type": "",  # simple, yolo, or ""
        # Camera worker startup control
        "auto_start_camera_worker": True,  # If True, backend will attempt to auto-start camera_worker subprocess
        
        # Last Updated
        "last_updated": "",
        "version": "1.0"
    }
    
    def __init__(self, config_file="config.json"):
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = Path(__file__).resolve().parent / config_path
        self.config_file = config_path
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults (in case new keys added)
                    self.config.update(loaded_config)
                print(f"[Config] Loaded from {self.config_file}")
                return True
            except Exception as e:
                print(f"[Config] Error loading: {e}")
                return False
        else:
            print(f"[Config] No config file found, using defaults")
            self.save()  # Create default config
            return False
    
    def save(self):
        """Save configuration to file"""
        try:
            self.config["last_updated"] = datetime.now().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"[Config] Saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"[Config] Error saving: {e}")
            return False
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value, auto_save=True):
        """Set configuration value and optionally auto-save"""
        self.config[key] = value
        if auto_save:
            self.save()
    
    def update(self, updates, auto_save=True):
        """Update multiple values at once"""
        self.config.update(updates)
        if auto_save:
            self.save()
    
    def get_all(self):
        """Get all configuration"""
        return self.config.copy()
    
    def reset(self):
        """Reset to default configuration"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save()
        print("[Config] Reset to defaults")


# Global instance
system_config = SystemConfig()
