import cv2
import numpy as np
import threading
from queue import Queue

# Thông tin camera 1
IP1 = "192.168.66.14"
# Thông tin camera 2
IP2 = "192.168.66.15"

USER = "admin"
PASS = "12345678%40%40"

# Đường dẫn RTSP
camera_url1 = f"rtsp://{USER}:{PASS}@{IP1}:554/cam/realmonitor?channel=1&subtype=1"
camera_url2 = f"rtsp://{USER}:{PASS}@{IP2}:554/cam/realmonitor?channel=1&subtype=1"

# Queue để lưu frame từ mỗi camera
frame_queue1 = Queue(maxsize=1)
frame_queue2 = Queue(maxsize=1)
stop_event = threading.Event()

def capture_camera(camera_url, queue, camera_name):
    """Chạy trong luồng riêng để capture frame từ camera"""
    cap = cv2.VideoCapture(camera_url)
    
    if not cap.isOpened():
        print(f"LỖI: Không thể kết nối tới {camera_name}.")
        return
    
    print(f"{camera_name} đã kết nối.")
    
    while not stop_event.is_set():
        ret, frame = cap.read()
        
        if not ret:
            print(f"LỖI: Mất kết nối {camera_name}.")
            break
        
        # Lưu frame vào queue, bỏ frame cũ nếu queue đầy
        if not queue.full():
            queue.put(frame)
        else:
            try:
                queue.get_nowait()
                queue.put(frame)
            except:
                pass
    
    cap.release()

def main():
    # Tạo 2 luồng capture camera
    thread1 = threading.Thread(target=capture_camera, 
                              args=(camera_url1, frame_queue1, "Camera 1"))
    thread2 = threading.Thread(target=capture_camera, 
                              args=(camera_url2, frame_queue2, "Camera 2"))
    
    thread1.daemon = True
    thread2.daemon = True
    thread1.start()
    thread2.start()
    
    print("Đang mở 2 Camera đồng thời... Nhấn phím 'Q' để thoát.")
    
    while True:
        try:
            frame1 = frame_queue1.get(timeout=1)
            frame2 = frame_queue2.get(timeout=1)
            
            # Lấy kích thước của frame
            height1, width1 = frame1.shape[:2]
            height2, width2 = frame2.shape[:2]
            
            # Resize frame 2 để có cùng độ rộng với frame 1
            frame2_resized = cv2.resize(frame2, (width1, int(width1 * height2 / width2)))
            
            # Xếp chồng frame 1 lên trên, frame 2 dưới
            combined = np.vstack([frame1, frame2_resized])
            
            # Thêm nhãn cho mỗi camera
            cv2.putText(combined, f"Camera 1 ({IP1})", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(combined, f"Camera 2 ({IP2})", (10, height1 + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Hiển thị tọa độ mốc hiện tại
            y_offset = 60
            for moc_name, coords in moc_coords.items():
                if coords['x'] is not None:
                    text = f"{moc_name}: ({coords['x']},{coords['y']}) - {coords['cam']}"
                    cv2.putText(combined, text, (10, y_offset),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
                    y_offset += 25
            
            # Hiển thị video
            cv2.imshow("Dahua Dual Camera View", combined)
            
            # Nhấn phím 'q' để đóng
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        except:
            continue
    
    # Dừng các luồng
    stop_event.set()
    thread1.join(timeout=2)
    thread2.join(timeout=2)
    cv2.destroyAllWindows()
    print("Đã thoát.")

if __name__ == "__main__":
    main()
