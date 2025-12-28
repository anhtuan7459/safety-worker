# TÓM TẮT TRẢ LỜI THẦY - CÁC ĐIỂM QUAN TRỌNG

## 1. CHUYỂN ĐỔI TỌA ĐỘ CAMERA 2 (QUAN TRỌNG NHẤT!)

### Câu hỏi: "Tại sao Camera 2 cần nhiều phép biến đổi?"

**Trả lời:**
Camera 2 đặt **vuông góc** với Camera 1, nên:

1. **Hoán đổi X↔Y:** 
   - Trục X camera = Trục Y BIM
   - Trục Y camera = Trục X BIM
   - → Cần swap: `tx, ty = ty, tx`

2. **Remap tọa độ:**
   - Sau swap, tọa độ không khớp với vùng BIM thực tế
   - Remap X: từ (-5, 27) sang (32, 70)
   - Remap Y: từ (32, 70) sang (-5, 27)
   - → Công thức: `new = (old - min_old) / range_old * range_new + min_new`

3. **Đảo Y:**
   - Hướng camera ngược → Cần đảo: `ty = 22 - ty`

**Ví dụ nhanh:**
```
Pixel (400, 250) Camera 2:
  → Transform: (15.2, 45.8)
  → Swap: (45.8, 15.2)
  → Remap X: 82.8 → Clamp 70
  → Remap Y: -19.1 → Clamp -5
  → Đảo Y: 27
  → Kết quả: (70, 27) - Top-Left BIM
```

---

## 2. MA TRẬN HOMOGRAPHY

### Câu hỏi: "Ma trận homography là gì? Tính như thế nào?"

**Trả lời:**
- Ma trận 3×3 để chuyển đổi từ hệ pixel sang hệ BIM
- Cần **4 điểm tương ứng** để tính
- Dùng `cv2.getPerspectiveTransform(pts1, pts2)`

**Công thức:**
```python
pts1 = [4 điểm pixel]      # Từ camera
pts2 = [4 điểm BIM]         # Tọa độ thực tế
matrix = cv2.getPerspectiveTransform(pts1, pts2)
```

**Áp dụng:**
```python
pt = np.array([[[px, py]]], dtype=np.float32)
tpt = cv2.perspectiveTransform(pt, matrix)
tx, ty = tpt[0, 0, 0], tpt[0, 0, 1]
```

---

## 3. TẠI SAO DÙNG TÂM ĐÁY?

### Câu hỏi: "Tại sao không dùng tâm bounding box?"

**Trả lời:**
- **Tâm đáy** đại diện vị trí tiếp xúc với mặt đất → Chính xác hơn
- Tâm bounding box có thể ở giữa không trung nếu đối tượng cao

**Công thức:**
```python
cx = (x1 + x2) / 2  # Tâm theo X
cy = y2              # Cạnh đáy (không phải (y1+y2)/2)
```

---

## 4. KIẾN TRÚC ĐA LUỒNG

### Câu hỏi: "Tại sao dùng threading? Queue có tác dụng gì?"

**Trả lời:**

**Threading:**
- **Camera Thread:** Đọc frame từ RTSP (I/O blocking)
- **Detection Thread:** Xử lý YOLO (CPU/GPU intensive)
- **Main Thread:** Hiển thị và ghi database
- → Chạy song song, không block lẫn nhau

**Queue:**
- **Frame Queue (maxsize=2):** Lưu frame mới nhất từ camera
- **Result Queue (maxsize=10):** Lưu kết quả detection
- → Truyền dữ liệu giữa các threads an toàn

**Stop Event:**
- `threading.Event()` để đồng bộ dừng tất cả threads
- Khi ESC → `stop_event.set()` → Tất cả threads dừng

---

## 5. LOGIC MODBUS TỐI ƯU

### Câu hỏi: "Tại sao chỉ gửi Modbus khi trạng thái thay đổi?"

**Trả lời:**
- **Tối ưu tài nguyên:** Giảm số lượng lệnh gửi đi
- **Giảm tải giao tiếp:** Không spam Modbus
- **Logic đúng:** Chỉ cần cảnh báo khi có thay đổi

**Cơ chế:**
```python
last_region_state = {"dog": "INSIDE", "songoku": "OUTSIDE"}

# Khi detection:
if prev_state != current_state:
    send_modbus_command()  # Chỉ gửi khi thay đổi
else:
    skip()  # Không gửi nếu giữ nguyên trạng thái
```

**Ví dụ:**
- Dog đang NGOÀI → Vẫn NGOÀI → Không gửi lệnh
- Dog từ NGOÀI → TRONG → Gửi lệnh TẮT đèn
- Dog từ TRONG → NGOÀI → Gửi lệnh BẬT đèn

---

## 6. DATABASE UPSERT

### Câu hỏi: "Tại sao dùng INSERT OR REPLACE?"

**Trả lời:**
- Mỗi đối tượng chỉ có **1 row** trong database
- Luôn cập nhật tọa độ **mới nhất**
- Không tạo nhiều rows cho cùng 1 đối tượng

**Cấu trúc:**
```sql
person_ID (PRIMARY KEY) | x_location | y_location
0 (songoku)            | 45.2       | 12.3
1 (dog)                | 50.1       | 15.7
```

**Logic:**
- person_ID=0 → songoku (Camera 2)
- person_ID=1 → dog (Camera 1)
- Mỗi lần lưu → UPDATE row cũ thay vì INSERT mới

---

## 7. LUỒNG XỬ LÝ TỔNG QUAN

