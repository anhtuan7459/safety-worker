"""
Dual Camera Detection System
- Chạy 2 camera IP đồng thời với đa luồng
- Camera 1: 192.168.66.15
- Camera 2: 192.168.66.14
- Cả 2 camera đều mapping về cùng hệ tọa độ BIM/Revit
- Ghi tọa độ vào database
"""

import os
import cv2
import numpy as np
import threading
from queue import Queue
from ultralytics import YOLO
from datetime import datetime
import pandas as pd

# Tự động chuyển đến thư mục script
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

from config.chuyendoitoado import get_projection_matrix
from config.chuyendoitoado_cam2 import get_projection_matrix_cam2
from db_manage import create_temp_table, add_many_temp
from signal_output import (
    signal_inside, signal_outside, signal_ready, signal_stop, signal_db_saved, 
    get_outside_direction, init_modbus, close_modbus
)

# Database path
DB_PATH = os.path.join(script_dir, "output", "data.db")

# Thông tin camera IP
USER = "admin"
PASS = "12345678%40%40"

# Camera 1
IP1 = "192.168.66.15"
CAMERA_URL_1 = f"rtsp://{USER}:{PASS}@{IP1}:554/cam/realmonitor?channel=1&subtype=1"

# Camera 2
IP2 = "192.168.66.14"
CAMERA_URL_2 = f"rtsp://{USER}:{PASS}@{IP2}:554/cam/realmonitor?channel=1&subtype=1"

# Queues để lưu frame và kết quả detection
frame_queue_1 = Queue(maxsize=2)
frame_queue_2 = Queue(maxsize=2)
result_queue = Queue(maxsize=10)

# Event để dừng các thread
stop_event = threading.Event()


class CameraThread(threading.Thread):
    """Thread để capture frame từ camera"""
    def __init__(self, camera_id, camera_url, frame_queue):
        super().__init__()
        self.camera_id = camera_id
        self.camera_url = camera_url
        self.frame_queue = frame_queue
        self.daemon = True
        
    def run(self):
        cap = cv2.VideoCapture(self.camera_url)
        if not cap.isOpened():
            print(f"[ERROR] Không thể kết nối Camera {self.camera_id}")
            return
        
        print(f"[OK] Camera {self.camera_id} đã kết nối")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print(f"[ERROR] Mất kết nối Camera {self.camera_id}")
                break
            
            # Bỏ frame cũ nếu queue đầy
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except:
                    pass
            self.frame_queue.put((self.camera_id, frame))
        
        cap.release()
        print(f"[INFO] Camera {self.camera_id} đã ngắt kết nối")


class DetectionThread(threading.Thread):
    """Thread để detect object từ frame"""
    def __init__(self, model, proj_matrix_1, proj_matrix_2, bim_bounds):
        super().__init__()
        self.model = model
        self.proj_matrix_1 = proj_matrix_1
        self.proj_matrix_2 = proj_matrix_2
        self.bim_bounds = bim_bounds
        self.daemon = True
        
    def pixel_to_bim(self, px, py, camera_id):
        """Chuyển pixel sang tọa độ BIM"""
        if camera_id == 1:
            matrix = self.proj_matrix_1
        else:
            matrix = self.proj_matrix_2
        
        pt = np.array([[[float(px), float(py)]]], dtype=np.float32)
        tpt = cv2.perspectiveTransform(pt, matrix)
        tx, ty = float(tpt[0, 0, 0]), float(tpt[0, 0, 1])
        
        # Camera 2: HOÁN ĐỔI X và Y (vì camera vuông góc) + REMAP + ĐẢO Y
        if camera_id == 2:
            tx, ty = ty, tx  # Swap X và Y
            
            # Remap tx: từ range (-5, 27) sang range (32, 70)
            tx = (tx - (-5)) / 32.0 * 38.0 + 32
            
            # Remap ty: từ range (32, 70) sang range (-5, 27)
            ty = (ty - 32) / 38.0 * 32.0 + (-5)
            
            # Đảo ngược Y (gần camera → xa trong BIM, cần sửa)
            ty = 22 - ty  # 22 = -5 + 27
        
        return tx, ty
    
    def is_inside_bim(self, x, y):
        """Kiểm tra tọa độ có trong vùng BIM không"""
        x_min, x_max, y_min, y_max = self.bim_bounds
        return x_min <= x <= x_max and y_min <= y <= y_max
    
    def process_frame(self, camera_id, frame):
        """Xử lý frame và detect objects"""
        results = self.model(frame, device=0, conf=0.3, imgsz=640, half=True, verbose=False)
        
        # Filter theo camera:
        # Camera 1: chỉ detect dog
        # Camera 2: chỉ detect songoku
        if camera_id == 1:
            allowed_labels = {"dog"}
        else:
            allowed_labels = {"songoku"}
        
        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                label = self.model.names.get(cls_id, str(cls_id))
                
                # Bỏ qua các mốc
                if label.lower() in {"moc1", "moc2", "moc3", "moc4"}:
                    continue
                
                # Chỉ giữ lại label được phép cho camera này
                if label.lower() not in allowed_labels:
                    continue
                
                # Lấy confidence score
                confidence = float(box.conf[0])
                
                # Tính tọa độ tâm đáy
                cx = int((x1 + x2) / 2)
                cy = y2
                
                # Chuyển sang tọa độ BIM
                try:
                    tx, ty = self.pixel_to_bim(cx, cy, camera_id)
                except Exception as e:
                    print(f"[ERROR] Transform failed: {e}")
                    continue
                
                inside_bim = self.is_inside_bim(tx, ty)
                
                detections.append({
                    'camera_id': camera_id,
                    'label': label,
                    'confidence': confidence,
                    'bbox': (x1, y1, x2, y2),
                    'center': (cx, cy),
                    'bim': (tx, ty),
                    'inside_bim': inside_bim
                })
        
        return detections
    
    def run(self):
        while not stop_event.is_set():
            # Xử lý Camera 1
            try:
                camera_id, frame = frame_queue_1.get(timeout=0.1)
                detections = self.process_frame(camera_id, frame)
                result_queue.put((camera_id, frame, detections))
            except:
                pass
            
            # Xử lý Camera 2
            try:
                camera_id, frame = frame_queue_2.get(timeout=0.1)
                detections = self.process_frame(camera_id, frame)
                result_queue.put((camera_id, frame, detections))
            except:
                pass


