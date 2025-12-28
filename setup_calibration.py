"""
Setup Calibration Tool - Dual Camera
- Calibrate Camera 1 (IP1: 192.168.66.15) trước
- Sau đó Calibrate Camera 2 (IP2: 192.168.66.14)
- Cả 2 camera đều mapping về cùng hệ tọa độ BIM/Revit
"""

import cv2
import numpy as np
import subprocess
import sys
import os
from signal_output import signal_calibration_done

# Thông tin camera IP
USER = "admin"
PASS = "12345678%40%40"

# Camera 1
IP1 = "192.168.66.15"
CAMERA_URL_1 = f"rtsp://{USER}:{PASS}@{IP1}:554/cam/realmonitor?channel=1&subtype=1"

# Camera 2
IP2 = "192.168.66.14"
CAMERA_URL_2 = f"rtsp://{USER}:{PASS}@{IP2}:554/cam/realmonitor?channel=1&subtype=1"

# BIM coordinates gốc (dùng cho cả 2 camera khi click)
# User click cùng thứ tự: Top-Left, Bottom-Left, Top-Right, Bottom-Right
BIM_COORDS_BASE = {
    'top_left': (70, 27),       # E70, N27
    'bottom_left': (32, 27),    # E32, N27
    'top_right': (70, -5),      # E70, N-5
    'bottom_right': (32, -5)    # E32, N-5
}

def get_bim_coords_for_camera(camera_id):
    """
    Trả về BIM coords cho camera.
    CẢ 2 CAMERA DÙNG CÙNG BIM COORDS.
    Việc đảo ngược cho Camera 2 được xử lý TỰ ĐỘNG trong run_dual_cam.py
    """
    return BIM_COORDS_BASE  # Cả 2 camera dùng chung


