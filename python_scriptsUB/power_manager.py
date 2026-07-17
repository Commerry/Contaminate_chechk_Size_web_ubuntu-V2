#!/usr/bin/env python3
"""
Power Management Module for PSE Vision System
Supports:
- Wake-on-LAN (WOL) - เปิดเครื่องผ่าน LAN
- Remote Shutdown via SSH
- Remote Reboot via SSH
- Local Shutdown/Reboot
"""

import socket
import struct
import time
import subprocess
import platform
from typing import Tuple, Optional

def send_wake_on_lan(mac_address: str, broadcast_ip: str = '255.255.255.255', port: int = 9) -> Tuple[bool, str]:
    """
    ส่ง Magic Packet เพื่อปลุกเครื่องที่รองรับ Wake-on-LAN
    
    Args:
        mac_address: MAC address ของเครื่องเป้าหมาย (format: AA:BB:CC:DD:EE:FF หรือ AA-BB-CC-DD-EE-FF)
        broadcast_ip: Broadcast IP address (default: 255.255.255.255)
        port: UDP port (default: 9, บางเครื่องใช้ 7)
    
    Returns:
        Tuple[bool, str]: (success, message)
    
    ตัวอย่าง:
        success, msg = send_wake_on_lan('00:11:22:33:44:55', '10.4.255.255')
    """
    try:
        # ลบ : หรือ - ออกจาก MAC address
        mac_address = mac_address.replace(':', '').replace('-', '').upper()
        
        # ตรวจสอบความถูกต้องของ MAC address (ต้องเป็น 12 hex digits)
        if len(mac_address) != 12:
            return False, f"Invalid MAC address format. Got {len(mac_address)} characters, expected 12"
        
        # แปลง hex string เป็น bytes
        try:
            mac_bytes = bytes.fromhex(mac_address)
        except ValueError as e:
            return False, f"Invalid MAC address hex values: {e}"
        
        # สร้าง Magic Packet
        # Magic Packet = 6 bytes ของ 0xFF + (MAC address 16 ครั้ง)
        magic_packet = b'\xFF' * 6 + mac_bytes * 16
        
        # สร้าง UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # ส่ง Magic Packet
        sock.sendto(magic_packet, (broadcast_ip, port))
        sock.close()
        
        return True, f"Magic Packet sent to {mac_address} via {broadcast_ip}:{port}"
        
    except Exception as e:
        return False, f"Failed to send Wake-on-LAN packet: {str(e)}"


def shutdown_local_machine(delay_seconds: int = 60) -> Tuple[bool, str]:
    """
    Shutdown เครื่อง local (เครื่องที่รัน backend นี้)
    
    Args:
        delay_seconds: เวลาหน่วงก่อน shutdown (default: 60 วินาที)
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        system = platform.system()
        
        if system == 'Linux':
            # Linux: ใช้ shutdown command
            cmd = ['sudo', 'shutdown', '-h', f'+{delay_seconds//60}']
            subprocess.Popen(cmd)
            return True, f"Local shutdown scheduled in {delay_seconds} seconds"
            
        elif system == 'Windows':
            # Windows: ใช้ shutdown command
            cmd = ['shutdown', '/s', '/t', str(delay_seconds)]
            subprocess.Popen(cmd)
            return True, f"Local shutdown scheduled in {delay_seconds} seconds"
            
        else:
            return False, f"Unsupported operating system: {system}"
            
    except Exception as e:
        return False, f"Failed to shutdown local machine: {str(e)}"


def reboot_local_machine(delay_seconds: int = 60) -> Tuple[bool, str]:
    """
    Reboot เครื่อง local (เครื่องที่รัน backend นี้)
    
    Args:
        delay_seconds: เวลาหน่วงก่อน reboot (default: 60 วินาที)
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        system = platform.system()
        
        if system == 'Linux':
            # Linux: ใช้ shutdown -r
            cmd = ['sudo', 'shutdown', '-r', f'+{delay_seconds//60}']
            subprocess.Popen(cmd)
            return True, f"Local reboot scheduled in {delay_seconds} seconds"
            
        elif system == 'Windows':
            # Windows: ใช้ shutdown /r
            cmd = ['shutdown', '/r', '/t', str(delay_seconds)]
            subprocess.Popen(cmd)
            return True, f"Local reboot scheduled in {delay_seconds} seconds"
            
        else:
            return False, f"Unsupported operating system: {system}"
            
    except Exception as e:
        return False, f"Failed to reboot local machine: {str(e)}"


