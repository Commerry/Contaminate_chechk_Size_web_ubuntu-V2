"""
Database Service
Handles SQLite and SQL Server connections and data insertion
"""

from datetime import datetime
import sqlite3
import os
from pathlib import Path

class DatabaseService:
    """Database service supporting SQLite and SQL Server"""
    
    def __init__(self, config):
        """Initialize database service"""
        self.config = config
        self.connection = None
        self.db_type = config.get('db_type', 'sqlite')
    
    def connect(self):
        """Connect to database"""
        try:
            if self.db_type == 'sqlite':
                return self._connect_sqlite()
            elif self.db_type == 'sqlserver':
                return self._connect_sqlserver()
            else:
                return False, f"Unknown database type: {self.db_type}"
        except Exception as e:
            self.connection = None
            return False, f"Connection failed: {str(e)}"
    
    def _connect_sqlite(self):
        """Connect to SQLite database"""
        try:
            db_path = self.config.get('sqlite_path', 'data/pse_vision.db')
            
            # Create data directory if not exists
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Connect to SQLite
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            
            # Create tables if not exist
            self._create_tables_sqlite()
            
            return True, "Connected successfully"
        except Exception as e:
            return False, f"SQLite connection failed: {str(e)}"
    
    def _connect_sqlserver(self):
        """Connect to SQL Server"""
        try:
            import pyodbc
            conn_str = self.config.get_connection_string()
            if not conn_str:
                return False, "SQL Server connection string not configured"
            
            self.connection = pyodbc.connect(conn_str, timeout=5)
            return True, "Connected successfully"
        except ImportError:
            return False, "pyodbc not installed. Install with: pip install pyodbc"
        except Exception as e:
            return False, f"SQL Server connection failed: {str(e)}"
    
    def _create_tables_sqlite(self):
        """Create necessary tables in SQLite"""
        cursor = self.connection.cursor()
        
        # Measurements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datetime TEXT NOT NULL,
                lot TEXT,
                product_type TEXT,
                obj TEXT,
                size REAL,
                status TEXT DEFAULT 'PASS',
                machine_id TEXT,
                configuration_id INTEGER,
                image_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Sessions table (for tracking measurement sessions)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tbl_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                machine_id TEXT,
                configuration_id INTEGER,
                lot TEXT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                total_measurements INTEGER DEFAULT 0,
                pass_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.connection.commit()
    
    def disconnect(self):
        """Disconnect from database"""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
        except:
            pass
    
    def test_connection(self):
        """Test database connection"""
        try:
            success, message = self.connect()
            if success:
                # Try a simple query
                cursor = self.connection.cursor()
                if self.db_type == 'sqlite':
                    cursor.execute("SELECT 1")
                else:
                    cursor.execute("SELECT 1")
                cursor.close()
                self.disconnect()
                return True, "Connection test successful"
            return False, message
        except Exception as e:
            self.disconnect()
            return False, f"Connection test failed: {str(e)}"
    
    def insert_measurement(self, data):
        """
        Insert measurement data into database
        
        Args:
            data (dict): Measurement data with keys:
                - lot: str
                - product_type: str
                - obj: str (object name)
                - size: float (mm)
                - status: str (PASS/FAIL)
                - machine_id: str
                - configuration_id: int
                - image_path: str
        
        Returns:
            tuple: (success, message)
        """
        try:
            # Connect if not connected
            if not self.connection:
                success, message = self.connect()
                if not success:
                    return False, message
            
            # Prepare data
            table_name = self.config.get('table', 'tbl_measurements')
            current_time = datetime.now()
            
            if self.db_type == 'sqlite':
                # SQLite insert
                query = f"""
                    INSERT INTO {table_name} 
                    (datetime, lot, product_type, obj, size, status, machine_id, configuration_id, image_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                values = (
                    current_time.isoformat(),
                    data.get('lot', ''),
                    data.get('product_type', ''),
                    data.get('obj', ''),
                    data.get('size', 0.0),
                    data.get('status', 'PASS'),
                    data.get('machine_id', ''),
                    data.get('configuration_id', None),
                    data.get('image_path', '')
                )
                
                cursor = self.connection.cursor()
                cursor.execute(query, values)
                self.connection.commit()
                row_id = cursor.lastrowid
                cursor.close()
                
                return True, f"Data saved successfully (ID: {row_id})"
            
            else:
                # SQL Server insert
                query = f"""
                    INSERT INTO {table_name} (datetime, lot, product_type, obj, size)
                    VALUES (?, ?, ?, ?, ?)
                """
                
                values = (
                    current_time,
                    data.get('lot', ''),
                    data.get('product_type', ''),
                    data.get('obj', ''),
                    data.get('size', 0.0)
                )
                
                cursor = self.connection.cursor()
                cursor.execute(query, values)
                self.connection.commit()
                cursor.close()
                
                return True, f"Data saved successfully (ID: {current_time.strftime('%Y%m%d_%H%M%S')})"
        
        except Exception as e:
            try:
                if self.connection:
                    self.connection.rollback()
            except:
                pass
            return False, f"Failed to save data: {str(e)}"
    
    def get_machines(self):
        """
        Get all machines from database
        
        Returns:
            tuple: (success, data/message)
                data is a list of dicts with keys: id, name, description, status, location
        """
        try:
            # Connect if not connected
            if not self.connection:
                success, message = self.connect()
                if not success:
                    return False, message
            
            # Query machines table
            query = """
                SELECT id, name, description, status, location, created_at
                FROM tbl_machines
                ORDER BY name
            """
            
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            # Fetch all rows
            machines = []
            for row in cursor.fetchall():
                machines.append({
                    'id': row.id,
                    'name': row.name,
                    'description': row.description or '',
                    'status': row.status or 'active',
                    'location': row.location or '',
                    'created_at': row.created_at.strftime('%Y-%m-%d %H:%M:%S') if row.created_at else None
                })
            
            cursor.close()
            return True, machines
        
        except Exception as e:
            return False, f"Failed to get machines: {str(e)}"
    
    def add_machine(self, machine_data):
        """
        Add a new machine to database
        
        Args:
            machine_data (dict): Machine data with keys:
                - id: str (machine ID, e.g., 'MC-01')
                - name: str
                - description: str (optional)
                - status: str (optional, default 'active')
                - location: str (optional)
        
        Returns:
            tuple: (success, message)
        """
        try:
            # Connect if not connected
            if not self.connection:
                success, message = self.connect()
                if not success:
                    return False, message
            
            # Prepare data
            current_time = datetime.now()
            
            query = """
                INSERT INTO tbl_machines (id, name, description, status, location, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            
            values = (
                machine_data.get('id', ''),
                machine_data.get('name', ''),
                machine_data.get('description', ''),
                machine_data.get('status', 'active'),
                machine_data.get('location', ''),
                current_time
            )
            
            cursor = self.connection.cursor()
            cursor.execute(query, values)
            self.connection.commit()
            cursor.close()
            
            return True, f"Machine '{machine_data.get('name')}' added successfully"
        
        except Exception as e:
            try:
                if self.connection:
                    self.connection.rollback()
            except:
                pass
            return False, f"Failed to add machine: {str(e)}"
    
    def update_machine(self, machine_id, machine_data):
        """
        Update machine information
        
        Args:
            machine_id (str): Machine ID
            machine_data (dict): Updated data (name, description, status, location)
        
        Returns:
            tuple: (success, message)
        """
        try:
            # Connect if not connected
            if not self.connection:
                success, message = self.connect()
                if not success:
                    return False, message
            
            # Build update query dynamically
            fields = []
            values = []
            
            if 'name' in machine_data:
                fields.append('name = ?')
                values.append(machine_data['name'])
            
            if 'description' in machine_data:
                fields.append('description = ?')
                values.append(machine_data['description'])
            
            if 'status' in machine_data:
                fields.append('status = ?')
                values.append(machine_data['status'])
            
            if 'location' in machine_data:
                fields.append('location = ?')
                values.append(machine_data['location'])
            
            if not fields:
                return False, "No fields to update"
            
            fields.append('updated_at = ?')
            values.append(datetime.now())
            values.append(machine_id)
            
            query = f"""
                UPDATE tbl_machines
                SET {', '.join(fields)}
                WHERE id = ?
            """
            
            cursor = self.connection.cursor()
            cursor.execute(query, values)
            self.connection.commit()
            
            if cursor.rowcount == 0:
                cursor.close()
                return False, f"Machine '{machine_id}' not found"
            
            cursor.close()
            return True, f"Machine '{machine_id}' updated successfully"
        
        except Exception as e:
            try:
                if self.connection:
                    self.connection.rollback()
            except:
                pass
            return False, f"Failed to update machine: {str(e)}"
    
    def delete_machine(self, machine_id):
        """
        Delete a machine from database
        
        Args:
            machine_id (str): Machine ID
        
        Returns:
            tuple: (success, message)
        """
        try:
            # Connect if not connected
            if not self.connection:
                success, message = self.connect()
                if not success:
                    return False, message
            
            query = "DELETE FROM tbl_machines WHERE id = ?"
            
            cursor = self.connection.cursor()
            cursor.execute(query, (machine_id,))
            self.connection.commit()
            
            if cursor.rowcount == 0:
                cursor.close()
                return False, f"Machine '{machine_id}' not found"
            
            cursor.close()
            return True, f"Machine '{machine_id}' deleted successfully"
        
        except Exception as e:
            try:
                if self.connection:
                    self.connection.rollback()
            except:
                pass
            return False, f"Failed to delete machine: {str(e)}"
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