def get_bim_bounds():
    """Đọc vùng BIM từ file calibration"""
    config_path = os.path.join(script_dir, 'config', 'chuyendoitoado.py')
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    import re
    pattern = r'(top_left|bottom_left|top_right|bottom_right)\s*=\s*\(([^)]+)\)'
    matches = re.findall(pattern, content)
    
    bim_coords = {}
    for name, coords in matches:
        if 'point' not in name:
            x, y = map(float, coords.split(','))
            bim_coords[name] = (x, y)
    
    all_x = [bim_coords[k][0] for k in bim_coords]
    all_y = [bim_coords[k][1] for k in bim_coords]
    
    return min(all_x), max(all_x), min(all_y), max(all_y)


def draw_detections(frame, detections, camera_id):
    """Vẽ kết quả detection lên frame"""
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        cx, cy = det['center']
        tx, ty = det['bim']
        label = det['label']
        confidence = det.get('confidence', 0.0)
        inside_bim = det['inside_bim']
        
        # Màu sắc
        if inside_bim:
            box_color = (0, 0, 255)  # Đỏ - trong vùng
            status = "TRONG"
        else:
            box_color = (255, 150, 0)  # Xanh - ngoài vùng
            status = "NGOAI"
        
        # Vẽ bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
        cv2.line(frame, (x1, y2), (x2, y2), box_color, 3)
        cv2.circle(frame, (cx, cy), 6, box_color, -1)
        
        # Hiển thị thông tin với confidence
        cv2.putText(frame, f"{label} [{status}] Conf:{confidence:.2f}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)
        cv2.putText(frame, f"BIM:({tx:.1f},{ty:.1f})", (x1, y2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)
    
    # Hiển thị camera ID và thời gian
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, f"CAM {camera_id} | {timestamp}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    return frame


def save_to_excel(detections_data, excel_path):
    """Lưu dữ liệu detection vào file Excel"""
    try:
        if not detections_data:
            return
        
        # Tạo DataFrame
        df = pd.DataFrame(detections_data)
        
        # Kiểm tra file đã tồn tại chưa
        if os.path.exists(excel_path):
            # Đọc file cũ và append
            df_old = pd.read_excel(excel_path, engine='openpyxl')
            df = pd.concat([df_old, df], ignore_index=True)
        
        # Lưu vào Excel
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
    except Exception as e:
        print(f"[ERROR] Khong luu duoc Excel: {e}")


def main():
    print("="*60)
    print("       DUAL CAMERA DETECTION SYSTEM")
    print("="*60)
    print(f"Camera 1: {IP1}")
    print(f"Camera 2: {IP2}")
    print("="*60)
    
    # Load model
    model_path = os.path.join(script_dir, "models", "best.pt")
    print(f"[INFO] Loading model: {model_path}")
    model = YOLO(model_path)
    
    # Load homography matrices
    print("[INFO] Loading calibration matrices...")
    proj_matrix_1 = get_projection_matrix().astype('float32')
    proj_matrix_2 = get_projection_matrix_cam2().astype('float32')
    
    # Get BIM bounds
    bim_bounds = get_bim_bounds()
    print(f"[INFO] Vùng BIM: X=[{bim_bounds[0]}, {bim_bounds[1]}], Y=[{bim_bounds[2]}, {bim_bounds[3]}]")
    
    # Khởi tạo database
    create_temp_table(DB_PATH)
    print(f"[INFO] Database: {DB_PATH}")
    
    # Khởi tạo Modbus RS485 cho điều khiển đèn
    print("[INFO] Khởi tạo Modbus RS485...")
    init_modbus()
    
    # Khởi tạo camera threads
    print("[INFO] Đang kết nối cameras...")
    cam_thread_1 = CameraThread(1, CAMERA_URL_1, frame_queue_1)
    cam_thread_2 = CameraThread(2, CAMERA_URL_2, frame_queue_2)
    
    # Khởi tạo detection thread
    det_thread = DetectionThread(model, proj_matrix_1, proj_matrix_2, bim_bounds)
    
    # Start threads
    cam_thread_1.start()
    cam_thread_2.start()
    det_thread.start()
    
    print("[INFO] Bắt đầu detection... Nhấn ESC để thoát.")
    signal_ready()  # Gửi tín hiệu hệ thống sẵn sàng
    
    # Biến để lưu frame và detections mới nhất
    latest_frames = {1: None, 2: None}
    latest_detections = {1: [], 2: []}
    
    # Counter cho database
    frame_count = 0
    SAVE_INTERVAL = 10
    
    # Đường dẫn file Excel
    excel_path = os.path.join(script_dir, "output", "detection_results.xlsx")
    
    while True:
        # Lấy kết quả từ queue
        try:
            camera_id, frame, detections = result_queue.get(timeout=0.1)
            latest_frames[camera_id] = frame
            latest_detections[camera_id] = detections
            
            # Log detections
            for det in detections:
                print(f"[CAM{camera_id}] {det['label']} -> BIM: ({det['bim'][0]:.2f}, {det['bim'][1]:.2f})")
        except:
            pass
        
        # Hiển thị Camera 1
        if latest_frames[1] is not None:
            display1 = draw_detections(latest_frames[1].copy(), latest_detections[1], 1)
            cv2.imshow("Camera 1 - Detection", display1)
        
        # Hiển thị Camera 2
        if latest_frames[2] is not None:
            display2 = draw_detections(latest_frames[2].copy(), latest_detections[2], 2)
            cv2.imshow("Camera 2 - Detection", display2)
        
        # Ghi database và Excel
        frame_count += 1
        if frame_count % SAVE_INTERVAL == 0:
            coords_to_save = []
            excel_data = []
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Camera 1 (dog) → person_id = 1
            for det in latest_detections[1]:
                tx, ty = det['bim']
                confidence = det.get('confidence', 0.0)
                coords_to_save.append((tx, ty, 1))  # dog = person_id 1
                
                # Thêm vào Excel data
                excel_data.append({
                    'Timestamp': timestamp,
                    'Camera': 1,
                    'Label': det['label'],
                    'Confidence': confidence,
                    'BIM_X': tx,
                    'BIM_Y': ty,
                    'Status': 'TRONG' if det['inside_bim'] else 'NGOAI'
                })
                
                if det['inside_bim']:
                    signal_inside(det['label'], tx, ty, camera_id=1, person_id=1)
                else:
                    direction = get_outside_direction(tx, ty, bim_bounds)
                    signal_outside(det['label'], tx, ty, camera_id=1, direction=direction)
                    break  # Chỉ lấy 1 detection
            
            # Camera 2 (songoku) → person_id = 0
            for det in latest_detections[2]:
                tx, ty = det['bim']
                confidence = det.get('confidence', 0.0)
                coords_to_save.append((tx, ty, 0))  # songoku = person_id 0
                
                # Thêm vào Excel data
                excel_data.append({
                    'Timestamp': timestamp,
                    'Camera': 2,
                    'Label': det['label'],
                    'Confidence': confidence,
                    'BIM_X': tx,
                    'BIM_Y': ty,
                    'Status': 'TRONG' if det['inside_bim'] else 'NGOAI'
                })
                
                if det['inside_bim']:
                    signal_inside(det['label'], tx, ty, camera_id=2, person_id=0)
                else:
                    direction = get_outside_direction(tx, ty, bim_bounds)
                    signal_outside(det['label'], tx, ty, camera_id=2, direction=direction)
                    break  # Chỉ lấy 1 detection
            
            # Lưu database
            if coords_to_save:
                try:
                    add_many_temp(DB_PATH, coords_to_save)
                    signal_db_saved(len(coords_to_save))
                except Exception as e:
                    print(f"[ERROR] Ghi database: {e}")
            
            # Lưu Excel
            if excel_data:
                save_to_excel(excel_data, excel_path)
        
        # ESC để thoát
        if cv2.waitKey(1) & 0xFF == 27:
            break
    
    # Cleanup
    print("[INFO] Đang tắt...")
    signal_stop()  # Gửi tín hiệu dừng hệ thống (tắt đèn)
    close_modbus()  # Đóng kết nối Modbus
    stop_event.set()
    cam_thread_1.join(timeout=2)
    cam_thread_2.join(timeout=2)
    cv2.destroyAllWindows()
    print("[OK] Đã thoát.")


if __name__ == "__main__":
    main()