def shutdown_remote_machine(host: str, username: str, password: Optional[str] = None, 
                           ssh_key: Optional[str] = None, delay_seconds: int = 60) -> Tuple[bool, str]:
    """
    Shutdown เครื่อง remote ผ่าน SSH
    
    Args:
        host: IP address หรือ hostname ของเครื่อง remote
        username: SSH username
        password: SSH password (optional ถ้าใช้ key)
        ssh_key: Path to SSH private key (optional ถ้าใช้ password)
        delay_seconds: เวลาหน่วงก่อน shutdown
    
    Returns:
        Tuple[bool, str]: (success, message)
    
    ต้องการ paramiko library: pip install paramiko
    """
    try:
        import paramiko
        
        # สร้าง SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # เชื่อมต่อ SSH
        if ssh_key:
            ssh.connect(hostname=host, username=username, key_filename=ssh_key, timeout=10)
        else:
            ssh.connect(hostname=host, username=username, password=password, timeout=10)
        
        # รัน shutdown command
        shutdown_cmd = f'sudo shutdown -h +{delay_seconds//60}'
        stdin, stdout, stderr = ssh.exec_command(shutdown_cmd, get_pty=True)
        
        # ถ้าต้องการ sudo password
        if password:
            stdin.write(password + '\n')
            stdin.flush()
        
        time.sleep(0.5)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        ssh.close()
        
        if 'shutdown' in output.lower() or len(error) == 0:
            return True, f"Remote shutdown scheduled on {host} in {delay_seconds} seconds"
        else:
            return False, f"Shutdown command failed: {error}"
            
    except ImportError:
        return False, "paramiko library not installed. Run: pip install paramiko"
    except Exception as e:
        return False, f"Failed to shutdown remote machine: {str(e)}"


def reboot_remote_machine(host: str, username: str, password: Optional[str] = None, 
                         ssh_key: Optional[str] = None, delay_seconds: int = 60) -> Tuple[bool, str]:
    """
    Reboot เครื่อง remote ผ่าน SSH
    
    Args:
        host: IP address หรือ hostname ของเครื่อง remote
        username: SSH username
        password: SSH password (optional ถ้าใช้ key)
        ssh_key: Path to SSH private key (optional ถ้าใช้ password)
        delay_seconds: เวลาหน่วงก่อน reboot
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        import paramiko
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if ssh_key:
            ssh.connect(hostname=host, username=username, key_filename=ssh_key, timeout=10)
        else:
            ssh.connect(hostname=host, username=username, password=password, timeout=10)
        
        # รัน reboot command
        reboot_cmd = f'sudo shutdown -r +{delay_seconds//60}'
        stdin, stdout, stderr = ssh.exec_command(reboot_cmd, get_pty=True)
        
        if password:
            stdin.write(password + '\n')
            stdin.flush()
        
        time.sleep(0.5)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        ssh.close()
        
        if 'reboot' in output.lower() or 'shutdown' in output.lower() or len(error) == 0:
            return True, f"Remote reboot scheduled on {host} in {delay_seconds} seconds"
        else:
            return False, f"Reboot command failed: {error}"
            
    except ImportError:
        return False, "paramiko library not installed. Run: pip install paramiko"
    except Exception as e:
        return False, f"Failed to reboot remote machine: {str(e)}"


# ========================================================================================
# Test Functions
# ========================================================================================

if __name__ == "__main__":
    print("=== PSE Vision Power Manager - Test Mode ===\n")
    
    # Test 1: Wake-on-LAN
    print("Test 1: Wake-on-LAN")
    mac = "00:11:22:33:44:55"  # แก้เป็น MAC address จริง
    success, msg = send_wake_on_lan(mac, broadcast_ip='255.255.255.255')
    print(f"  Result: {msg}\n")
    
    # Test 2: Local Machine Info
    print("Test 2: Local Machine Info")
    print(f"  OS: {platform.system()}")
    print(f"  Platform: {platform.platform()}\n")
    
    print("⚠️  Skipping actual shutdown/reboot tests for safety")
    print("    To test, call functions manually with appropriate parameters")