### Câu hỏi: "Mô tả luồng xử lý từ đầu đến cuối?"

**Trả lời ngắn gọn:**

```
1. Camera Thread → Đọc frame RTSP → Put vào Queue
2. Detection Thread → Lấy frame từ Queue → YOLO detect
3. Tính tâm đáy → Transform pixel → BIM
4. Check inside BIM?
   - INSIDE → signal_inside() → TẮT đèn (nếu thay đổi)
   - OUTSIDE → signal_outside() → BẮT đèn (nếu thay đổi)
5. Mỗi 10 frames → Save to Database (UPSERT)
6. Main Thread → Hiển thị video với bounding box và tọa độ BIM
```

---

## 8. TẠI SAO 2 CAMERA?

### Câu hỏi: "Tại sao cần 2 camera?"

**Trả lời:**
- **Camera 1:** Detect "dog" (person_id=1)
- **Camera 2:** Detect "songoku" (person_id=0)
- **Góc nhìn khác nhau:** Camera 2 vuông góc với Camera 1
- **Tăng độ bao phủ:** Phát hiện đối tượng từ nhiều góc
- **Mapping về cùng hệ BIM:** Cả 2 camera đều chuyển về cùng hệ tọa độ

---

## 9. CALIBRATION PROCESS

### Câu hỏi: "Quá trình calibration như thế nào?"

**Trả lời:**

1. **Người dùng chọn 4 điểm** trên frame camera:
   - Top-Left, Bottom-Left, Top-Right, Bottom-Right

2. **Tính ma trận homography:**
   ```python
   pts1 = [4 điểm pixel]
   pts2 = [4 điểm BIM tương ứng]
   matrix = cv2.getPerspectiveTransform(pts1, pts2)
   ```

3. **Lưu vào file config:**
   - Camera 1: `config/chuyendoitoado.py`
   - Camera 2: `config/chuyendoitoado_cam2.py`

4. **Cả 2 camera dùng cùng 4 điểm BIM:**
   - Top-Left: (70, 27)
   - Bottom-Left: (32, 27)
   - Top-Right: (70, -5)
   - Bottom-Right: (32, -5)

---

## 10. XỬ LÝ LỖI

### Câu hỏi: "Xử lý lỗi như thế nào?"

**Trả lời:**

**Mất kết nối camera:**
- Camera Thread: `cap.read()` → `ret=False` → Log lỗi và break
- Detection Thread: Queue timeout → Skip và tiếp tục
- Main Thread: Kiểm tra `latest_frames is None` → Không hiển thị

**Lỗi Modbus:**
- Try-except khi gửi lệnh
- Log lỗi nhưng không crash hệ thống
- Cho phép thử lại kết nối

**Lỗi Database:**
- Try-except khi ghi
- Log lỗi nhưng tiếp tục detection
- Database không ảnh hưởng đến detection

---

## CÁC CÔNG THỨC QUAN TRỌNG CẦN NHỚ

### 1. Tính tâm đáy:
```python
cx = (x1 + x2) / 2
cy = y2
```

### 2. Transform pixel → BIM (Camera 1):
```python
pt = np.array([[[px, py]]], dtype=np.float32)
tpt = cv2.perspectiveTransform(pt, matrix1)
tx, ty = tpt[0, 0, 0], tpt[0, 0, 1]
```

### 3. Transform pixel → BIM (Camera 2):
```python
# Sau perspectiveTransform:
tx, ty = ty, tx  # Swap
tx = (tx - (-5)) / 32.0 * 38.0 + 32  # Remap X
ty = (ty - 32) / 38.0 * 32.0 + (-5)  # Remap Y
ty = 22 - ty  # Đảo Y
```

### 4. Check inside BIM:
```python
x_min ≤ x ≤ x_max and y_min ≤ y ≤ y_max
```

### 5. Tính hướng ra ngoài:
```python
if x < x_min: → TRAI
if x > x_max: → PHAI
if y < y_min: → DUOI
if y > y_max: → TREN
```

---

## CÁC CON SỐ QUAN TRỌNG

- **Resolution:** 640×480 pixels
- **Confidence:** 0.3
- **Image size:** 640×640 (YOLO input)
- **Frame Queue:** maxsize=2
- **Result Queue:** maxsize=10
- **Save interval:** 10 frames
- **Modbus baudrate:** 9600
- **Vùng BIM:** X=[32, 70], Y=[-5, 27]
- **person_ID:** 0=songoku, 1=dog
- **Slave IDs:** 1=ESP32, 2=ESP8266

---

## KHI THẦY HỎI - TRẢ LỜI NGẮN GỌN

**Q: "Hệ thống hoạt động như thế nào?"**
→ 2 camera đọc RTSP → YOLO detect → Transform pixel→BIM → Check inside → Modbus → Database

**Q: "Tại sao Camera 2 phức tạp?"**
→ Camera vuông góc → Cần swap X↔Y → Remap → Đảo Y

**Q: "Tại sao dùng threading?"**
→ Camera I/O và Detection chạy song song → Không block lẫn nhau

**Q: "Modbus gửi khi nào?"**
→ Chỉ khi trạng thái thay đổi (NGOÀI↔TRONG) → Tối ưu tài nguyên

**Q: "Database lưu gì?"**
→ Tọa độ mới nhất của mỗi đối tượng → UPSERT theo person_ID

**Q: "Tại sao dùng tâm đáy?"**
→ Đại diện vị trí tiếp xúc mặt đất → Chính xác hơn tâm bounding box

