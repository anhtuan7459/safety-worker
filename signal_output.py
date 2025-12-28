"""
Signal Output Module
- Gửi tín hiệu ra console
- Điều khiển đèn qua Modbus RS485 (ESP32/ESP8266)
- Đọc cấu hình từ config/modbus_config.json
"""

import os
import json
import time
from datetime import datetime

# Path
script_dir = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(script_dir, "config", "modbus_config.json")

# Global Modbus client & state
modbus_client = None
modbus_config = None

# Lưu trạng thái vùng hiện tại của từng label
# key = label_lower ("songoku"/"dog"), value = "INSIDE" hoặc "OUTSIDE"
last_region_state = {}


def load_modbus_config():
    """Đọc cấu hình Modbus từ file JSON"""
    global modbus_config
    
    if not os.path.exists(CONFIG_PATH):
        print(f"[MODBUS] ⚠ Không tìm thấy config: {CONFIG_PATH}")
        modbus_config = {
            "enabled": False,
            "port": "COM7",
            "baudrate": 9600,
            "slave_esp32": 1,
            "slave_esp8266": 2
        }
        return modbus_config
    
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            modbus_config = json.load(f)
        print(f"[MODBUS] Đã đọc config: {CONFIG_PATH}")
        return modbus_config
    except Exception as e:
        print(f"[MODBUS] ❌ Lỗi đọc config: {e}")
        modbus_config = {"enabled": False}
        return modbus_config


def save_modbus_config(config):
    """Lưu cấu hình Modbus vào file JSON"""
    global modbus_config
    modbus_config = config
    
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print(f"[MODBUS] ✅ Đã lưu config: {CONFIG_PATH}")
        return True
    except Exception as e:
        print(f"[MODBUS] ❌ Lỗi lưu config: {e}")
        return False


def init_modbus():
    """Khởi tạo kết nối Modbus RS485 từ config"""
    global modbus_client, modbus_config
    
    print("[MODBUS] === Bắt đầu init_modbus() ===")
    
    # Đọc config
    if modbus_config is None:
        load_modbus_config()
    
    print(f"[MODBUS] Config: enabled={modbus_config.get('enabled')}, port={modbus_config.get('port')}")
    
    if not modbus_config.get("enabled", False):
        print("[MODBUS] ⚠ Modbus chưa được bật trong config")
        print("         → Vào GUI > Tab Modbus > Kết nối để bật")
        return False
    
    port = modbus_config.get("port", "COM7")
    baudrate = modbus_config.get("baudrate", 9600)
    
    try:
        from pymodbus.client.sync import ModbusSerialClient
        print(f"[MODBUS] Đang kết nối tới {port}...")
        
        client = ModbusSerialClient(
            method='rtu',
            port=port,
            baudrate=baudrate,
            parity='N',
            stopbits=1,
            bytesize=8,
            timeout=1
        )
        
        if client.connect():
            modbus_client = client  # Gán vào biến global SAU khi connect thành công
            slave1 = modbus_config.get("slave_esp32", 1)
            slave2 = modbus_config.get("slave_esp8266", 2)
            print(f"[MODBUS] ✅ Đã kết nối RS485 tại {port} @ {baudrate}")
            print(f"         - Slave {slave1} (ESP32): songoku")
            print(f"         - Slave {slave2} (ESP8266): dog")
            print(f"[MODBUS] modbus_client = {modbus_client}")
            return True
        else:
            print(f"[MODBUS] ❌ Không thể kết nối tới {port} (connect() returned False)")
            modbus_client = None
            return False
            
    except ImportError:
        print("[MODBUS] ❌ Thiếu thư viện pymodbus! Chạy: pip install pymodbus==2.5.3")
        return False
    except Exception as e:
        print(f"[MODBUS] ❌ Lỗi kết nối: {e}")
        modbus_client = None
        return False


def close_modbus():
    """Đóng kết nối Modbus"""
    global modbus_client
    if modbus_client:
        turn_off_all_lights()
        modbus_client.close()
        print("[MODBUS] Đã ngắt kết nối RS485")


