import cv2
import numpy as np
from ultralytics import YOLO
from chuyendoitoado import get_projection_matrix
import pandas as pd

def analyze_video_coordinates(video_path, model_path):
    """
    Chạy detection trên video và thu thập tọa độ để phân tích
    """
    model = YOLO(model_path)
    proj_matrix = get_projection_matrix().astype('float32')
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Không mở được video: {video_path}")
        return
    
    # BIM bounds
    BIM_X_MIN, BIM_X_MAX = -476, -96
    BIM_Y_MIN, BIM_Y_MAX = -568, -228
    
    all_coords = []
    frame_idx = 0
    
    print("🎬 Bắt đầu phân tích video...")
    print(f"📦 Vùng BIM hợp lệ: X[{BIM_X_MIN} → {BIM_X_MAX}], Y[{BIM_Y_MIN} → {BIM_Y_MAX}]")
    print("="*80)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        results = model(frame, device=0, conf=0.3, imgsz=640, half=True, verbose=False)
        
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                label = model.names.get(cls_id, str(cls_id))
                conf = float(box.conf[0])
                
                # Skip moc labels
                if label.lower() in {"moc1", "moc2", "moc3", "moc4"}:
                    continue
                
                # Tính tọa độ tâm đáy
                cx = int((x1 + x2) / 2)
                cy = y2
                
                # Transform to BIM coordinates
                try:
                    pt = np.array([[[float(cx), float(cy)]]], dtype=np.float32)
                    tpt = cv2.perspectiveTransform(pt, proj_matrix)
                    tx, ty = float(tpt[0, 0, 0]), float(tpt[0, 0, 1])
                except Exception as e:
                    print(f"⚠️ Transform failed: {e}")
                    tx, ty = float(cx), float(cy)
                
                # Check if in bounds
                in_bounds = (BIM_X_MIN <= tx <= BIM_X_MAX) and (BIM_Y_MIN <= ty <= BIM_Y_MAX)
                
                coord_data = {
                    'frame': frame_idx,
                    'label': label,
                    'conf': round(conf, 3),
                    'pixel_x': cx,
                    'pixel_y': cy,
                    'bim_x': int(tx),
                    'bim_y': int(ty),
                    'in_bounds': in_bounds
                }
                all_coords.append(coord_data)
                
                # In ra console
                status = "✅" if in_bounds else "❌ NGOÀI KHUNG"
                print(f"Frame {frame_idx:4d} | {label:10s} | Pixel:({cx:3d},{cy:3d}) → BIM:({int(tx):4d},{int(ty):4d}) {status}")
                
                # Vẽ lên frame
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
                
                # Text hiển thị
                text1 = f"{label} P:({cx},{cy})"
                text2 = f"BIM:({int(tx)},{int(ty)}) {'OK' if in_bounds else 'OUT'}"
                color2 = (0, 255, 0) if in_bounds else (0, 0, 255)
                
                cv2.putText(frame, text1, (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.putText(frame, text2, (x1, y2 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color2, 2)
        
        cv2.imshow("Video Analysis", frame)
        if cv2.waitKey(30) & 0xFF == 27:
            break
        
        frame_idx += 1
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Phân tích kết quả
    if all_coords:
        df = pd.DataFrame(all_coords)
        
        print("\n" + "="*80)
        print("📊 TỔNG HỢP PHÂN TÍCH")
        print("="*80)
        print(f"Tổng số detections: {len(df)}")
        print(f"Số frames xử lý: {frame_idx}")
        
        in_bounds_count = df['in_bounds'].sum()
        out_bounds_count = len(df) - in_bounds_count
        
        print(f"\n✅ Tọa độ TRONG khung BIM: {in_bounds_count} ({in_bounds_count/len(df)*100:.1f}%)")
        print(f"❌ Tọa độ NGOÀI khung BIM: {out_bounds_count} ({out_bounds_count/len(df)*100:.1f}%)")
        
        print(f"\n📍 Tọa độ BIM - Thống kê:")
        print(f"   X: min={df['bim_x'].min()}, max={df['bim_x'].max()}")
        print(f"   Y: min={df['bim_y'].min()}, max={df['bim_y'].max()}")
        
        print(f"\n📦 Vùng BIM mong muốn:")
        print(f"   X: [{BIM_X_MIN} → {BIM_X_MAX}] (rộng {BIM_X_MAX - BIM_X_MIN}cm)")
        print(f"   Y: [{BIM_Y_MIN} → {BIM_Y_MAX}] (cao {BIM_Y_MAX - BIM_Y_MIN}cm)")
        
        # Xem những detections ngoài khung
        if out_bounds_count > 0:
            print(f"\n❌ CÁC DETECTION NGOÀI KHUNG:")
            out_df = df[~df['in_bounds']]
            print(out_df[['frame', 'label', 'pixel_x', 'pixel_y', 'bim_x', 'bim_y']].to_string(index=False))
        
        # Lưu kết quả
        output_file = "video_coords_analysis.xlsx"
        df.to_excel(output_file, index=False)
        print(f"\n💾 Đã lưu chi tiết vào: {output_file}")
    else:
        print("❌ Không có detection nào!")

if __name__ == "__main__":
    video_path = r"D:\Download\Video\3.mp4"
    model_path = r"C:\Users\Acer\Documents\Thonny\VXL\kingdomcome\18thg9\best1.pt"
    
    analyze_video_coordinates(video_path, model_path)