class CalibrationSetup:
    def __init__(self, camera_id, camera_ip, camera_url):
        self.camera_id = camera_id
        self.camera_ip = camera_ip
        self.camera_url = camera_url
        self.points = []
        self.labels = ["Top Left (Xa-Trái)", "Bottom Left (Gần-Trái)", 
                       "Top Right (Xa-Phải)", "Bottom Right (Gần-Phải)"]
        self.frame = None
        self.cap = None
        self.save_clicked = False
        self.cancel_clicked = False
        
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Kiểm tra click vào nút SAVE (góc trên bên phải)
            if len(self.points) == 4:
                if 470 <= x <= 580 and 50 <= y <= 90:
                    # Click nút SAVE
                    self.save_clicked = True
                    return
                elif 470 <= x <= 580 and 100 <= y <= 140:
                    # Click nút HỦY
                    self.cancel_clicked = True
                    return
            
            # Click chọn điểm calibration
            if len(self.points) < 4:
                self.points.append((x, y))
                print(f"[{len(self.points)}/4] Da chon {self.labels[len(self.points)-1]}: ({x}, {y})")
            else:
                # Reset
                self.points = [(x, y)]
                print(f"\n[RESET] Da chon lai {self.labels[0]}: ({x}, {y})")
    
    def draw_interface(self, frame):
        """Ve cac diem va huong dan len frame"""
        display = frame.copy()
        colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 255, 0)]
        
        # Hiển thị camera ID
        cv2.putText(display, f"CAMERA {self.camera_id} ({self.camera_ip})", (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # Ve cac diem da chon
        for i, point in enumerate(self.points):
            cv2.circle(display, point, 8, colors[i], -1)
            cv2.circle(display, point, 12, (255, 255, 255), 2)
            
            label = f"{i+1}. {self.labels[i]} {point}"
            cv2.putText(display, label, (point[0] + 15, point[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors[i], 2)
        
        # Ve duong noi
        if len(self.points) >= 2:
            for i in range(len(self.points)):
                j = (i + 1) % len(self.points)
                if j < len(self.points):
                    cv2.line(display, self.points[i], self.points[j], (0, 255, 255), 2)
        
        # Huong dan
        y_offset = 60
        if len(self.points) < 4:
            text = f"[{len(self.points)}/4] Click chon: {self.labels[len(self.points)]}"
            cv2.putText(display, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            cv2.putText(display, "Da chon du 4 diem!", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Vẽ nút SAVE (màu xanh lá) - góc trên bên phải
            cv2.rectangle(display, (470, 50), (580, 90), (0, 200, 0), -1)
            cv2.rectangle(display, (470, 50), (580, 90), (255, 255, 255), 2)
            cv2.putText(display, "SAVE", (490, 78),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Vẽ nút HỦY (màu đỏ) - dưới nút SAVE
            cv2.rectangle(display, (470, 100), (580, 140), (0, 0, 200), -1)
            cv2.rectangle(display, (470, 100), (580, 140), (255, 255, 255), 2)
            cv2.putText(display, "HUY", (500, 128),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return display
    
    def calculate_and_print_bim_coords(self):
        """Tính toán và in 4 điểm calibration sau khi chuyển sang hệ BIM"""
        try:
            # Load ma trận homography vừa tạo
            script_dir = os.path.dirname(os.path.abspath(__file__))
            if self.camera_id == 1:
                sys.path.insert(0, os.path.join(script_dir, "config"))
                from chuyendoitoado import get_projection_matrix
                matrix = get_projection_matrix().astype('float32')
            else:
                sys.path.insert(0, os.path.join(script_dir, "config"))
                from chuyendoitoado_cam2 import get_projection_matrix_cam2
                matrix = get_projection_matrix_cam2().astype('float32')
            
            # Lấy BIM coords mong đợi để so sánh
            expected_bim = get_bim_coords_for_camera(self.camera_id)
            expected_points = [
                expected_bim['top_left'],
                expected_bim['bottom_left'],
                expected_bim['top_right'],
                expected_bim['bottom_right']
            ]
            
            # Tính toán 4 điểm sang BIM
            bim_points = []
            point_names = ["Top Left", "Bottom Left", "Top Right", "Bottom Right"]
            
            print("\n" + "="*70)
            print(f"  KIỂM TRA ĐỘ CHÍNH XÁC MA TRẬN CAMERA {self.camera_id}")
            print("="*70)
            print("  So sánh: Pixel → BIM (tính toán) vs BIM (mong đợi)")
            print("="*70)
            
            total_error = 0.0
            max_error = 0.0
            
            for i, (px, py) in enumerate(self.points):
                # Chuyển pixel sang BIM bằng perspectiveTransform
                pt = np.array([[[float(px), float(py)]]], dtype=np.float32)
                tpt = cv2.perspectiveTransform(pt, matrix)
                tx, ty = float(tpt[0, 0, 0]), float(tpt[0, 0, 1])
                
                # Camera 2: Áp dụng các phép biến đổi như trong run_dual_cam.py
                if self.camera_id == 2:
                    tx, ty = ty, tx  # Swap X và Y
                    # Remap tx: từ range (-5, 27) sang range (32, 70)
                    tx = (tx - (-5)) / 32.0 * 38.0 + 32
                    # Remap ty: từ range (32, 70) sang range (-5, 27)
                    ty = (ty - 32) / 38.0 * 32.0 + (-5)
                    # Đảo ngược Y
                    ty = 22 - ty  # 22 = -5 + 27
                
                bim_points.append((tx, ty))
                
                # So sánh với giá trị mong đợi
                exp_x, exp_y = expected_points[i]
                error_x = abs(tx - exp_x)
                error_y = abs(ty - exp_y)
                error_total = np.sqrt(error_x**2 + error_y**2)
                total_error += error_total
                max_error = max(max_error, error_total)
                
                # In ra terminal với so sánh
                print(f"  {point_names[i]:15s}:")
                print(f"    Pixel({px:4d}, {py:4d}) → BIM({tx:7.2f}, {ty:7.2f})")
                print(f"    Mong đợi: ({exp_x:7.2f}, {exp_y:7.2f})")
                print(f"    Sai số:   ΔX={error_x:6.3f}, ΔY={error_y:6.3f}, Tổng={error_total:6.3f}")
                print()
            
            avg_error = total_error / 4.0
            
            print("="*70)
            print(f"  TÓM TẮT ĐỘ CHÍNH XÁC CAMERA {self.camera_id}:")
            print(f"    - Sai số trung bình: {avg_error:.3f}")
            print(f"    - Sai số lớn nhất:   {max_error:.3f}")
            if max_error < 0.1:
                print(f"    - Đánh giá: ✅ RẤT TỐT (sai số < 0.1)")
            elif max_error < 0.5:
                print(f"    - Đánh giá: ✅ TỐT (sai số < 0.5)")
            elif max_error < 1.0:
                print(f"    - Đánh giá: ⚠️  CHẤP NHẬN ĐƯỢC (sai số < 1.0)")
            else:
                print(f"    - Đánh giá: ❌ CẦN KIỂM TRA LẠI (sai số >= 1.0)")
            print("="*70)
            
            # In ma trận homography H
            print(f"\n  MA TRẬN HOMOGRAPHY H - CAMERA {self.camera_id}:")
            print("  " + "-"*66)
            for i in range(3):
                print(f"    [{matrix[i,0]:12.6f}  {matrix[i,1]:12.6f}  {matrix[i,2]:12.6f}]")
            print("  " + "-"*66 + "\n")
            
        except Exception as e:
            print(f"[WARN] Không thể tính toán BIM coordinates: {e}")
    
    def save_to_file(self):
        """Ghi toa do vao file chuyendoitoado.py hoặc chuyendoitoado_cam2.py"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            if self.camera_id == 1:
                file_path = os.path.join(script_dir, "config", "chuyendoitoado.py")
                func_name = "get_projection_matrix"
            else:
                file_path = os.path.join(script_dir, "config", "chuyendoitoado_cam2.py")
                func_name = "get_projection_matrix_cam2"
            
            # Tự động lấy BIM coords phù hợp cho camera
            bim = get_bim_coords_for_camera(self.camera_id)
            if self.camera_id == 1:
                comment = "Camera 1 - dùng BIM coords gốc"
            else:
                comment = "Camera 2 - tự động đảo ngược (vuông góc với Camera 1)"
            
            new_content = f'''import cv2
import numpy as np

def {func_name}():
    """
    Return a homography matrix for camera {self.camera_id} projection.
    Camera {self.camera_id} IP: {self.camera_ip}
    """
    # Interest points in camera (pixel)
    top_left_point = {self.points[0]}
    bottom_left_point = {self.points[1]}
    top_right_point = {self.points[2]}
    bottom_right_point = {self.points[3]}

    # Interest points in BIM coordinates (Project coordinates)
    # Hệ tọa độ Revit: E (East) = X, N (North) = Y
    # {comment}
    top_left = {bim['top_left']}
    bottom_left = {bim['bottom_left']}
    top_right = {bim['top_right']}
    bottom_right = {bim['bottom_right']}

    # Get perspective transformation matrix
    pts1 = np.float32([top_left_point, bottom_left_point, top_right_point, bottom_right_point])
    pts2 = np.float32([top_left, bottom_left, top_right, bottom_right])
    matrix = cv2.getPerspectiveTransform(pts1, pts2)

    return np.array(matrix)
'''
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("\n" + "="*60)
            print(f"[OK] Da luu toa do Camera {self.camera_id} vao {os.path.basename(file_path)}")
            print("="*60)
            print(f"    top_left_point = {self.points[0]}")
            print(f"    bottom_left_point = {self.points[1]}")
            print(f"    top_right_point = {self.points[2]}")
            print(f"    bottom_right_point = {self.points[3]}")
            print("="*60)
            
            # Tính toán và in 4 điểm sau khi chuyển sang hệ BIM
            self.calculate_and_print_bim_coords()
            
            # Gửi tín hiệu calibration done
            signal_calibration_done(self.camera_id)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Khong luu duoc: {e}")
            return False
    
    def run(self):
        """Chay calibration setup cho 1 camera"""
        print("\n" + "="*60)
        print(f"SETUP CALIBRATION - CAMERA {self.camera_id} ({self.camera_ip})")
        print("="*60)
        print("Huong dan:")
        print("1. Click chuot de chon 4 goc CUNG MAT BAN theo thu tu:")
        print("   - Top Left (Xa camera, ben Trai)")
        print("   - Bottom Left (Gan camera, ben Trai)")
        print("   - Top Right (Xa camera, ben Phai)")
        print("   - Bottom Right (Gan camera, ben Phai)")
        print("2. Sau khi chon du 4 diem:")
        print("   - Click nut SAVE de luu")
        print("   - Click nut HUY de huy")
        print("="*60)
        
        # Mo camera IP
        print(f"[INFO] Dang ket noi toi Camera {self.camera_id}: {self.camera_ip}...")
        self.cap = cv2.VideoCapture(self.camera_url)
        if not self.cap.isOpened():
            print(f"[ERROR] Khong mo duoc Camera {self.camera_id} tai {self.camera_ip}!")
            return False
        
        print(f"[OK] Da ket noi Camera {self.camera_id}: {self.camera_ip}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        window_name = f"Setup Calibration - Camera {self.camera_id} ({self.camera_ip})"
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
            
            # Check click nút SAVE
            if self.save_clicked:
                self.save_clicked = False
                if len(self.points) == 4:
                    if self.save_to_file():
                        self.cap.release()
                        cv2.destroyAllWindows()
                        return True
                else:
                    print("[WARN] Chua chon du 4 diem!")
            
            # Check click nút HỦY hoặc nhấn Q/ESC
            if self.cancel_clicked or key == ord('q') or key == ord('Q') or key == 27:
                print(f"[CANCEL] Da huy calibration Camera {self.camera_id}")
                break
        
        self.cap.release()
        cv2.destroyAllWindows()
        return False


def print_summary_both_cameras():
    """In tổng hợp 4 điểm calibration của cả 2 camera trong hệ BIM"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(script_dir, "config")
        sys.path.insert(0, config_dir)
        
        from chuyendoitoado import get_projection_matrix
        from chuyendoitoado_cam2 import get_projection_matrix_cam2
        
        # Đọc lại các điểm pixel từ file đã lưu
        import re
        
        # Camera 1
        cam1_file = os.path.join(config_dir, "chuyendoitoado.py")
        cam1_points = []
        with open(cam1_file, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = re.findall(r'(top_left|bottom_left|top_right|bottom_right)_point = \((\d+), (\d+)\)', content)
            cam1_points = [(int(x), int(y)) for _, x, y in sorted(matches)]
        
        # Camera 2
        cam2_file = os.path.join(config_dir, "chuyendoitoado_cam2.py")
        cam2_points = []
        with open(cam2_file, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = re.findall(r'(top_left|bottom_left|top_right|bottom_right)_point = \((\d+), (\d+)\)', content)
            cam2_points = [(int(x), int(y)) for _, x, y in sorted(matches)]
        
        # Load matrices
        matrix1 = get_projection_matrix().astype('float32')
        matrix2 = get_projection_matrix_cam2().astype('float32')
        
        # Lấy BIM coords mong đợi để so sánh
        expected_bim = get_bim_coords_for_camera(1)  # Cả 2 camera dùng chung
        expected_points = [
            expected_bim['top_left'],
            expected_bim['bottom_left'],
            expected_bim['top_right'],
            expected_bim['bottom_right']
        ]
        
        point_names = ["Top Left", "Bottom Left", "Top Right", "Bottom Right"]
        
        print("\n" + "="*80)
        print("  KIỂM TRA ĐỘ CHÍNH XÁC MA TRẬN CỦA CẢ 2 CAMERA")
        print("="*80)
        print("  So sánh: Pixel → BIM (tính toán) vs BIM (mong đợi)")
        print("="*80)
        
        # Camera 1
        print("\n  📹 CAMERA 1 (192.168.66.15):")
        print("  " + "-"*76)
        cam1_total_error = 0.0
        cam1_max_error = 0.0
        for i, (px, py) in enumerate(cam1_points):
            pt = np.array([[[float(px), float(py)]]], dtype=np.float32)
            tpt = cv2.perspectiveTransform(pt, matrix1)
            tx, ty = float(tpt[0, 0, 0]), float(tpt[0, 0, 1])
            
            # So sánh với giá trị mong đợi
            exp_x, exp_y = expected_points[i]
            error_x = abs(tx - exp_x)
            error_y = abs(ty - exp_y)
            error_total = np.sqrt(error_x**2 + error_y**2)
            cam1_total_error += error_total
            cam1_max_error = max(cam1_max_error, error_total)
            
            print(f"    {point_names[i]:15s}:")
            print(f"      Pixel({px:4d}, {py:4d}) → BIM({tx:7.2f}, {ty:7.2f})")
            print(f"      Mong đợi: ({exp_x:7.2f}, {exp_y:7.2f}) | Sai số: ΔX={error_x:6.3f}, ΔY={error_y:6.3f}, Tổng={error_total:6.3f}")
        
        cam1_avg_error = cam1_total_error / 4.0
        print(f"    → Sai số trung bình: {cam1_avg_error:.3f} | Sai số lớn nhất: {cam1_max_error:.3f}")
        
        # Camera 2
        print("\n  📹 CAMERA 2 (192.168.66.14):")
        print("  " + "-"*76)
        cam2_total_error = 0.0
        cam2_max_error = 0.0
        for i, (px, py) in enumerate(cam2_points):
            pt = np.array([[[float(px), float(py)]]], dtype=np.float32)
            tpt = cv2.perspectiveTransform(pt, matrix2)
            tx, ty = float(tpt[0, 0, 0]), float(tpt[0, 0, 1])
            # Áp dụng các phép biến đổi cho Camera 2
            tx, ty = ty, tx  # Swap
            tx = (tx - (-5)) / 32.0 * 38.0 + 32  # Remap X
            ty = (ty - 32) / 38.0 * 32.0 + (-5)  # Remap Y
            ty = 22 - ty  # Đảo Y
            
            # So sánh với giá trị mong đợi
            exp_x, exp_y = expected_points[i]
            error_x = abs(tx - exp_x)
            error_y = abs(ty - exp_y)
            error_total = np.sqrt(error_x**2 + error_y**2)
            cam2_total_error += error_total
            cam2_max_error = max(cam2_max_error, error_total)
            
            print(f"    {point_names[i]:15s}:")
            print(f"      Pixel({px:4d}, {py:4d}) → BIM({tx:7.2f}, {ty:7.2f})")
            print(f"      Mong đợi: ({exp_x:7.2f}, {exp_y:7.2f}) | Sai số: ΔX={error_x:6.3f}, ΔY={error_y:6.3f}, Tổng={error_total:6.3f}")
        
        cam2_avg_error = cam2_total_error / 4.0
        print(f"    → Sai số trung bình: {cam2_avg_error:.3f} | Sai số lớn nhất: {cam2_max_error:.3f}")
        
        # Tổng kết
        print("\n" + "="*80)
        print("  TÓM TẮT ĐỘ CHÍNH XÁC:")
        print(f"    Camera 1: Trung bình={cam1_avg_error:.3f}, Lớn nhất={cam1_max_error:.3f}")
        print(f"    Camera 2: Trung bình={cam2_avg_error:.3f}, Lớn nhất={cam2_max_error:.3f}")
        overall_max = max(cam1_max_error, cam2_max_error)
        if overall_max < 0.1:
            print(f"    Đánh giá: ✅ RẤT TỐT (sai số < 0.1)")
        elif overall_max < 0.5:
            print(f"    Đánh giá: ✅ TỐT (sai số < 0.5)")
        elif overall_max < 1.0:
            print(f"    Đánh giá: ⚠️  CHẤP NHẬN ĐƯỢC (sai số < 1.0)")
        else:
            print(f"    Đánh giá: ❌ CẦN KIỂM TRA LẠI (sai số >= 1.0)")
        print("="*80)
        
        # In ma trận homography H của cả 2 camera
        print("\n  MA TRẬN HOMOGRAPHY H - CAMERA 1:")
        print("  " + "-"*76)
        for i in range(3):
            print(f"    [{matrix1[i,0]:12.6f}  {matrix1[i,1]:12.6f}  {matrix1[i,2]:12.6f}]")
        print("  " + "-"*76)
        
        print("\n  MA TRẬN HOMOGRAPHY H - CAMERA 2:")
        print("  " + "-"*76)
        for i in range(3):
            print(f"    [{matrix2[i,0]:12.6f}  {matrix2[i,1]:12.6f}  {matrix2[i,2]:12.6f}]")
        print("  " + "-"*76 + "\n")
        
    except Exception as e:
        print(f"[WARN] Không thể in tổng hợp: {e}")


def run_dual_camera():
    """Chay run_dual_cam.py"""
    try:
        print("\n[START] Dang chay run_dual_cam.py...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        run_cam_path = os.path.join(script_dir, "run_dual_cam.py")
        subprocess.Popen([sys.executable, run_cam_path])
        print(f"[OK] Da khoi dong: {run_cam_path}")
    except Exception as e:
        print(f"[ERROR] Khong chay duoc: {e}")


def main():
    print("\n" + "="*60)
    print("       DUAL CAMERA CALIBRATION SETUP")
    print("="*60)
    print("Se calibrate lan luot:")
    print(f"  1. Camera 1: {IP1}")
    print(f"  2. Camera 2: {IP2}")
    print("Ca 2 camera se mapping ve CUNG HE TOA DO BIM/Revit")
    print("="*60)
    
    # Calibrate Camera 1
    print("\n>>> BAT DAU CALIBRATE CAMERA 1 <<<")
    setup1 = CalibrationSetup(camera_id=1, camera_ip=IP1, camera_url=CAMERA_URL_1)
    result1 = setup1.run()
    
    if not result1:
        print("\n[ABORT] Calibration Camera 1 that bai. Dung chuong trinh.")
        return
    
    # Calibrate Camera 2
    print("\n>>> BAT DAU CALIBRATE CAMERA 2 <<<")
    setup2 = CalibrationSetup(camera_id=2, camera_ip=IP2, camera_url=CAMERA_URL_2)
    result2 = setup2.run()
    
    if not result2:
        print("\n[ABORT] Calibration Camera 2 that bai. Dung chuong trinh.")
        return
    
    # In tổng hợp cả 2 camera
    print_summary_both_cameras()
    
    # Hoi nguoi dung co muon chay dual camera khong
    print("\n" + "="*60)
    print("[SUCCESS] Da calibrate xong ca 2 camera!")
    print("="*60)
    print("Nhan 'Y' de chay run_dual_cam.py, hoac phim khac de thoat...")
    
    key = cv2.waitKey(0) & 0xFF
    if key == ord('y') or key == ord('Y'):
        run_dual_camera()
    else:
        print("[EXIT] Da thoat.")


if __name__ == "__main__":
    main()
