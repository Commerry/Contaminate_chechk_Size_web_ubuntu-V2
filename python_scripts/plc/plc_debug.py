"""
PLC Debug Module for PSE Vision CM4
Simulates PLC behavior for development/testing without real PLC hardware
"""
from threading import Thread
from queue import Queue, Empty
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PLCClientDebug:
    """Simulated PLC Client for debugging"""
    
    def __init__(self, plc_address, db_num):
        self.db_num = int(db_num)
        self.plc_address = plc_address
        self.trigger_counter = 0
        self.status_callback = None
        logger.info(f"[DEBUG MODE] Simulated PLC initialized: {plc_address}, DB{db_num}")
        
    def set_status_callback(self, callback):
        """Set callback function for PLC status updates"""
        self.status_callback = callback
        if callback:
            callback('connected', 'PLC Debug Mode - Always Connected')
        
    def is_ready_for_trigger(self):
        """Simulate PLC trigger every 10 seconds"""
        self.trigger_counter += 1
        
        # Trigger every 100 cycles (10 seconds at 100ms interval)
        is_ready = (self.trigger_counter % 100 == 0)
        
        if is_ready:
            logger.info("[DEBUG] Simulated PLC trigger activated")
            
        return is_ready
    
    def read_int(self, offset, size):
        """Simulate reading INT from PLC"""
        logger.debug(f"[DEBUG] read_int at offset {offset}")
        return 123
    
    def write_int(self, offset, size, value):
        """Simulate writing INT to PLC"""
        logger.info(f"[DEBUG] write_int: {value} to offset {offset}")

    def read_real(self, offset):
        """Simulate reading REAL from PLC"""
        logger.debug(f"[DEBUG] read_real at offset {offset}")
        return 12.34

    def write_real(self, offset, value):
        """Simulate writing REAL to PLC"""
        logger.info(f"[DEBUG] write_real: {value} to offset {offset}")

    def read_bool(self, offset, index):
        """Simulate reading BOOL from PLC"""
        # Trigger every 10 seconds
        is_trigger = (self.trigger_counter % 100 == 0)
        logger.debug(f"[DEBUG] read_bool at {offset},{index} = {is_trigger}")
        return is_trigger

    def write_bool(self, offset, index, value):
        """Simulate writing BOOL to PLC"""
        logger.info(f"[DEBUG] write_bool: {value} to offset {offset},{index}")

    def write_measurement_result(self, area, width, height, status):
        """
        Simulate writing measurement result to PLC
        """
        logger.info(f"[DEBUG] ✓ Sent to PLC: Area={int(area)}mm², W={width}mm, H={height}mm, Status={status}")

    def write_camera_status(self, is_connected):
        """Simulate writing camera status to PLC"""
        status_text = "Connected" if is_connected else "Disconnected"
        logger.info(f"[DEBUG] Camera status sent to PLC: {status_text}")


def plc_loop_debug(plc_address, plc_db_num, queue_list, status_callback=None):
    """
    Debug PLC Loop - simulates PLC behavior for testing
    
    Args:
        plc_address: PLC IP address (ignored in debug mode)
        plc_db_num: PLC DB number (ignored in debug mode)
        queue_list: Dictionary with queues:
            - 'trigger': Queue for trigger signals (output from this thread)
            - 'result': Queue for measurement results (input to this thread)
            - 'camera_status': Queue for camera status updates
        status_callback: Optional callback for PLC status updates
    """
    trigger_queue: Queue = queue_list["trigger"]
    result_queue: Queue = queue_list["result"]
    camera_status_queue: Queue = queue_list["camera_status"]

    client = PLCClientDebug(plc_address, plc_db_num)
    if status_callback:
        client.set_status_callback(status_callback)

    logger.info(f"[DEBUG] PLC Loop started in DEBUG MODE")
    logger.info(f"[DEBUG] Will simulate trigger every 10 seconds")

    while True:
        try:
            time.sleep(0.1)  # 100ms cycle
            
            # 1. Simulate PLC trigger check
            is_ready = client.is_ready_for_trigger()
            
            if is_ready:
                # Send trigger signal to main thread
                if not trigger_queue.full():
                    trigger_queue.put_nowait(True)
                    logger.info("[DEBUG] ▶ Simulated PLC Trigger sent!")

            # 2. Process measurement results from queue
            try:
                if not result_queue.empty():
                    result_data = result_queue.get_nowait()
                    if result_data:
                        client.write_measurement_result(
                            area=result_data.get('area', 0),
                            width=result_data.get('width', 0),
                            height=result_data.get('height', 0),
                            status=result_data.get('status', 'unknown')
                        )
            except Empty:
                pass
            except Exception as e:
                logger.error(f"[DEBUG] Error processing result: {e}")

            # 3. Process camera status updates
            try:
                if not camera_status_queue.empty():
                    camera_connected = camera_status_queue.get_nowait()
                    client.write_camera_status(camera_connected)
            except Empty:
                pass
            except Exception as e:
                logger.error(f"[DEBUG] Error processing camera status: {e}")

        except Exception as e:
            logger.error(f"[DEBUG] Error in PLC loop: {e}")
            time.sleep(1)
