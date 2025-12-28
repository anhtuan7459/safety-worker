# TÀI LIỆU CHI TIẾT VỀ HỆ THỐNG DUAL CAMERA DETECTION

## MỤC LỤC
1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Chuyển đổi tọa độ chi tiết](#3-chuyển-đổi-tọa-độ-chi-tiết)
4. [Luồng xử lý dữ liệu](#4-luồng-xử-lý-dữ-liệu)
5. [Các module và chức năng](#5-các-module-và-chức-năng)
6. [Câu hỏi thường gặp](#6-câu-hỏi-thường-gặp)

---

## 1. TỔNG QUAN HỆ THỐNG

### 1.1. Mục đích hệ thống
Hệ thống sử dụng 2 camera IP để:
- Phát hiện đối tượng (dog và songoku) bằng YOLO
- Chuyển đổi tọa độ từ pixel sang hệ tọa độ BIM/Revit
- Giám sát vị trí đối tượng trong vùng BIM quy định
- Điều khiển đèn cảnh báo qua Modbus RS485 khi đối tượng ra ngoài vùng
- Lưu tọa độ vào database SQLite

### 1.2. Thông số kỹ thuật
- **Camera 1:** IP 192.168.66.15, RTSP, 640×480, detect "dog"
- **Camera 2:** IP 192.168.66.14, RTSP, 640×480, detect "songoku"
- **Model YOLO:** best.pt, confidence=0.3, imgsz=640
- **Database:** SQLite, file `output/data.db`
- **Modbus:** RS485, RTU protocol, 9600 baud

---

## 2. KIẾN TRÚC HỆ THỐNG

### 2.1. Kiến trúc đa luồng (Multi-threading)

```
┌─────────────────────────────────────────────────────────┐
│                    MAIN THREAD                          │
│  - Hiển thị video                                       │
│  - Ghi database                                         │
│  - Xử lý phím ESC                                       │
└─────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Camera Thread 1 │  │ Camera Thread 2  │  │ Detection Thread│
│                 │  │                 │  │                 │
│ - Đọc RTSP      │  │ - Đọc RTSP      │  │ - YOLO detect   │
│ - Put vào Queue │  │ - Put vào Queue │  │ - Transform BIM │
│                 │  │                 │  │ - Put vào Queue │
└─────────────────┘  └─────────────────┘  └─────────────────┘
           │                    │                    │
           └────────────────────┴────────────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │   Queues     │
                   │ - frame_q_1  │
                   │ - frame_q_2  │
                   │ - result_q   │
                   └──────────────┘
```

### 2.2. Cấu trúc Queue

**Frame Queue (maxsize=2):**
- Lưu frame mới nhất từ camera
- Nếu đầy → Bỏ frame cũ, giữ frame mới
- Format: `(camera_id, frame)`

**Result Queue (maxsize=10):**
- Lưu kết quả detection đã xử lý
- Format: `(camera_id, frame, detections)`

**Stop Event:**
- `threading.Event()` để đồng bộ dừng tất cả threads
- Khi nhấn ESC → `stop_event.set()` → Tất cả threads dừng

---

## 3. CHUYỂN ĐỔI TỌA ĐỘ CHI TIẾT

### 3.1. Các hệ tọa độ trong hệ thống

**1. Hệ tọa độ Pixel (Camera):**
- Gốc (0,0) ở góc trên bên trái
- X tăng sang phải, Y tăng xuống dưới
- Độ phân giải: 640×480 pixels

**2. Hệ tọa độ BIM/Revit:**
- Hệ tọa độ thực tế trong không gian xây dựng
- E (East) = X, N (North) = Y
- Vùng giám sát: X=[32, 70], Y=[-5, 27]

**3. Điểm chuẩn calibration:**
- **Top-Left:** (70, 27) - Xa camera, bên Trái
- **Bottom-Left:** (32, 27) - Gần camera, bên Trái
- **Top-Right:** (70, -5) - Xa camera, bên Phải
- **Bottom-Right:** (32, -5) - Gần camera, bên Phải

### 3.2. Quá trình calibration

**Bước 1: Chọn 4 điểm trên frame camera**
- Người dùng click chuột chọn 4 góc của mặt phẳng làm việc
- Thứ tự: Top-Left → Bottom-Left → Top-Right → Bottom-Right

**Bước 2: Tính ma trận Homography**
```python
# 4 điểm pixel
pts1 = np.float32([
    top_left_point,      # (px1, py1)
    bottom_left_point,   # (px2, py2)
    top_right_point,     # (px3, py3)
    bottom_right_point   # (px4, py4)
])

# 4 điểm BIM tương ứng
pts2 = np.float32([
    (70, 27),   # Top-Left BIM
    (32, 27),   # Bottom-Left BIM
    (70, -5),   # Top-Right BIM
    (32, -5)    # Bottom-Right BIM
])

# Tính ma trận homography 3×3
matrix = cv2.getPerspectiveTransform(pts1, pts2)
```

**Bước 3: Lưu ma trận**
- Camera 1: `config/chuyendoitoado.py` → `get_projection_matrix()`
- Camera 2: `config/chuyendoitoado_cam2.py` → `get_projection_matrix_cam2()`

### 3.3. Chuyển đổi Pixel → BIM

#### **Camera 1 (Đơn giản):**

```python
def pixel_to_bim_cam1(px, py):
    # 1. Tạo điểm pixel dạng numpy array
    pt = np.array([[[float(px), float(py)]]], dtype=np.float32)
    
    # 2. Áp dụng perspectiveTransform
    tpt = cv2.perspectiveTransform(pt, matrix1)
    
    # 3. Lấy tọa độ BIM
    tx, ty = float(tpt[0, 0, 0]), float(tpt[0, 0, 1])
    
    return tx, ty
```

**Ví dụ:**
- Pixel (300, 200) → BIM (50.5, 12.3)

#### **Camera 2 (Phức tạp - Camera vuông góc):**

Camera 2 đặt vuông góc với Camera 1, nên cần các phép biến đổi bổ sung:

```python
def pixel_to_bim_cam2(px, py):
    # 1. Tạo điểm pixel
    pt = np.array([[[float(px), float(py)]]], dtype=np.float32)
    
    # 2. Áp dụng perspectiveTransform
    tpt = cv2.perspectiveTransform(pt, matrix2)
    tx, ty = float(tpt[0, 0, 0]), float(tpt[0, 0, 1])
    
    # 3. HOÁN ĐỔI X và Y (vì camera vuông góc)
    tx, ty = ty, tx
    
    # 4. REMAP tọa độ X: từ range (-5, 27) sang range (32, 70)
    #    Công thức: new_x = (old_x - min_old) / range_old * range_new + min_new
    tx = (tx - (-5)) / 32.0 * 38.0 + 32
    #    Giải thích: 
    #    - Range cũ: 27 - (-5) = 32
    #    - Range mới: 70 - 32 = 38
    #    - tx từ -5→27 được map sang 32→70
    
    # 5. REMAP tọa độ Y: từ range (32, 70) sang range (-5, 27)
    ty = (ty - 32) / 38.0 * 32.0 + (-5)
    #    Giải thích:
    #    - Range cũ: 70 - 32 = 38
    #    - Range mới: 27 - (-5) = 32
    #    - ty từ 32→70 được map sang -5→27
    
    # 6. ĐẢO NGƯỢC trục Y
    ty = 22 - ty  # 22 = -5 + 27
    #    Giải thích: Đảo ngược để gần camera → xa trong BIM
    
    return tx, ty
```

**Tại sao cần các phép biến đổi này?**

1. **Hoán đổi X↔Y:** Camera 2 đặt vuông góc với Camera 1, nên trục X/Y của camera 2 tương ứng với Y/X trong BIM

2. **Remap:** Sau khi hoán đổi, tọa độ không khớp với vùng BIM thực tế, cần scale và dịch chuyển

3. **Đảo Y:** Do hướng camera ngược lại, cần đảo trục Y để đúng với hệ BIM

**Ví dụ cụ thể:**
```
Pixel (400, 250) trong Camera 2:
  → Sau perspectiveTransform: (15.2, 45.8)
  → Sau swap: (45.8, 15.2)
  → Sau remap X: (45.8 - (-5)) / 32 * 38 + 32 = 50.8 + 32 = 82.8 → Clamp về 70
  → Sau remap Y: (15.2 - 32) / 38 * 32 + (-5) = -14.1 + (-5) = -19.1 → Clamp về -5
  → Sau đảo Y: 22 - (-5) = 27
  → Kết quả BIM: (70, 27) - Top-Left
```

### 3.4. Tính tọa độ tâm đáy đối tượng

**Tại sao dùng tâm đáy?**
- Tâm đáy (bottom center) đại diện cho vị trí tiếp xúc với mặt đất
- Chính xác hơn tâm bounding box trong việc xác định vị trí thực tế

**Công thức:**
```python
# Bounding box: (x1, y1) - góc trên trái, (x2, y2) - góc dưới phải
x1, y1, x2, y2 = box.xyxy[0]

# Tâm đáy
cx = int((x1 + x2) / 2)  # X trung bình
cy = y2                   # Y của cạnh đáy
```

**Ví dụ:**
- Bounding box: (100, 50, 200, 300)
- Tâm đáy: cx = (100+200)/2 = 150, cy = 300

---

## 4. LUỒNG XỬ LÝ DỮ LIỆU

### 4.1. Luồng chính (Main Flow)

```
START
  │
  ├─> Load YOLO model (best.pt)
  ├─> Load Homography matrices (Camera 1 & 2)
  ├─> Đọc vùng BIM bounds từ config
  ├─> Khởi tạo Database SQLite
  ├─> Khởi tạo Modbus RS485
  │
  ├─> Start Camera Thread 1 ──┐
  ├─> Start Camera Thread 2 ──┤
  └─> Start Detection Thread ──┤
                                │
                                ▼
                         MAIN LOOP
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
        ▼                                               ▼
  Get frame from Queue                            Process frame
        │                                               │
        ▼                                               ▼
  Display on OpenCV                            YOLO Detection
        │                                               │
        ▼                                               ▼
  Check ESC key                              Transform to BIM
        │                                               │
        └───────────────────────┬───────────────────────┘
                                │
                                ▼
                        Check inside BIM?
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
              INSIDE BIM              OUTSIDE BIM
                    │                       │
                    ▼                       ▼
            signal_inside()         signal_outside()
                    │                       │
                    ▼                       ▼
            TẮT đèn Modbus          BẬT đèn Modbus
                    │                       │
                    └───────────┬───────────┘
                                │
                                ▼
                        Save to Database
                        (mỗi 10 frames)
                                │
                                ▼
                            Continue Loop
                                │
                                ▼
                            ESC pressed?
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    NO                      YES
                    │                       │
                    └───────────┐           │
                                │           │
                                └───────────┘
                                    │
                                    ▼
                            signal_stop()
                                    │
                                    ▼
                            Close Modbus
                                    │
                                    ▼
                            Stop all threads
                                    │
                                    ▼
                                    END
```

### 4.2. Luồng Camera Thread

```
Camera Thread Start
  │
  ├─> Connect RTSP: rtsp://admin:pass@IP:554/...
  ├─> Set resolution: 640×480
  │
  └─> LOOP:
        │
        ├─> cap.read() → frame
        │
        ├─> Check queue full?
        │   ├─> YES → Remove old frame
        │   └─> NO → Continue
        │
        ├─> Put (camera_id, frame) vào queue
        │
        └─> Check stop_event?
            ├─> SET → Break loop
            └─> NOT SET → Continue
```

### 4.3. Luồng Detection Thread

```
Detection Thread Start
  │
  └─> LOOP:
        │
        ├─> Get frame from Camera 1 Queue
        │   └─> Process frame
        │       ├─> YOLO detection
        │       ├─> Filter label (dog/songoku)
        │       ├─> Calculate bottom center
        │       ├─> Transform to BIM
        │       └─> Check inside BIM
        │
        ├─> Get frame from Camera 2 Queue
        │   └─> Process frame (tương tự)
        │
        ├─> Put results vào Result Queue
        │
        └─> Check stop_event?
            ├─> SET → Break loop
            └─> NOT SET → Continue
```

### 4.4. Luồng xử lý Modbus

```
Detection → signal_inside/outside
  │
  ├─> Check last_region_state[label]
  │
  ├─> State changed?
  │   ├─> YES → Send Modbus command
  │   │   ├─> INSIDE → write_coil(0, False) → TẮT đèn
  │   │   └─> OUTSIDE → write_coil(0, True) → BẬT đèn
  │   │
  │   └─> NO → Skip (tiết kiệm tài nguyên)
  │
  └─> Update last_region_state[label]
```

---

## 5. CÁC MODULE VÀ CHỨC NĂNG

### 5.1. run_dual_cam.py - Module chính

**Chức năng:**
- Điều phối toàn bộ hệ thống detection
- Quản lý threads và queues
- Xử lý detection và chuyển đổi tọa độ
- Ghi database và điều khiển Modbus

**Các class chính:**

**CameraThread:**
- Kế thừa `threading.Thread`
- Đọc frame từ RTSP camera
- Đưa frame vào queue

**DetectionThread:**
- Kế thừa `threading.Thread`
- Xử lý YOLO detection
- Chuyển đổi tọa độ pixel → BIM
- Kiểm tra trong/ngoài vùng BIM

**Các hàm quan trọng:**

`pixel_to_bim(px, py, camera_id)`:
- Chuyển pixel sang BIM
- Xử lý đặc biệt cho Camera 2

`is_inside_bim(x, y)`:
- Kiểm tra tọa độ có trong vùng BIM không
- `x_min ≤ x ≤ x_max` và `y_min ≤ y ≤ y_max`

`get_bim_bounds()`:
- Đọc vùng BIM từ file config
- Parse bằng regex để lấy 4 điểm góc
- Tính min/max X và Y

### 5.2. setup_calibration.py - Module calibration

**Chức năng:**
- Hiệu chỉnh camera để tính ma trận homography
- Cho phép người dùng chọn 4 điểm calibration
- Lưu ma trận vào file config

**Class CalibrationSetup:**

**mouse_callback():**
- Xử lý click chuột để chọn điểm
- Kiểm tra click vào nút SAVE/HỦY

**save_to_file():**
- Tính ma trận homography từ 4 điểm
- Ghi vào file Python config
- Tính toán và in 4 điểm trong hệ BIM

**run():**
- Vòng lặp chính hiển thị camera
- Xử lý click và phím

### 5.3. signal_output.py - Module tín hiệu và Modbus

**Chức năng:**
- Gửi tín hiệu ra console
- Điều khiển Modbus RS485
- Quản lý trạng thái đối tượng

**Các hàm quan trọng:**

`init_modbus()`:
- Đọc config từ JSON
- Kết nối ModbusSerialClient
- Kiểm tra `enabled` flag

`send_signal(signal_type, **kwargs)`:
- Xử lý các loại tín hiệu:
  - `DETECT_INSIDE`: Vật vào vùng → TẮT đèn
  - `DETECT_OUTSIDE`: Vật ra ngoài → BẬT đèn
  - `SYSTEM_READY`: Test đèn nhấp nháy
  - `SYSTEM_STOP`: Tắt tất cả đèn

`get_outside_direction(x, y, bim_bounds)`:
- Tính hướng vật ra ngoài
- TRAI/PHAI/TREN/DUOI hoặc kết hợp

**Logic tối ưu:**
- Lưu `last_region_state` cho mỗi label
- Chỉ gửi Modbus khi trạng thái thay đổi
- Giảm tải giao tiếp

### 5.4. db_manage.py - Module database

**Chức năng:**
- Quản lý database SQLite
- Lưu tọa độ đối tượng

**Bảng temp_data:**
```sql
CREATE TABLE temp_data (
    person_ID INTEGER PRIMARY KEY,
    x_location INTEGER,
    y_location INTEGER
)
```

**person_ID:**
- 0 = songoku (Camera 2)
- 1 = dog (Camera 1)

**Các hàm:**

`create_temp_table(db_path)`:
- Tạo bảng nếu chưa có
- Khởi tạo 2 rows với person_ID 0 và 1

`add_many_temp(db_path, data_list)`:
- Insert hoặc Replace (UPSERT) theo person_ID
- Validate và filter dữ liệu
- Chỉ chấp nhận person_ID 0 hoặc 1

### 5.5. gui/main_app.py - Module giao diện

**Chức năng:**
- Giao diện điều khiển hệ thống
- Quản lý Modbus từ GUI
- Khởi chạy các script

**Các tab:**

**Tab Điều khiển:**
- Nút FULL SYSTEM, DETECTION, CALIBRATION, RECORDING
- Nút mở Output folder, Database

**Tab Modbus RS485:**
- Chọn COM port, baudrate
- Kết nối/Ngắt Modbus
- Điều khiển đèn thủ công
- Log Modbus

**Logic đặc biệt:**
- Khi chạy Detection từ GUI → Tự động ngắt Modbus GUI
- Giữ `enabled=true` trong config để Detection tự kết nối
- Tránh xung đột cổng COM

---

## 6. CÂU HỎI THƯỜNG GẶP

### Q1: Tại sao cần 2 camera?

**Trả lời:**
- Camera 1: Phát hiện "dog" (person_id=1)
- Camera 2: Phát hiện "songoku" (person_id=0)
- Mỗi camera có góc nhìn khác nhau, tăng độ bao phủ
- Camera 2 đặt vuông góc với Camera 1 để có góc nhìn đa chiều

### Q2: Tại sao Camera 2 cần các phép biến đổi phức tạp?

**Trả lời:**
- Camera 2 đặt **vuông góc** với Camera 1
- Trục X/Y của Camera 2 tương ứng với Y/X trong BIM
- Cần **hoán đổi** X↔Y
- Sau hoán đổi, tọa độ không khớp → Cần **remap** để scale và dịch chuyển
- Hướng camera ngược → Cần **đảo Y** để đúng với hệ BIM

**Ví dụ:**
```
Camera 2 nhìn từ góc vuông góc:
  - Trục X camera = Trục Y BIM
  - Trục Y camera = Trục X BIM
  → Cần swap và remap
```

### Q3: Tại sao dùng tâm đáy thay vì tâm bounding box?

**Trả lời:**
- **Tâm đáy** đại diện cho vị trí tiếp xúc với mặt đất
- Chính xác hơn trong việc xác định vị trí thực tế của đối tượng
- Tâm bounding box có thể ở giữa không trung nếu đối tượng cao

**Công thức:**
```python
cx = (x1 + x2) / 2  # Tâm theo X
cy = y2              # Cạnh đáy (không phải (y1+y2)/2)
```

### Q4: Ma trận Homography là gì?

**Trả lời:**
- Ma trận 3×3 để chuyển đổi từ hệ tọa độ này sang hệ tọa độ khác
- Sử dụng **phép chiếu đồng nhất** (homogeneous transformation)
- Cần tối thiểu 4 điểm tương ứng để tính ma trận

**Công thức:**
```
[x']   [h11 h12 h13] [x]
[y'] = [h21 h22 h23] [y]
[w']   [h31 h32 h33] [1]

x_final = x'/w'
y_final = y'/w'
```

**Trong OpenCV:**
```python
matrix = cv2.getPerspectiveTransform(pts1, pts2)
# pts1: 4 điểm pixel
# pts2: 4 điểm BIM tương ứng
```

### Q5: Tại sao chỉ gửi Modbus khi trạng thái thay đổi?

**Trả lời:**
- **Tối ưu hóa tài nguyên:** Giảm số lượng lệnh gửi đi
- **Giảm tải giao tiếp:** Không spam Modbus với lệnh giống nhau
- **Logic đúng:** Chỉ cần cảnh báo khi có sự thay đổi

**Cơ chế:**
```python
last_region_state = {
    "dog": "INSIDE",      # Trạng thái hiện tại
    "songoku": "OUTSIDE"
}

# Khi detection:
if prev_state != current_state:
    send_modbus_command()  # Chỉ gửi khi thay đổi
```

### Q6: Queue có kích thước bao nhiêu? Tại sao?

**Trả lời:**
- **Frame Queue:** maxsize=2
  - Chỉ cần frame mới nhất
  - Bỏ frame cũ nếu queue đầy
  - Giảm độ trễ

- **Result Queue:** maxsize=10
  - Lưu nhiều kết quả hơn để xử lý
  - Tránh mất dữ liệu khi xử lý chậm

### Q7: Tại sao dùng threading thay vì multiprocessing?

**Trả lời:**
- **Threading:** Chia sẻ bộ nhớ, phù hợp với Queue và shared data
- **Multiprocessing:** Tốn tài nguyên hơn, khó chia sẻ frame (phải serialize)
- Camera I/O và detection có thể chạy song song với threading

### Q8: Database lưu gì? Tại sao dùng UPSERT?

**Trả lời:**
- Lưu tọa độ mới nhất của mỗi đối tượng
- **UPSERT (INSERT OR REPLACE):**
  - Mỗi person_ID chỉ có 1 row
  - Update tọa độ mới nhất
  - Không tạo nhiều rows cho cùng 1 đối tượng

**Ví dụ:**
```
person_ID=0 (songoku): (45.2, 12.3)
person_ID=1 (dog): (50.1, 15.7)
→ Chỉ 2 rows, luôn cập nhật tọa độ mới nhất
```

### Q9: Làm sao xác định vật ở ngoài vùng theo hướng nào?

**Trả lời:**
```python
def get_outside_direction(x, y, bim_bounds):
    x_min, x_max, y_min, y_max = bim_bounds
    
    if x < x_min: → TRAI
    if x > x_max: → PHAI
    if y < y_min: → DUOI
    if y > y_max: → TREN
    
    # Có thể kết hợp: TRAI_TREN, PHAI_DUOI, etc.
```

### Q10: Tại sao Camera 2 cần remap tọa độ?

**Trả lời:**
- Sau khi hoán đổi X↔Y, tọa độ không khớp với vùng BIM thực tế
- Cần scale và dịch chuyển để map đúng

**Ví dụ:**
```
Sau swap: tx trong range (-5, 27)
Cần map sang: (32, 70)
→ Công thức remap: new = (old - min_old) / range_old * range_new + min_new
```

### Q11: Làm sao hệ thống biết đối tượng nào thuộc camera nào?

**Trả lời:**
- **Filter theo label:**
  - Camera 1: Chỉ giữ detection có label="dog"
  - Camera 2: Chỉ giữ detection có label="songoku"
- **person_ID:**
  - dog → person_id=1
  - songoku → person_id=0

### Q12: Tại sao dùng YOLO thay vì các mô hình khác?

**Trả lời:**
- **YOLO:** Real-time detection, tốc độ cao
- **Tối ưu:** Có thể chạy trên GPU với half precision (FP16)
- **Độ chính xác:** Đủ tốt với confidence=0.3
- **Dễ tích hợp:** Ultralytics YOLO có API đơn giản

### Q13: Làm sao đảm bảo 2 camera mapping về cùng hệ BIM?

**Trả lời:**
- Cả 2 camera dùng **cùng 4 điểm BIM** khi calibration:
  - Top-Left: (70, 27)
  - Bottom-Left: (32, 27)
  - Top-Right: (70, -5)
  - Bottom-Right: (32, -5)
- Sau đó Camera 2 được transform thêm để khớp với Camera 1

### Q14: Tại sao lưu database mỗi 10 frames?

**Trả lời:**
- **Giảm I/O:** Không ghi database mỗi frame (tốn tài nguyên)
- **Đủ nhanh:** 10 frames ≈ 0.4 giây (với 25fps)
- **Cân bằng:** Giữa độ chính xác và hiệu suất

### Q15: Làm sao xử lý khi mất kết nối camera?

**Trả lời:**
- **Camera Thread:** Kiểm tra `cap.read()` → Nếu `ret=False` → Log lỗi và break loop
- **Detection Thread:** Queue timeout 0.1s → Nếu không có frame → Skip và tiếp tục
- **Main Thread:** Kiểm tra `latest_frames[camera_id] is None` → Không hiển thị

---

## KẾT LUẬN

Tài liệu này cung cấp kiến thức chi tiết về:
- Kiến trúc và luồng xử lý của hệ thống
- Chuyển đổi tọa độ giữa các hệ
- Cách thức hoạt động của từng module
- Câu hỏi thường gặp và cách trả lời

**Lưu ý quan trọng:**
- Luôn nhớ Camera 2 cần các phép biến đổi đặc biệt do đặt vuông góc
- Modbus chỉ gửi khi trạng thái thay đổi để tối ưu
- Database dùng UPSERT để chỉ lưu tọa độ mới nhất
- Queue nhỏ để giảm độ trễ, chỉ giữ frame mới nhất

**Khi thầy hỏi:**
1. Giải thích rõ về chuyển đổi tọa độ Camera 2
2. Nêu lý do dùng threading và queue
3. Giải thích logic Modbus chỉ gửi khi thay đổi
4. Mô tả luồng xử lý từ camera → detection → BIM → Modbus

