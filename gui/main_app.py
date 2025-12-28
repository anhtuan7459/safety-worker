"""
Dual Camera Detection System - GUI
- Giao diện điều khiển hệ thống
- Chạy các file .bat
- Điều khiển Modbus RS485
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import subprocess
import sys
import os
import json
from datetime import datetime

# Thêm path để import các module
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

# Config path
CONFIG_PATH = os.path.join(parent_dir, "config", "modbus_config.json")

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("[WARN] pyserial chưa cài. Chạy: pip install pyserial")

# Import Modbus
try:
    from pymodbus.client.sync import ModbusSerialClient as ModbusClient
    MODBUS_AVAILABLE = True
except ImportError:
    MODBUS_AVAILABLE = False
    print("[WARN] pymodbus chưa cài. Chạy: pip install pymodbus==2.5.3")


class DualCameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dual Camera Detection System")
        self.root.geometry("520x750")
        self.root.configure(bg='#f5f7fa')
        self.root.resizable(False, False)
        
        # Modbus
        self.modbus_client = None
        self.modbus_connected = False
        
        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()
        
        # Tạo giao diện
        self.create_widgets()
        
        # Log khởi động
        self.log("🚀 Hệ thống đã khởi động")
        self.log("📹 Camera 1: 192.168.66.15 (dog)")
        self.log("📹 Camera 2: 192.168.66.14 (songoku)")
        
        # Load config và refresh COM ports
        self.load_config()
        self.refresh_com_ports()
        
        # Đóng khi thoát
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def configure_styles(self):
        """Cấu hình style"""
        self.style.configure('TFrame', background='#f5f7fa')
        self.style.configure('TLabel', background='#f5f7fa', foreground='#333333', font=('Segoe UI', 10))
        self.style.configure('Header.TLabel', font=('Segoe UI', 14, 'bold'), foreground='#0078d4')
        self.style.configure('TNotebook', background='#f5f7fa')
        self.style.configure('TNotebook.Tab', font=('Segoe UI', 10, 'bold'), padding=[15, 5])
    
    def create_widgets(self):
        """Tạo giao diện"""
        # Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Điều khiển
        self.create_control_tab()
        
        # Tab 2: Modbus RS485
        self.create_modbus_tab()
        
        # Log area
        self.create_log_area()
    
    def create_control_tab(self):
        """Tab điều khiển"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=" 🎮 Điều khiển ")
        
        # Header
        ttk.Label(tab, text="Chọn chế độ chạy:", style='Header.TLabel').pack(pady=20)
        
        # Buttons frame
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=30)
        
        # Full System
        btn = tk.Button(btn_frame, text="🚀 FULL SYSTEM\n(Calibration + Detection)",
                        command=lambda: self.run_bat("start_system.bat"),
                        bg='#007bff', fg='white', font=('Segoe UI', 11, 'bold'),
                        width=35, height=3)
        btn.pack(pady=8)
        
        # Detection
        btn = tk.Button(btn_frame, text="▶ DETECTION\n(Không cần Calibration)",
                        command=lambda: self.run_bat("run_detection.bat"),
                        bg='#28a745', fg='white', font=('Segoe UI', 11, 'bold'),
                        width=35, height=3)
        btn.pack(pady=8)
        
        # Calibration
        btn = tk.Button(btn_frame, text="🎯 CALIBRATION\n(Chỉ Calibrate Camera)",
                        command=lambda: self.run_bat("run_calibration.bat"),
                        bg='#ffc107', fg='black', font=('Segoe UI', 11, 'bold'),
                        width=35, height=3)
        btn.pack(pady=8)
        
        # Record
        btn = tk.Button(btn_frame, text="📹 QUAY VIDEO\n(Để lấy ảnh Label)",
                        command=lambda: self.run_bat("run_record.bat"),
                        bg='#17a2b8', fg='white', font=('Segoe UI', 11, 'bold'),
                        width=35, height=3)
        btn.pack(pady=8)
        
        # Separator
        ttk.Separator(tab, orient='horizontal').pack(fill=tk.X, pady=20, padx=30)
        
        # Quick actions
        ttk.Label(tab, text="Thao tác nhanh:", style='Header.TLabel').pack()
        
        quick_frame = ttk.Frame(tab)
        quick_frame.pack(pady=10)
        
        tk.Button(quick_frame, text="📁 Mở Output", command=self.open_output_folder,
                  bg='#6c757d', fg='white', font=('Segoe UI', 10), width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(quick_frame, text="🗃 Xem Database", command=self.open_database,
                  bg='#6c757d', fg='white', font=('Segoe UI', 10), width=15).pack(side=tk.LEFT, padx=5)
    
    def create_modbus_tab(self):
        """Tab Modbus RS485"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=" 🔌 Modbus RS485 ")
        
        # Connection
        conn_frame = ttk.LabelFrame(tab, text=" Kết nối RS485 ")
        conn_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Port selection
        port_frame = ttk.Frame(conn_frame)
        port_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(port_frame, text="COM:").pack(side=tk.LEFT)
        self.com_port_var = tk.StringVar()
        self.com_port_combo = ttk.Combobox(port_frame, textvariable=self.com_port_var, 
                                            width=12, state='readonly')
        self.com_port_combo.pack(side=tk.LEFT, padx=5)
        
        tk.Button(port_frame, text="🔄", command=self.refresh_com_ports,
                  bg='#6c757d', fg='white', width=3).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(port_frame, text="Baud:").pack(side=tk.LEFT, padx=(15, 0))
        self.baud_var = tk.StringVar(value="9600")
        ttk.Combobox(port_frame, textvariable=self.baud_var, width=10,
                     values=["9600", "115200"], state='readonly').pack(side=tk.LEFT, padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(conn_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.btn_connect = tk.Button(btn_frame, text="🔗 Kết nối", command=self.connect_modbus,
                                      bg='#28a745', fg='white', font=('Segoe UI', 10, 'bold'), width=12)
        self.btn_connect.pack(side=tk.LEFT, padx=5)
        
        self.btn_disconnect = tk.Button(btn_frame, text="❌ Ngắt", command=self.disconnect_modbus,
                                         bg='#dc3545', fg='white', font=('Segoe UI', 10, 'bold'), 
                                         width=12, state=tk.DISABLED)
        self.btn_disconnect.pack(side=tk.LEFT, padx=5)
        
        self.modbus_status = ttk.Label(conn_frame, text="⚫ Chưa kết nối", foreground='#dc3545')
        self.modbus_status.pack(pady=5)
        
        # Note
        note_frame = ttk.Frame(conn_frame)
        note_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(note_frame, text="💡 Kết nối ở đây sẽ lưu config để Detection tự động dùng",
                  foreground='#17a2b8', font=('Segoe UI', 9)).pack()
        
        # Slave Control
        control_frame = ttk.LabelFrame(tab, text=" Điều khiển đèn (Test thủ công) ")
        control_frame.pack(fill=tk.X, padx=15, pady=10)
        
        # Slave 1 (ESP32 - songoku)
        slave1_frame = ttk.Frame(control_frame)
        slave1_frame.pack(fill=tk.X, padx=10, pady=8)
        
        ttk.Label(slave1_frame, text="Slave 1 (ESP32 - songoku):", 
                  font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        
        tk.Button(slave1_frame, text="🔆 BẬT", command=lambda: self.set_light(1, True),
                  bg='#ffc107', fg='black', font=('Segoe UI', 9, 'bold'), width=8).pack(side=tk.RIGHT, padx=3)
        tk.Button(slave1_frame, text="⚫ TẮT", command=lambda: self.set_light(1, False),
                  bg='#343a40', fg='white', font=('Segoe UI', 9, 'bold'), width=8).pack(side=tk.RIGHT, padx=3)
        
        # Slave 2 (ESP8266 - dog)
        slave2_frame = ttk.Frame(control_frame)
        slave2_frame.pack(fill=tk.X, padx=10, pady=8)
        
        ttk.Label(slave2_frame, text="Slave 2 (ESP8266 - dog):", 
                  font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
        
        tk.Button(slave2_frame, text="🔆 BẬT", command=lambda: self.set_light(2, True),
                  bg='#ffc107', fg='black', font=('Segoe UI', 9, 'bold'), width=8).pack(side=tk.RIGHT, padx=3)
        tk.Button(slave2_frame, text="⚫ TẮT", command=lambda: self.set_light(2, False),
                  bg='#343a40', fg='white', font=('Segoe UI', 9, 'bold'), width=8).pack(side=tk.RIGHT, padx=3)
        
        # All
        all_frame = ttk.Frame(control_frame)
        all_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(all_frame, text="💡 BẬT TẤT CẢ", command=self.turn_on_all,
                  bg='#28a745', fg='white', font=('Segoe UI', 10, 'bold'), width=18).pack(side=tk.LEFT, padx=5)
        tk.Button(all_frame, text="🌑 TẮT TẤT CẢ", command=self.turn_off_all,
                  bg='#dc3545', fg='white', font=('Segoe UI', 10, 'bold'), width=18).pack(side=tk.LEFT, padx=5)
        
        # Test
        test_frame = ttk.Frame(control_frame)
        test_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(test_frame, text="🧪 TEST NHẤP NHÁY", command=self.test_blink,
                  bg='#17a2b8', fg='white', font=('Segoe UI', 10, 'bold'), width=38).pack()
        
        # Log Modbus
        log_frame = ttk.LabelFrame(tab, text=" Log Modbus ")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        self.modbus_log = scrolledtext.ScrolledText(log_frame, height=6,
                                                     bg='#fafcff', fg='#0064b4',
                                                     font=('Consolas', 9), state=tk.DISABLED)
        self.modbus_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_log_area(self):
        """Log area"""
        log_frame = ttk.LabelFrame(self.root, text=" 📋 Thông báo ")
        log_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=5,
                                                   bg='#fafcff', fg='#28a745',
                                                   font=('Consolas', 9), state=tk.DISABLED)
        self.log_text.pack(fill=tk.X, padx=5, pady=5)
    
    # ============ CONFIG ============
    
    def load_config(self):
        """Load config từ file"""
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.com_port_var.set(config.get("port", "COM7"))
                self.baud_var.set(str(config.get("baudrate", 9600)))
                self.log(f"📂 Đã load config: {config.get('port')} @ {config.get('baudrate')}")
        except Exception as e:
            self.log(f"⚠ Không đọc được config: {e}")
    
    def save_config(self, enabled=True):
        """Lưu config vào file"""
        config = {
            "enabled": enabled,
            "port": self.com_port_var.get(),
            "baudrate": int(self.baud_var.get()),
            "slave_esp32": 1,
            "slave_esp8266": 2
        }
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            self.log(f"💾 Đã lưu config (enabled={enabled})")
        except Exception as e:
            self.log(f"❌ Lỗi lưu config: {e}")
    
    # ============ FUNCTIONS ============
    
    def run_bat(self, bat_name):
        """Chạy file bat"""
        bat_path = os.path.join(parent_dir, "autorun", bat_name)
        if not os.path.exists(bat_path):
            messagebox.showerror("Lỗi", f"Không tìm thấy: {bat_path}")
            return
        
        # Nếu đang chạy Detection/Full System, ngắt Modbus để Detection tự kết nối
        if bat_name in ["run_detection.bat", "start_system.bat"]:
            if self.modbus_connected:
                self.log("🔌 Ngắt Modbus để Detection tự kết nối...")
                self.disconnect_modbus_silent()
        
        self.log(f"🚀 Đang chạy: {bat_name}")
        try:
            subprocess.Popen(bat_path, shell=True, cwd=parent_dir)
        except Exception as e:
            self.log(f"❌ Lỗi: {e}")
    
    def open_output_folder(self):
        """Mở thư mục output"""
        os.startfile(os.path.join(parent_dir, "output"))
        self.log("📁 Đã mở thư mục Output")
    
    def open_database(self):
        """Mở database"""
        db_path = os.path.join(parent_dir, "output", "data.db")
        if os.path.exists(db_path):
            os.startfile(db_path)
            self.log("🗃 Đã mở Database")
        else:
            messagebox.showwarning("Cảnh báo", "Database chưa tồn tại!")
    
    def refresh_com_ports(self):
        """Refresh COM ports"""
        if not SERIAL_AVAILABLE:
            return
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.com_port_combo['values'] = ports
        if ports:
            # Giữ port đã chọn nếu còn available
            current = self.com_port_var.get()
            if current not in ports:
                self.com_port_combo.set(ports[0])
            self.log(f"🔌 Tìm thấy: {', '.join(ports)}")
        else:
            self.log("⚠ Không tìm thấy cổng COM")
    
    def connect_modbus(self):
        """Kết nối Modbus"""
        if not MODBUS_AVAILABLE:
            messagebox.showerror("Lỗi", "Chưa cài pymodbus!\nChạy: pip install pymodbus==2.5.3")
            return
        
        port = self.com_port_var.get()
        baud = int(self.baud_var.get())
        
        if not port:
            messagebox.showwarning("Cảnh báo", "Chưa chọn COM!")
            return
        
        try:
            self.modbus_client = ModbusClient(
                method='rtu',
                port=port,
                baudrate=baud,
                parity='N',
                stopbits=1,
                bytesize=8,
                timeout=1
            )
            
            if self.modbus_client.connect():
                self.modbus_connected = True
                self.btn_connect.config(state=tk.DISABLED)
                self.btn_disconnect.config(state=tk.NORMAL)
                self.modbus_status.config(text=f"🟢 {port} @ {baud}", foreground='#28a745')
                self.log(f"🔗 Đã kết nối Modbus RS485 tại {port}")
                self.modbus_log_msg(f"[CONNECTED] {port} @ {baud}")
                self.modbus_log_msg("Slave 1: ESP32 (songoku)")
                self.modbus_log_msg("Slave 2: ESP8266 (dog)")
                
                # Lưu config với enabled=True
                self.save_config(enabled=True)
            else:
                messagebox.showerror("Lỗi", f"Không thể kết nối tới {port}")
        except Exception as e:
            self.log(f"❌ Lỗi: {e}")
    
    def disconnect_modbus(self):
        """Ngắt Modbus - GIỮ NGUYÊN enabled=True trong config để Detection vẫn hoạt động"""
        if self.modbus_client:
            self.turn_off_all()  # Tắt đèn trước khi ngắt
            self.modbus_client.close()
            self.modbus_client = None
        
        self.modbus_connected = False
        self.btn_connect.config(state=tk.NORMAL)
        self.btn_disconnect.config(state=tk.DISABLED)
        self.modbus_status.config(text="⚫ Đã ngắt (config vẫn enabled)", foreground='#dc3545')
        self.log("❌ Đã ngắt Modbus RS485 (config vẫn giữ enabled=true)")
        
        # KHÔNG ghi enabled=False - để Detection vẫn tự kết nối được
        # self.save_config(enabled=False)
    
    def disconnect_modbus_silent(self):
        """Ngắt Modbus không tắt đèn, giữ config enabled=True để Detection tự kết nối"""
        if self.modbus_client:
            self.modbus_client.close()
            self.modbus_client = None
        
        self.modbus_connected = False
        self.btn_connect.config(state=tk.NORMAL)
        self.btn_disconnect.config(state=tk.DISABLED)
        self.modbus_status.config(text="⚫ (Detection đang dùng)", foreground='#17a2b8')
    
    def set_light(self, slave_id, state):
        """Bật/tắt đèn cho slave"""
        if not self.modbus_connected or not self.modbus_client:
            messagebox.showwarning("Cảnh báo", "Chưa kết nối Modbus!")
            return
        
        try:
            self.modbus_client.write_coil(0, bool(state), unit=slave_id)
            status = "🔆 BẬT" if state else "⚫ TẮT"
            device = "ESP32 (songoku)" if slave_id == 1 else "ESP8266 (dog)"
            self.modbus_log_msg(f"[TX] Slave {slave_id}: {status} - {device}")
        except Exception as e:
            self.modbus_log_msg(f"[ERROR] Slave {slave_id}: {e}")
    
    def turn_on_all(self):
        """Bật tất cả đèn"""
        self.set_light(1, True)
        self.set_light(2, True)
    
    def turn_off_all(self):
        """Tắt tất cả đèn"""
        self.set_light(1, False)
        self.set_light(2, False)
    
    def test_blink(self):
        """Test nhấp nháy đèn"""
        if not self.modbus_connected:
            messagebox.showwarning("Cảnh báo", "Chưa kết nối Modbus!")
            return
        
        def blink():
            import time
            self.modbus_log_msg("[TEST] Bắt đầu test nhấp nháy...")
            for i in range(3):
                self.set_light(1, True)
                self.set_light(2, True)
                time.sleep(0.3)
                self.set_light(1, False)
                self.set_light(2, False)
                time.sleep(0.3)
            self.modbus_log_msg("[TEST] Hoàn tất!")
        
        threading.Thread(target=blink, daemon=True).start()
    
    def modbus_log_msg(self, msg):
        """Log Modbus"""
        ts = datetime.now().strftime("%H:%M:%S")
        self.modbus_log.config(state=tk.NORMAL)
        self.modbus_log.insert(tk.END, f"[{ts}] {msg}\n")
        self.modbus_log.see(tk.END)
        self.modbus_log.config(state=tk.DISABLED)
    
    def log(self, msg):
        """Log"""
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def on_closing(self):
        """Đóng app"""
        if self.modbus_client:
            self.turn_off_all()
            self.modbus_client.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = DualCameraApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