def set_light(slave_id, state):
    """
    Bật/tắt đèn cho slave cụ thể
    
    Args:
        slave_id: 1 (ESP32) hoặc 2 (ESP8266)
        state: True (bật) hoặc False (tắt)
    """
    if not modbus_client:
        return False
    
    try:
        modbus_client.write_coil(0, bool(state), unit=slave_id)
        status = "🔆 BẬT" if state else "⚫ TẮT"
        device = "ESP32" if slave_id == 1 else "ESP8266"
        print(f"[MODBUS] {status} đèn {device} (Slave {slave_id})")
        return True
    except Exception as e:
        print(f"[MODBUS] Lỗi điều khiển Slave {slave_id}: {e}")
        return False


def turn_on_light_for_label(label):
    """Bật đèn tương ứng với label (songoku/dog)"""
    if modbus_config is None:
        load_modbus_config()
    
    label_lower = label.lower()
    if label_lower == "songoku":
        slave_id = modbus_config.get("slave_esp32", 1)
    elif label_lower == "dog":
        slave_id = modbus_config.get("slave_esp8266", 2)
    else:
        return False
    
    return set_light(slave_id, True)


def turn_off_light_for_label(label):
    """Tắt đèn tương ứng với label"""
    if modbus_config is None:
        load_modbus_config()
    
    label_lower = label.lower()
    if label_lower == "songoku":
        slave_id = modbus_config.get("slave_esp32", 1)
    elif label_lower == "dog":
        slave_id = modbus_config.get("slave_esp8266", 2)
    else:
        return False
    
    return set_light(slave_id, False)


def turn_off_all_lights():
    """Tắt tất cả đèn"""
    if modbus_config is None:
        load_modbus_config()
    
    slave1 = modbus_config.get("slave_esp32", 1)
    slave2 = modbus_config.get("slave_esp8266", 2)
    set_light(slave1, False)
    set_light(slave2, False)


# ============ SIGNAL FUNCTIONS ============

