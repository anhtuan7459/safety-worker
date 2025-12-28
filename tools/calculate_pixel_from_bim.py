"""
Chương trình tính toán điểm pixel trên Camera 1 và 2 từ tọa độ BIM
- Nhập tọa độ BIM (X, Y)
- Tính ngược lại để tìm pixel tương ứng trên cả 2 camera
- Sử dụng ma trận H nghịch đảo
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


def bim_to_pixel_cam1(bim_x, bim_y, matrix):
    """
    Tính pixel trên Camera 1 từ tọa độ BIM
    Camera 1: Transform trực tiếp qua H^(-1)
    """
    # Tạo điểm BIM dạng numpy array
    bim_point = np.array([[[float(bim_x), float(bim_y)]]], dtype=np.float32)
    
    # Tính ma trận nghịch đảo
    inv_matrix = np.linalg.inv(matrix)
    
    # Transform ngược lại
    pixel_point = cv2.perspectiveTransform(bim_point, inv_matrix)
    px = int(pixel_point[0, 0, 0])
    py = int(pixel_point[0, 0, 1])
    
    return px, py


def bim_to_pixel_cam2(bim_x, bim_y, matrix):
    """
    Tính pixel trên Camera 2 từ tọa độ BIM
    Camera 2: Cần đảo ngược các phép biến đổi trước khi dùng H^(-1)
    """
    # Bước 1: Đảo ngược phép đảo Y
    # ty = 22 - ty_original  => ty_original = 22 - ty
    ty_original = 22 - bim_y  # 22 = -5 + 27
    
    # Bước 2: Đảo ngược remap Y: từ range (-5, 27) về range (32, 70)
    # ty = (ty_old - 32) / 38.0 * 32.0 + (-5)
    # => ty_old = (ty - (-5)) / 32.0 * 38.0 + 32
    ty_before_remap = (ty_original - (-5)) / 32.0 * 38.0 + 32
    
    # Bước 3: Đảo ngược remap X: từ range (32, 70) về range (-5, 27)
    # tx = (tx_old - (-5)) / 32.0 * 38.0 + 32
    # => tx_old = (tx - 32) / 38.0 * 32.0 + (-5)
    tx_before_remap = (bim_x - 32) / 38.0 * 32.0 + (-5)
    
    # Bước 4: Đảo ngược swap (swap lại X và Y)
    tx_after_swap, ty_after_swap = ty_before_remap, tx_before_remap
    
    # Bước 5: Transform qua H^(-1)
    bim_point = np.array([[[float(tx_after_swap), float(ty_after_swap)]]], dtype=np.float32)
    inv_matrix = np.linalg.inv(matrix)
    pixel_point = cv2.perspectiveTransform(bim_point, inv_matrix)
    px = int(pixel_point[0, 0, 0])
    py = int(pixel_point[0, 0, 1])
    
    return px, py


def main():
    print("="*70)
    print("  TÍNH TOÁN ĐIỂM PIXEL TỪ TỌA ĐỘ BIM")
    print("="*70)
    print("  Chương trình tính pixel trên Camera 1 và 2 từ tọa độ BIM")
    print("="*70)
    
    # Load ma trận H
    matrix1 = get_projection_matrix().astype('float32')
    matrix2 = get_projection_matrix_cam2().astype('float32')
    
    print("\n  Ma trận H Camera 1:")
    print("  " + "-"*66)
    for i in range(3):
        print(f"    [{matrix1[i,0]:12.6f}  {matrix1[i,1]:12.6f}  {matrix1[i,2]:12.6f}]")
    print("  " + "-"*66)
    
    print("\n  Ma trận H Camera 2:")
    print("  " + "-"*66)
    for i in range(3):
        print(f"    [{matrix2[i,0]:12.6f}  {matrix2[i,1]:12.6f}  {matrix2[i,2]:12.6f}]")
    print("  " + "-"*66)
    
    # Menu
    while True:
        print("\n" + "="*70)
        print("  MENU:")
        print("  1. Nhập tọa độ BIM thủ công")
        print("  2. Tính 4 điểm calibration (Top Left, Bottom Left, Top Right, Bottom Right)")
        print("  3. Tính nhiều điểm từ file")
        print("  0. Thoát")
        print("="*70)
        
        choice = input("\n  Chọn chức năng (0-3): ").strip()
        
        if choice == "0":
            print("\n  Đã thoát chương trình.")
            break
        
        elif choice == "1":
            try:
                print("\n  Nhập tọa độ BIM:")
                bim_x = float(input("    X (East): "))
                bim_y = float(input("    Y (North): "))
                
                # Tính pixel cho Camera 1
                px1, py1 = bim_to_pixel_cam1(bim_x, bim_y, matrix1)
                
                # Tính pixel cho Camera 2
                px2, py2 = bim_to_pixel_cam2(bim_x, bim_y, matrix2)
                
                print("\n  " + "="*66)
                print(f"  Tọa độ BIM: ({bim_x:.2f}, {bim_y:.2f})")
                print("  " + "-"*66)
                print(f"  Camera 1: Pixel({px1:4d}, {py1:4d})")
                print(f"  Camera 2: Pixel({px2:4d}, {py2:4d})")
                print("  " + "="*66)
                
            except ValueError:
                print("  [ERROR] Tọa độ không hợp lệ!")
            except Exception as e:
                print(f"  [ERROR] {e}")
        
        elif choice == "2":
            # 4 điểm calibration BIM
            calibration_points = [
                ("Top Left", 70, 27),
                ("Bottom Left", 32, 27),
                ("Top Right", 70, -5),
                ("Bottom Right", 32, -5)
            ]
            
            print("\n  " + "="*70)
            print("  TÍNH TOÁN 4 ĐIỂM CALIBRATION")
            print("  " + "="*70)
            
            for name, bim_x, bim_y in calibration_points:
                px1, py1 = bim_to_pixel_cam1(bim_x, bim_y, matrix1)
                px2, py2 = bim_to_pixel_cam2(bim_x, bim_y, matrix2)
                
                print(f"\n  {name}:")
                print(f"    BIM: ({bim_x:6.2f}, {bim_y:6.2f})")
                print(f"    Camera 1: Pixel({px1:4d}, {py1:4d})")
                print(f"    Camera 2: Pixel({px2:4d}, {py2:4d})")
            
            print("\n  " + "="*70)
        
        elif choice == "3":
            file_path = input("\n  Nhập đường dẫn file (mỗi dòng: X Y): ").strip()
            if not os.path.exists(file_path):
                print(f"  [ERROR] File không tồn tại: {file_path}")
                continue
            
            try:
                output_file = file_path.replace('.txt', '_pixel.txt')
                with open(file_path, 'r') as f_in, open(output_file, 'w') as f_out:
                    f_out.write("BIM_X\tBIM_Y\tCam1_X\tCam1_Y\tCam2_X\tCam2_Y\n")
                    
                    for line_num, line in enumerate(f_in, 1):
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        try:
                            parts = line.split()
                            if len(parts) < 2:
                                continue
                            bim_x = float(parts[0])
                            bim_y = float(parts[1])
                            
                            px1, py1 = bim_to_pixel_cam1(bim_x, bim_y, matrix1)
                            px2, py2 = bim_to_pixel_cam2(bim_x, bim_y, matrix2)
                            
                            f_out.write(f"{bim_x:.2f}\t{bim_y:.2f}\t{px1}\t{py1}\t{px2}\t{py2}\n")
                            print(f"  [OK] Dòng {line_num}: BIM({bim_x:.2f}, {bim_y:.2f}) → Cam1({px1}, {py1}), Cam2({px2}, {py2})")
                            
                        except (ValueError, IndexError) as e:
                            print(f"  [WARN] Dòng {line_num} bỏ qua: {line}")
                
                print(f"\n  [SUCCESS] Đã lưu kết quả vào: {output_file}")
                
            except Exception as e:
                print(f"  [ERROR] {e}")
        
        else:
            print("  [ERROR] Lựa chọn không hợp lệ!")


if __name__ == "__main__":
    main()

