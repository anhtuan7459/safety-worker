"""
Quay video từ 2 Camera riêng biệt để lấy ảnh label vật thể
- Camera 1: 192.168.66.15 → cam1_video.avi
- Camera 2: 192.168.66.14 → cam2_video.avi
- Nhấn 'S' để chụp ảnh từ cả 2 cam
- Nhấn 'Q' hoặc ESC để dừng
"""

import cv2
import os
import threading
from queue import Queue
from datetime import datetime

# Tạo folder output
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "output", "videos")
images_dir = os.path.join(script_dir, "output", "images")
os.makedirs(output_dir, exist_ok=True)
os.makedirs(images_dir, exist_ok=True)

# Thông tin camera
USER = "admin"
PASS = "12345678%40%40"

# Camera 1
IP1 = "192.168.66.15"
CAMERA_URL_1 = f"rtsp://{USER}:{PASS}@{IP1}:554/cam/realmonitor?channel=1&subtype=1"

# Camera 2
IP2 = "192.168.66.14"
CAMERA_URL_2 = f"rtsp://{USER}:{PASS}@{IP2}:554/cam/realmonitor?channel=1&subtype=1"

# Queues
frame_queue_1 = Queue(maxsize=2)
frame_queue_2 = Queue(maxsize=2)
stop_event = threading.Event()


class CameraRecorder(threading.Thread):
    """Thread để capture và ghi video từ camera"""
    def __init__(self, camera_id, camera_url, ip, frame_queue):
        super().__init__()
        self.camera_id = camera_id
        self.camera_url = camera_url
        self.ip = ip
        self.frame_queue = frame_queue
        self.daemon = True
        self.writer = None
        self.frame_count = 0
        
    def run(self):
        cap = cv2.VideoCapture(self.camera_url)
        if not cap.isOpened():
            print(f"[LỖI] Không thể kết nối Camera {self.camera_id} ({self.ip})")
            return
        
        # Lấy thông tin video
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        
        print(f"[OK] Camera {self.camera_id} đã kết nối: {width}x{height} @ {fps:.1f}fps")
        
        # Tạo file video output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_path = os.path.join(output_dir, f"cam{self.camera_id}_{timestamp}.avi")
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
        
        print(f"[RECORD] Camera {self.camera_id} → {video_path}")
        
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print(f"[LỖI] Mất kết nối Camera {self.camera_id}")
                break
            
            # Ghi video
            self.writer.write(frame)
            self.frame_count += 1
            
            # Đưa frame vào queue để hiển thị
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except:
                    pass
            self.frame_queue.put(frame.copy())
        
        # Cleanup
        cap.release()
        if self.writer:
            self.writer.release()
        print(f"[DONE] Camera {self.camera_id}: Đã ghi {self.frame_count} frames")


def main():
    print("=" * 60)
    print("      QUAY VIDEO 2 CAMERA ĐỂ LABEL VẬT THỂ")
    print("=" * 60)
    print(f"📹 Camera 1: {IP1}")
    print(f"📹 Camera 2: {IP2}")
    print("-" * 60)
    print("📁 Video lưu tại: output/videos/")
    print("📁 Ảnh chụp lưu tại: output/images/")
    print("-" * 60)
    print("⌨️  Phím tắt:")
    print("    S - Chụp ảnh từ cả 2 camera")
    print("    Q/ESC - Dừng quay")
    print("=" * 60)
    
    # Khởi tạo recorder threads
    recorder_1 = CameraRecorder(1, CAMERA_URL_1, IP1, frame_queue_1)
    recorder_2 = CameraRecorder(2, CAMERA_URL_2, IP2, frame_queue_2)
    
    # Start threads
    recorder_1.start()
    recorder_2.start()
    
    print("\n[INFO] Đang quay video... Nhấn Q hoặc ESC để dừng.\n")
    
    # Counter cho ảnh chụp
    snapshot_count = 0
    
    while True:
        frame1 = None
        frame2 = None
        
        # Lấy frame từ queue
        try:
            frame1 = frame_queue_1.get_nowait()
        except:
            pass
        
        try:
            frame2 = frame_queue_2.get_nowait()
        except:
            pass
        
        # Hiển thị Camera 1
        if frame1 is not None:
            display1 = frame1.copy()
            # Thêm overlay
            cv2.putText(display1, f"CAM 1 - {IP1}", (10, 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(display1, "RECORDING", (10, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.circle(display1, (display1.shape[1] - 20, 20), 8, (0, 0, 255), -1)
            cv2.imshow("Camera 1", display1)
        
        # Hiển thị Camera 2
        if frame2 is not None:
            display2 = frame2.copy()
            cv2.putText(display2, f"CAM 2 - {IP2}", (10, 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(display2, "RECORDING", (10, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.circle(display2, (display2.shape[1] - 20, 20), 8, (0, 0, 255), -1)
            cv2.imshow("Camera 2", display2)
        
        # Xử lý phím
        key = cv2.waitKey(1) & 0xFF
        
        # S - Chụp ảnh
        if key == ord('s') or key == ord('S'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_count += 1
            
            if frame1 is not None:
                img_path1 = os.path.join(images_dir, f"cam1_{timestamp}_{snapshot_count:04d}.jpg")
                cv2.imwrite(img_path1, frame1)
                print(f"📸 Chụp Camera 1: {img_path1}")
            
            if frame2 is not None:
                img_path2 = os.path.join(images_dir, f"cam2_{timestamp}_{snapshot_count:04d}.jpg")
                cv2.imwrite(img_path2, frame2)
                print(f"📸 Chụp Camera 2: {img_path2}")
        
        # Q hoặc ESC - Dừng
        if key == ord('q') or key == ord('Q') or key == 27:
            break
    
    # Cleanup
    print("\n[INFO] Đang dừng quay...")
    stop_event.set()
    recorder_1.join(timeout=3)
    recorder_2.join(timeout=3)
    cv2.destroyAllWindows()
    
    print("\n" + "=" * 60)
    print("✅ ĐÃ DỪNG QUAY VIDEO")
    print(f"📁 Video: {output_dir}")
    print(f"📁 Ảnh:   {images_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()


