import os
import cv2
import numpy as np
from ultralytics import YOLO
from config.chuyendoitoado import get_projection_matrix
from db_manage import create_temp_table, add_many_temp

# Tự động chuyển đến thư mục script để tránh lỗi đường dẫn
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Database path
DB_PATH = os.path.join(script_dir, "output", "data.db")

# Thông tin camera IP
IP2 = "192.168.66.15"
USER = "admin"
PASS = "12345678%40%40"
CAMERA_URL = f"rtsp://{USER}:{PASS}@{IP2}:554/cam/realmonitor?channel=1&subtype=1"


def get_bim_bounds():
    """Đọc tọa độ BIM từ chuyendoitoado.py và tính vùng hợp lệ"""
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


def main():
    model_path = os.path.join(script_dir, "models", "best.pt")
    model = YOLO(model_path)
    
    # Khởi tạo database
    create_temp_table(DB_PATH)
    print(f"[INFO] Database: {DB_PATH}")
    
    # Load projection matrix (homography) to convert pixel -> project coordinates
    proj_matrix = get_projection_matrix().astype('float32')
    
    # Đọc vùng BIM hợp lệ từ chuyendoitoado.py
    BIM_X_MIN, BIM_X_MAX, BIM_Y_MIN, BIM_Y_MAX = get_bim_bounds()
    print(f"[INFO] Vùng BIM: X=[{BIM_X_MIN}, {BIM_X_MAX}], Y=[{BIM_Y_MIN}, {BIM_Y_MAX}]")
    
    def is_inside_bim(x, y):
        """Kiểm tra tọa độ có nằm trong vùng BIM không"""
        return BIM_X_MIN <= x <= BIM_X_MAX and BIM_Y_MIN <= y <= BIM_Y_MAX

    # Sử dụng camera IP thay vì camera laptop
    print(f"🔗 Đang kết nối tới camera IP: {IP2}...")
    cap = cv2.VideoCapture(CAMERA_URL)
    if not cap.isOpened():
        print(f"❌ Không mở được camera IP tại {IP2}")
        return
        
    # Thiết lập kích thước khung hình cho camera để tăng FPS
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Counter để giới hạn tần suất ghi database
    frame_count = 0
    SAVE_INTERVAL = 10  # Ghi database mỗi 10 frame

    print(f"🎥 Đã kết nối camera {IP2}. Bắt đầu detect... Nhấn ESC để thoát.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Không đọc được khung hình từ camera")
            break

        frame_count += 1
        
        # Dự đoán
        results = model(frame, device=0, conf=0.3, imgsz=640, half=True, verbose=False)
        
        # Danh sách tọa độ để ghi vào database
        coords_to_save = []

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                label = model.names.get(cls_id, str(cls_id))

                # Bỏ qua các mốc (moc1, moc2, moc3, moc4)
                if label.lower() in {"moc1", "moc2", "moc3", "moc4"}:
                    continue
                
                # Camera 1 chỉ detect dog
                if label.lower() != "dog":
                    continue

                # Tính tọa độ tâm đáy (bottom center)
                cx = int((x1 + x2) / 2)
                cy = y2

                # Transform pixel center (cx,cy) -> project coordinates using homography
                try:
                    pt = np.array([[[float(cx), float(cy)]]], dtype=np.float32)
                    tpt = cv2.perspectiveTransform(pt, proj_matrix)
                    tx, ty = float(tpt[0, 0, 0]), float(tpt[0, 0, 1])
                    print(f"[{label}] Pixel: ({cx},{cy}) -> BIM: ({tx:.2f},{ty:.2f})")
                except Exception as e:
                    print(f"⚠️ Transform failed for point ({cx},{cy}): {e}")
                    tx, ty = float(cx), float(cy)

                # Kiểm tra tọa độ có nằm trong vùng BIM không
                inside_bim = is_inside_bim(tx, ty)
                
                # Màu sắc dựa trên vị trí: ĐỎ nếu trong vùng BIM, XANH DƯƠNG nếu ngoài
                if inside_bim:
                    box_color = (0, 0, 255)      # Đỏ - TRONG vùng BIM
                    text_color = (0, 0, 255)
                    status = "TRONG VUNG"
                    
                    # Thêm vào danh sách để ghi database (dog = person_id 1)
                    if len(coords_to_save) == 0:  # Chỉ lưu 1 dog
                        coords_to_save.append((tx, ty, 1))  # dog luôn là person_id = 1
                else:
                    box_color = (255, 150, 0)   # Xanh dương - NGOÀI vùng BIM
                    text_color = (255, 150, 0)
                    status = "NGOAI VUNG"

                # Vẽ bounding box (màu thay đổi theo vị trí)
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

                # Vẽ đường đáy
                cv2.line(frame, (x1, y2), (x2, y2), box_color, 3)

                # Vẽ điểm tại tâm đáy
                cv2.circle(frame, (cx, cy), 6, box_color, -1)
                
                # Hiển thị label và trạng thái
                text_status = f"{label} [{status}]"
                cv2.putText(frame, text_status, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 2)
                
                # Hiển thị tọa độ BIM chuyển đổi
                text_bim = f"BIM:({tx:.1f},{ty:.1f})"
                cv2.putText(frame, text_bim, (x1, y2 + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 2)
        
        # Ghi tọa độ vào database mỗi SAVE_INTERVAL frame
        if coords_to_save and frame_count % SAVE_INTERVAL == 0:
            try:
                add_many_temp(DB_PATH, coords_to_save)
                tx, ty, pid = coords_to_save[0]
                print(f"💾 DB: dog (ID=1): ({tx:.1f}, {ty:.1f})")
            except Exception as e:
                print(f"⚠️ Lỗi ghi database: {e}")

        cv2.imshow("YOLOv8 Live Detection", frame)

        # ESC để thoát
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    print("👋 Đã thoát.")


if __name__ == "__main__":
    main()
