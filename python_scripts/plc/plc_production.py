"""
PLC Production Module for PSE Vision CM4
Uses Snap7 to communicate with Siemens PLC
"""
import snap7.client
from snap7 import util
from threading import Timer, Thread
from queue import Queue, Empty
import time
import traceback
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PLCClient:
    """Siemens PLC Client using Snap7"""
    
    def __init__(self, plc_address, db_num):
        self.db_num = int(db_num)
        self.plc_address = plc_address
        self.client_for_read = snap7.client.Client()
        self.client_for_write = snap7.client.Client()
        self.is_read_connected = False
        self.is_write_connected = False
        self.status_callback = None
        
    def set_status_callback(self, callback):
        """Set callback function for PLC status updates"""
        self.status_callback = callback
        
    def _notify_status(self, status, message):
        """Notify status change"""
        if self.status_callback:
            self.status_callback(status, message)
        
    def connect(self):
        """Establish connection to PLC"""
        # Check current connection state
        try:
            read_cpu = self.client_for_read.get_cpu_state()
            write_cpu = self.client_for_write.get_cpu_state()
            
            if self.is_read_connected and read_cpu != "S7CpuStatusRun":
                self.is_read_connected = False
                self.client_for_read.disconnect()

            if self.is_write_connected and write_cpu != "S7CpuStatusRun":
                self.is_write_connected = False
                self.client_for_write.disconnect()
        except:
            pass

        if not self.is_read_connected or not self.is_write_connected:
            self._notify_status('connecting', 'Connecting to PLC...')
            
        # Connect read client
        while not self.is_read_connected:
            logger.info(f"Connecting to PLC for read at {self.plc_address}...")
            try:
                self.client_for_read.connect(self.plc_address, 0, 1)
                logger.info(f"✓ Connected to PLC for read")
                self.is_read_connected = True
                break
            except Exception as e:
                logger.error(f"Failed to connect to PLC for read: {e}")
                self._notify_status('error', f'Connection failed: {e}')
                time.sleep(1)
            
        # Connect write client
        while not self.is_write_connected:
            logger.info(f"Connecting to PLC for write at {self.plc_address}...")
            try:
                self.client_for_write.connect(self.plc_address, 0, 1)
                logger.info(f"✓ Connected to PLC for write")
                self.is_write_connected = True
                break
            except Exception as e:
                logger.error(f"Failed to connect to PLC for write: {e}")
                self._notify_status('error', f'Connection failed: {e}')
                time.sleep(1)

        if self.is_read_connected and self.is_write_connected:
            self._notify_status('connected', 'PLC Connected')
            logger.info("✓✓ PLC fully connected (read + write)")

    def reconnect_for_read(self):
        """Reconnect read client"""
        self.is_read_connected = False
        try:
            self.client_for_read.disconnect()
        except:
            pass
        time.sleep(0.1)
        self.connect()

    def reconnect_for_write(self):
        """Reconnect write client"""
        self.is_write_connected = False
        try:
            self.client_for_write.disconnect()
        except:
            pass
        time.sleep(0.1)
        self.connect()

    def is_ready_for_trigger(self):
        """Check if PLC is ready to trigger camera capture"""
        return self.read_bool(0, 0)
    
    def read_int(self, offset, size):
        """Read INT value from PLC DB"""
        try:
            self.connect()
            db = self.client_for_read.db_read(self.db_num, offset, size)
            current_buff = util.get_int(db, 0)
            return current_buff
        except Exception as e:
            logger.error(f"Failed to read_int at {offset}: {e}")
            self.reconnect_for_read()
            return None
    
    def write_int(self, offset, size, value):
        """Write INT value to PLC DB"""
        try:
            self.connect()
            logger.info(f"Writing int {value} to offset {offset}")
            db = self.client_for_write.db_read(self.db_num, offset, size)
            updated_buff = util.set_int(db, 0, value)
            self.client_for_write.db_write(self.db_num, offset, updated_buff)
        except Exception as e:
            logger.error(f"Failed to write_int at {offset}: {e}")
            self.reconnect_for_write()

    def read_real(self, offset):
        """Read REAL (float) value from PLC DB"""
        try:
            self.connect()
            db = self.client_for_read.db_read(self.db_num, offset, 4)
            current_buff = util.get_real(db, 0)
            return current_buff
        except Exception as e:
            logger.error(f"Failed to read_real at {offset}: {e}")
            self.reconnect_for_read()
            return None

    def write_real(self, offset, value):
        """Write REAL (float) value to PLC DB"""
        try:
            self.connect()
            logger.info(f"Writing real {value} to offset {offset}")
            db = self.client_for_write.db_read(self.db_num, offset, 4)
            updated_buff = util.set_real(db, 0, value)
            self.client_for_write.db_write(self.db_num, offset, updated_buff)
        except Exception as e:
            logger.error(f"Failed to write_real at {offset}: {e}")
            self.reconnect_for_write()

    def read_bool(self, offset, index):
        """Read BOOL value from PLC DB"""
        try:
            self.connect()
            db = self.client_for_read.db_read(self.db_num, offset, index + 1)
            current_buff = util.get_bool(db, 0, index)
            return current_buff
        except Exception as e:
            logger.error(f"Failed to read_bool at {offset},{index}: {e}")
            self.reconnect_for_read()
            return False

    def write_bool(self, offset, index, value):
        """Write BOOL value to PLC DB"""
        try:
            self.connect()
            logger.info(f"Writing bool {value} to offset {offset},{index}")
            db = self.client_for_write.db_read(self.db_num, offset, index + 1)
            updated_buff = util.set_bool(db, 0, index, value)
            self.client_for_write.db_write(self.db_num, offset, updated_buff)
        except Exception as e:
            logger.error(f"Failed to write_bool at {offset},{index}: {e}")
            self.reconnect_for_write()

    def write_measurement_result(self, area, width, height, status):
        """
        Write measurement result to PLC
        
        PLC DB Layout:
        - Offset 0.0 (BOOL): Trigger from PLC (input)
        - Offset 2 (INT): Area in mm² (output)
        - Offset 4 (REAL): Width in mm (output)
        - Offset 8 (REAL): Height in mm (output)
        - Offset 12.0 (BOOL): Pass status (output)
        - Offset 12.1 (BOOL): Fail status (output)
        """
        try:
            # Write area (INT)
            area_int = int(area)
            self.write_int(2, 2, area_int)
            
            # Write width (REAL)
            self.write_real(4, float(width))
            
            # Write height (REAL)
            self.write_real(8, float(height))
            
            # Write status (BOOL)
            if status == 'pass':
                self.write_bool(12, 0, True)   # Pass
                self.write_bool(12, 1, False)  # Not Fail
            elif status == 'fail':
                self.write_bool(12, 0, False)  # Not Pass
                self.write_bool(12, 1, True)   # Fail
            else:
                self.write_bool(12, 0, False)
                self.write_bool(12, 1, False)
                
            logger.info(f"✓ Sent to PLC: Area={area_int}mm², W={width}mm, H={height}mm, Status={status}")
            
        except Exception as e:
            logger.error(f"Failed to write measurement result: {e}")

    def write_camera_status(self, is_connected):
        """Write camera connection status to PLC"""
        try:
            # Offset 16.0 (BOOL): Camera connected
            self.write_bool(16, 0, is_connected)
        except Exception as e:
            logger.error(f"Failed to write camera status: {e}")


