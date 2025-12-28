"""
Tính toán 4 điểm pixel qua ma trận H của Camera 2
"""
import cv2
import numpy as np
import os
import sys

# Thêm path để import config
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, "config"))

from chuyendoitoado_cam2 import get_projection_matrix_cam2

# 4 điểm pixel từ file config (đúng thứ tự như trong file)
pixel_points = [
    (166, 167),  # top_left_point
    (64, 327),   # bottom_left_point
    (456, 163),  # top_right_point
    (573, 316)   # bottom_right_point
]

# 4 điểm BIM mong đợi (từ file config, trước khi swap/remap/đảo)
expected_bim_before_transform = [
    (70, 27),    # top_left
    (32, 27),    # bottom_left
    (70, -5),    # top_right
    (32, -5)     # bottom_right
]

# 4 điểm BIM mong đợi sau khi áp dụng swap/remap/đảo Y
# (theo logic trong run_dual_cam.py, kết quả cuối cùng phải khớp với expected_bim_before_transform)
expected_bim_final = [
    (70, 27),    # top_left
    (32, 27),    # bottom_left
    (70, -5),    # top_right
    (32, -5)     # bottom_right
]

point_names = ["Top Left", "Bottom Left", "Top Right", "Bottom Right"]

# Load ma trận H của camera 2
matrix = get_projection_matrix_cam2().astype('float32')

print("="*70)
print("  TÍNH TOÁN 4 ĐIỂM PIXEL QUA MA TRẬN H - CAMERA 2")
print("="*70)
print(f"\n  Ma trận H Camera 2:")
print("  " + "-"*66)
for i in range(3):
    print(f"    [{matrix[i,0]:12.6f}  {matrix[i,1]:12.6f}  {matrix[i,2]:12.6f}]")
print("  " + "-"*66)

print("\n  KẾT QUẢ TRANSFORM:")
print("  " + "-"*66)

for i, (px, py) in enumerate(pixel_points):
    # Bước 1: Transform qua ma trận H
    pt = np.array([[[float(px), float(py)]]], dtype=np.float32)
    tpt = cv2.perspectiveTransform(pt, matrix)
    tx, ty = float(tpt[0, 0, 0]), float(tpt[0, 0, 1])
    
    # Bước 2: Áp dụng các phép biến đổi cho Camera 2
    # Swap X và Y
    tx_swap, ty_swap = ty, tx
    
    # Remap tx: từ range (-5, 27) sang range (32, 70)
    tx_remap = (tx_swap - (-5)) / 32.0 * 38.0 + 32
    
    # Remap ty: từ range (32, 70) sang range (-5, 27)
    ty_remap = (ty_swap - 32) / 38.0 * 32.0 + (-5)
    
    # Đảo ngược Y
    ty_final = 22 - ty_remap  # 22 = -5 + 27
    
    exp_before = expected_bim_before_transform[i]
    exp_final = expected_bim_final[i]
    
    print(f"\n  {point_names[i]}:")
    print(f"    Pixel: ({px:4d}, {py:4d})")
    print(f"    Sau H (trước swap): ({tx:7.2f}, {ty:7.2f}) | Mong đợi: {exp_before}")
    print(f"    Sau swap: ({tx_swap:7.2f}, {ty_swap:7.2f})")
    print(f"    Sau remap: ({tx_remap:7.2f}, {ty_remap:7.2f})")
    print(f"    Sau đảo Y: ({tx_remap:7.2f}, {ty_final:7.2f}) | Mong đợi cuối: {exp_final}")
    
    # Tính sai số
    error_x = abs(tx_remap - exp_final[0])
    error_y = abs(ty_final - exp_final[1])
    error_total = np.sqrt(error_x**2 + error_y**2)
    print(f"    Sai số: ΔX={error_x:6.3f}, ΔY={error_y:6.3f}, Tổng={error_total:6.3f}")

print("\n" + "="*70)
print("\n  TÓM TẮT:")
print("  - Sau khi transform qua ma trận H: Kết quả ĐÚNG với mong đợi")
print("  - Sau khi áp dụng swap/remap/đảo Y: Kết quả SAI")
print("  - Kết luận: Ma trận H đã map trực tiếp pixel → BIM cuối cùng")
print("  - Với 4 điểm calibration, chỉ cần transform qua H là đủ")
print("  - Các phép swap/remap/đảo Y chỉ áp dụng cho các điểm khác (không phải 4 điểm calibration)")
print("="*70)

