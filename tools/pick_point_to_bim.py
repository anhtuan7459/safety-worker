"""
Chương trình Pick điểm trên Camera và tính tọa độ BIM
- Click chuột trên camera để chọn điểm
- Tự động tính tọa độ BIM tương ứng
- Hiển thị kết quả trên màn hình
"""

import cv2
import numpy as np
import os
import sys

# Thêm path để import config
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(script_dir, "config"))

from chuyendoitoado import get_projection_matrix
from chuyendoitoado_cam2 import get_projection_matrix_cam2

# Thông tin camera IP
USER = "admin"
PASS = "12345678%40%40"

# Camera 1
IP1 = "192.168.66.15"
CAMERA_URL_1 = f"rtsp://{USER}:{PASS}@{IP1}:554/cam/realmonitor?channel=1&subtype=1"

# Camera 2
IP2 = "192.168.66.14"
CAMERA_URL_2 = f"rtsp://{USER}:{PASS}@{IP2}:554/cam/realmonitor?channel=1&subtype=1"


class PointPicker:
    def __init__(self, camera_id, camera_ip, camera_url, matrix):
        self.camera_id = camera_id
        self.camera_ip = camera_ip
        self.camera_url = camera_url
        self.matrix = matrix
        self.picked_points = []  # List of (pixel, bim) tuples
        self.current_point = None
        self.cap = None
        
    def pixel_to_bim(self, px, py):
        """Chuyển pixel sang tọa độ BIM"""
        pt = np.array([[[float(px), float(py)]]], dtype=np.float32)
        tpt = cv2.perspectiveTransform(pt, self.matrix)
        tx, ty = float(tpt[0, 0, 0]), float(tpt[0, 0, 1])
        
        # Camera 2: Áp dụng các phép biến đổi
        if self.camera_id == 2:
            tx, ty = ty, tx  # Swap X và Y
            # Remap tx: từ range (-5, 27) sang range (32, 70)
            tx = (tx - (-5)) / 32.0 * 38.0 + 32
            # Remap ty: từ range (32, 70) sang range (-5, 27)
            ty = (ty - 32) / 38.0 * 32.0 + (-5)
            # Đảo ngược Y
            ty = 22 - ty  # 22 = -5 + 27
        
        return tx, ty
    
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Click chọn điểm
            bim_x, bim_y = self.pixel_to_bim(x, y)
            self.current_point = {
                'pixel': (x, y),
                'bim': (bim_x, bim_y)
            }
            self.picked_points.append(self.current_point.copy())
            print(f"[Camera {self.camera_id}] Pixel({x:4d}, {y:4d}) → BIM({bim_x:7.2f}, {bim_y:7.2f})")
    
    def draw_interface(self, frame):
        """Vẽ giao diện và các điểm đã pick"""
        display = frame.copy()
        
        # Hiển thị camera ID
        cv2.putText(display, f"CAMERA {self.camera_id} ({self.camera_ip})", (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # Vẽ các điểm đã pick
        for i, point_data in enumerate(self.picked_points):
            px, py = point_data['pixel']
            bim_x, bim_y = point_data['bim']
            
            # Vẽ điểm
            color = (0, 255, 0) if i == len(self.picked_points) - 1 else (0, 255, 255)
            cv2.circle(display, (px, py), 8, color, -1)
            cv2.circle(display, (px, py), 12, (255, 255, 255), 2)
            
            # Hiển thị thông tin
            label = f"#{i+1}: Pixel({px},{py})"
            cv2.putText(display, label, (px + 15, py - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            bim_label = f"BIM({bim_x:.1f}, {bim_y:.1f})"
            cv2.putText(display, bim_label, (px + 15, py - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Vẽ điểm hiện tại (nếu có)
        if self.current_point:
            px, py = self.current_point['pixel']
            bim_x, bim_y = self.current_point['bim']
            cv2.circle(display, (px, py), 10, (0, 0, 255), -1)
            cv2.circle(display, (px, py), 14, (255, 255, 255), 2)
        
        # Hiển thị số điểm đã pick
        cv2.putText(display, f"Points: {len(self.picked_points)}", (10, display.shape[0] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return display
    
    def save_results(self):
        """Lưu kết quả vào file"""
        if not self.picked_points:
            print("[WARN] Khong co diem nao de luu!")
            return
        
        output_file = os.path.join(script_dir, "tools", f"picked_points_cam{self.camera_id}.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Ket qua pick diem Camera {self.camera_id} ({self.camera_ip})\n")
            f.write("# Format: Pixel_X Pixel_Y BIM_X BIM_Y\n")
            f.write("#\n")
            
            for i, point_data in enumerate(self.picked_points):
                px, py = point_data['pixel']
                bim_x, bim_y = point_data['bim']
                f.write(f"{px:4d} {py:4d} {bim_x:10.2f} {bim_y:10.2f}\n")
        
        print(f"\n[OK] Da luu {len(self.picked_points)} diem vao: {output_file}")
    
    def print_results(self):
        """In kết quả ra terminal"""
        if not self.picked_points:
            return
        
        print("\n" + "="*70)
        print(f"  KET QUA PICK DIEM - CAMERA {self.camera_id}")
        print("="*70)
        print(f"  {'STT':<5} {'Pixel':<15} {'BIM':<25}")
        print("  " + "-"*68)
        
        for i, point_data in enumerate(self.picked_points):
            px, py = point_data['pixel']
            bim_x, bim_y = point_data['bim']
            print(f"  {i+1:<5} ({px:4d}, {py:4d}){'':<5} ({bim_x:7.2f}, {bim_y:7.2f})")
        
        print("="*70 + "\n")
    
    def run(self):
        """Chạy chương trình pick điểm"""
        print(f"\n[INFO] Dang khoi dong Camera {self.camera_id} ({self.camera_ip})...")
        
        # Mở camera
        print(f"[INFO] Dang ket noi toi Camera {self.camera_id}: {self.camera_ip}...")
        self.cap = cv2.VideoCapture(self.camera_url)
        if not self.cap.isOpened():
            print(f"[ERROR] Khong mo duoc Camera {self.camera_id} tai {self.camera_ip}!")
            return False
        
        print(f"[OK] Da ket noi Camera {self.camera_id}: {self.camera_ip}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        window_name = f"Pick Point - Camera {self.camera_id} ({self.camera_ip})"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self.mouse_callback)
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("[ERROR] Khong doc duoc frame tu camera")
                break
            
            display = self.draw_interface(frame)
            cv2.imshow(window_name, display)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == ord('Q') or key == 27:
                # Thoát
                break
            elif key == ord('c') or key == ord('C'):
                # Xóa điểm cuối
                if self.picked_points:
                    removed = self.picked_points.pop()
                    print(f"[INFO] Da xoa diem cuoi: Pixel{removed['pixel']} → BIM{removed['bim']}")
                    self.current_point = None
            elif key == ord('r') or key == ord('R'):
                # Reset tất cả
                count = len(self.picked_points)
                self.picked_points = []
                self.current_point = None
                print(f"[INFO] Da reset {count} diem")
            elif key == ord('s') or key == ord('S'):
                # Lưu kết quả
                self.save_results()
                self.print_results()
        
        self.cap.release()
        cv2.destroyAllWindows()
        
        # In kết quả cuối cùng
        if self.picked_points:
            self.print_results()
        
        return True


def main():
    import sys
    
    # Kiểm tra tham số dòng lệnh
    camera_id = None
    if len(sys.argv) > 1:
        try:
            camera_id = int(sys.argv[1])
            if camera_id not in [1, 2]:
                print("[ERROR] Camera ID phai la 1 hoac 2!")
                return
        except ValueError:
            print("[ERROR] Camera ID phai la so!")
            return
    
    print("\n" + "="*60)
    print("       PICK DIEM TREN CAMERA - TINH TOA DO BIM")
    print("="*60)
    
    # Nếu không có tham số, hỏi người dùng
    if camera_id is None:
        print("Chon camera:")
        print("  1. Camera 1 (192.168.66.15)")
        print("  2. Camera 2 (192.168.66.14)")
        print("="*60)
        
        choice = input("\n>>> Nhap so camera (1 hoac 2): ").strip()
        
        if choice == "1":
            camera_id = 1
        elif choice == "2":
            camera_id = 2
        else:
            print("[ERROR] Lua chon khong hop le!")
            return
    
    # Thiết lập camera
    if camera_id == 1:
        camera_ip = IP1
        camera_url = CAMERA_URL_1
        matrix = get_projection_matrix().astype('float32')
    else:
        camera_id = 2
        camera_ip = IP2
        camera_url = CAMERA_URL_2
        matrix = get_projection_matrix_cam2().astype('float32')
    
    print(f"\n[INFO] Dang khoi dong Camera {camera_id}...\n")
    
    picker = PointPicker(camera_id, camera_ip, camera_url, matrix)
    picker.run()
    
    print("\n[EXIT] Da thoat chuong trinh.")


if __name__ == "__main__":
    main()