def plc_loop(plc_address, plc_db_num, queue_list, status_callback=None):
    """
    PLC Loop Thread - monitors PLC trigger and sends results
    
    Args:
        plc_address: PLC IP address
        plc_db_num: PLC DB number
        queue_list: Dictionary with queues:
            - 'trigger': Queue for trigger signals (output from this thread)
            - 'result': Queue for measurement results (input to this thread)
            - 'camera_status': Queue for camera status updates
        status_callback: Optional callback for PLC status updates
    """
    trigger_queue: Queue = queue_list["trigger"]
    result_queue: Queue = queue_list["result"]
    camera_status_queue: Queue = queue_list["camera_status"]

    client = PLCClient(plc_address, plc_db_num)
    if status_callback:
        client.set_status_callback(status_callback)

    logger.info(f"PLC Loop started: {plc_address}, DB{plc_db_num}")

    while True:
        try:
            time.sleep(0.1)  # 100ms cycle
            
            # 1. Check for trigger from PLC
            is_ready = client.is_ready_for_trigger()
            
            if is_ready:
                # Send trigger signal to main thread
                if not trigger_queue.full():
                    trigger_queue.put_nowait(True)
                    logger.info("▶ PLC Trigger received!")

            # 2. Check for measurement results to write back to PLC
            try:
                if not result_queue.empty():
                    result_data = result_queue.get_nowait()
                    if result_data:
                        # result_data = {'area': 123, 'width': 10.5, 'height': 11.7, 'status': 'pass'}
                        client.write_measurement_result(
                            area=result_data.get('area', 0),
                            width=result_data.get('width', 0),
                            height=result_data.get('height', 0),
                            status=result_data.get('status', 'unknown')
                        )
            except Empty:
                pass
            except Exception as e:
                logger.error(f"Error writing result to PLC: {e}")

            # 3. Check for camera status updates
            try:
                if not camera_status_queue.empty():
                    camera_connected = camera_status_queue.get_nowait()
                    client.write_camera_status(camera_connected)
            except Empty:
                pass
            except Exception as e:
                logger.error(f"Error writing camera status: {e}")

        except Exception as e:
            logger.error(f"Error in PLC loop: {e}")
            traceback.print_exc()
            time.sleep(1)