def send_signal(signal_type, **kwargs):
    """
    Gửi tín hiệu ra console và điều khiển đèn
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if signal_type == "DETECT_INSIDE":
        label = kwargs.get('label', 'unknown')
        label_lower = label.lower()
        x = kwargs.get('x', 0)
        y = kwargs.get('y', 0)
        cam = kwargs.get('camera_id', 0)
        person_id = kwargs.get('person_id', 0)
        
        console_msg = f"🟢 [TRONG VÙNG] {label} | Cam{cam} | BIM({x:.1f}, {y:.1f}) | ID={person_id}"
        print(f"[{timestamp}] {console_msg}")
        
        # Vật VÀO vùng BIM
        # Chỉ gửi tín hiệu TẮT đèn nếu trước đó đang Ở NGOÀI vùng
        prev_state = last_region_state.get(label_lower)
        last_region_state[label_lower] = "INSIDE"
        if modbus_client and prev_state == "OUTSIDE":
            print(f"         >>> MODBUS: {label} từ NGOÀI → TRONG, TẮT đèn")
            turn_off_light_for_label(label)
        
    elif signal_type == "DETECT_OUTSIDE":
        label = kwargs.get('label', 'unknown')
        label_lower = label.lower()
        x = kwargs.get('x', 0)
        y = kwargs.get('y', 0)
        cam = kwargs.get('camera_id', 0)
        direction = kwargs.get('direction', 'UNKNOWN')
        
        console_msg = f"🔴 [NGOÀI VÙNG - {direction}] {label} | Cam{cam} | BIM({x:.1f}, {y:.1f})"
        print(f"[{timestamp}] {console_msg}")
        
        # Vật RA NGOÀI vùng BIM
        # Chỉ gửi tín hiệu BẬT đèn nếu trước đó đang Ở TRONG vùng (hoặc chưa có trạng thái)
        prev_state = last_region_state.get(label_lower)
        last_region_state[label_lower] = "OUTSIDE"
        if modbus_client and prev_state != "OUTSIDE":
            print(f"         >>> MODBUS: {label} từ TRONG → NGOÀI ({direction}), BẬT đèn")
            turn_on_light_for_label(label)
        
    elif signal_type == "CALIBRATION_DONE":
        cam = kwargs.get('camera_id', 0)
        console_msg = f"✅ [CALIBRATION DONE] Camera {cam} đã calibrate xong!"
        print(f"[{timestamp}] {console_msg}")
        
    elif signal_type == "SYSTEM_READY":
        console_msg = "🚀 [SYSTEM READY] Hệ thống đã sẵn sàng!"
        print(f"[{timestamp}] {console_msg}")
        
        # Nhấp nháy đèn để test kết nối
        if modbus_client and modbus_config:
            print("[MODBUS] Test đèn...")
            slave1 = modbus_config.get("slave_esp32", 1)
            slave2 = modbus_config.get("slave_esp8266", 2)
            set_light(slave1, True)
            set_light(slave2, True)
            time.sleep(0.5)
            turn_off_all_lights()
        
    elif signal_type == "SYSTEM_STOP":
        console_msg = "⏹️ [SYSTEM STOP] Hệ thống đã dừng!"
        print(f"[{timestamp}] {console_msg}")
        
        # Tắt tất cả đèn khi dừng
        if modbus_client:
            turn_off_all_lights()
        
    elif signal_type == "DB_SAVED":
        count = kwargs.get('count', 0)
        console_msg = f"💾 [DB SAVED] Đã lưu {count} tọa độ vào database"
        print(f"[{timestamp}] {console_msg}")
        
    else:
        console_msg = f"❓ [UNKNOWN] {signal_type}"
        print(f"[{timestamp}] {console_msg}")


# ============ SHORTCUT FUNCTIONS ============

def signal_inside(label, x, y, camera_id, person_id=0):
    """Tín hiệu khi vật vào trong vùng BIM → TẮT đèn"""
    return send_signal("DETECT_INSIDE", label=label, x=x, y=y, 
                       camera_id=camera_id, person_id=person_id)

def signal_outside(label, x, y, camera_id, direction="UNKNOWN"):
    """Tín hiệu khi vật ở ngoài vùng BIM → BẬT đèn"""
    return send_signal("DETECT_OUTSIDE", label=label, x=x, y=y, 
                       camera_id=camera_id, direction=direction)


def get_outside_direction(x, y, bim_bounds):
    """
    Tính hướng của vật khi nằm ngoài vùng BIM
    bim_bounds = (x_min, x_max, y_min, y_max)
    """
    x_min, x_max, y_min, y_max = bim_bounds
    directions = []
    
    if x < x_min:
        directions.append("TRAI")
    elif x > x_max:
        directions.append("PHAI")
    
    if y < y_min:
        directions.append("DUOI")
    elif y > y_max:
        directions.append("TREN")
    
    if not directions:
        return "TRONG"
    
    return "_".join(directions)


def signal_calibration_done(camera_id):
    """Tín hiệu khi calibration xong"""
    return send_signal("CALIBRATION_DONE", camera_id=camera_id)

def signal_ready():
    """Tín hiệu hệ thống sẵn sàng"""
    return send_signal("SYSTEM_READY")

def signal_stop():
    """Tín hiệu hệ thống dừng"""
    return send_signal("SYSTEM_STOP")

def signal_db_saved(count):
    """Tín hiệu đã lưu database"""
    return send_signal("DB_SAVED", count=count)


# ============ TEST ============
if __name__ == "__main__":
    print("=" * 60)
    print("    TEST SIGNAL OUTPUT + MODBUS RS485")
    print("=" * 60)
    
    # Đọc và hiển thị config
    config = load_modbus_config()
    print(f"Config: {json.dumps(config, indent=2)}")
    print()
    
    # Khởi tạo Modbus
    init_modbus()
    print()
    
    # Test system ready
    signal_ready()
    time.sleep(1)
    
    # Test detection
    bim_bounds = (32, 70, -5, 27)
    
    print("\n--- Test: Vật NGOÀI vùng ---")
    signal_outside("songoku", 80.0, 10.0, camera_id=2, 
                   direction=get_outside_direction(80.0, 10.0, bim_bounds))
    time.sleep(2)
    
    signal_outside("dog", 25.0, 35.0, camera_id=1, 
                   direction=get_outside_direction(25.0, 35.0, bim_bounds))
    time.sleep(2)
    
    print("\n--- Test: Vật VÀO vùng ---")
    signal_inside("songoku", 50.0, 10.0, camera_id=2, person_id=0)
    signal_inside("dog", 45.0, 15.0, camera_id=1, person_id=1)
    
    print()
    signal_stop()
    close_modbus()
