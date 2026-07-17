"""
Database Configuration Management
Manages SQLite database connection settings
"""

import json
import os
from pathlib import Path

class DatabaseConfig:
    """Manages database configuration"""
    
    DEFAULT_CONFIG = {
        "enabled": True,  # SQLite always enabled by default
        "db_type": "sqlite",  # sqlite or sqlserver
        "sqlite_path": "data/pse_vision.db",
        "table": "tbl_measurements",
        "sqlserver": {
            "host": "",
            "username": "",
            "password": "",
            "database": "",
            "port": 1433
        },
        "measurement_triggers": 10  # Number of measurements per session
    }
    
    def __init__(self, config_file='database/db_config.json'):
        """Initialize database configuration"""
        self.config_dir = Path(__file__).parent.parent.parent / 'config'
        self.config_file = self.config_dir / config_file
        self.config = self.load()
    
    def load(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return {**self.DEFAULT_CONFIG, **json.load(f)}
            else:
                return self.DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"Error loading database config: {e}")
            return self.DEFAULT_CONFIG.copy()
    
    def save(self, config=None):
        """Save configuration to file"""
        try:
            # Create config directory if not exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            if config:
                self.config = {**self.DEFAULT_CONFIG, **config}
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving database config: {e}")
            return False
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def update(self, **kwargs):
        """Update configuration"""
        self.config.update(kwargs)
        return self.save()
    
    def test_connection(self):
        """Test database connection"""
        if not self.config.get('enabled', False):
            return False, "Database is disabled"
        
        try:
            from .db_service import DatabaseService
            db = DatabaseService(self)
            return db.test_connection()
        except Exception as e:
            return False, str(e)
    
    def get_connection_string(self):
        """Get database connection string"""
        if not self.config.get('enabled', False):
            return None
        
        db_type = self.config.get('db_type', 'sqlite')
        
        if db_type == 'sqlite':
            # Return SQLite database path
            return self.config.get('sqlite_path', 'data/pse_vision.db')
        elif db_type == 'sqlserver':
            # SQL Server connection string (for backward compatibility)
            sqlserver = self.config.get('sqlserver', {})
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={sqlserver.get('host', '')},{sqlserver.get('port', 1433)};"
                f"DATABASE={sqlserver.get('database', '')};"
                f"UID={sqlserver.get('username', '')};"
                f"PWD={sqlserver.get('password', '')}"
            )
            return conn_str
        
        return None
