"""
Socket Client - Chạy trên máy có webcam để gửi hình ảnh đến server

Cách dùng:
    python socket_client.py <IP_SERVER>
    python socket_client.py 192.168.1.100
"""
import socket
import cv2
import struct
import time
import sys

def start_client(server_ip, server_port=9999, camera_id=0):
    """
    Khởi động client để gửi hình ảnh webcam đến server
    
    Args:
        server_ip: Địa chỉ IP của laptop/server
        server_port: Port của server (mặc định 9999)
        camera_id: ID của webcam (mặc định 0)
    """
    # Kết nối đến server
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    print(f"Đang kết nối đến server {server_ip}:{server_port}...")
    
    try:
        client_socket.connect((server_ip, server_port))
        print("[+] Đã kết nối thành công!")
    except Exception as e:
        print(f"[!] Không thể kết nối đến server: {e}")
        print("Hãy kiểm tra:")
        print("  1. Server đã chạy chưa?")
        print("  2. Địa chỉ IP có đúng không?")
        print("  3. Hai máy có cùng mạng WiFi không?")
        print("  4. Firewall có chặn không?")
        return
    
    # Mở webcam
    cap = cv2.VideoCapture(camera_id)
    
    if not cap.isOpened():
        print(f"[!] Không thể mở webcam với ID: {camera_id}")
        client_socket.close()
        return
    
    # Cấu hình webcam
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("[*] Đang gửi hình ảnh... Nhấn 'q' để dừng")
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("[!] Không thể đọc frame từ webcam")
                break
            
            # Nén hình ảnh thành JPEG để giảm dung lượng
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            _, encoded_frame = cv2.imencode('.jpg', frame, encode_param)
            frame_bytes = encoded_frame.tobytes()
            
            # Gửi kích thước frame trước
            message_size = struct.pack("Q", len(frame_bytes))
            
            try:
                client_socket.sendall(message_size + frame_bytes)
            except Exception as e:
                print(f"[!] Mất kết nối với server: {e}")
                break
            
            # Hiển thị preview trên máy client (tùy chọn)
            cv2.imshow("Webcam Preview (Client)", frame)
            
            # Nhấn 'q' để thoát
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[*] Đang đóng client...")
                break
            
            # Delay nhỏ để không quá tải
            time.sleep(0.03)  # ~30 FPS
    
    except KeyboardInterrupt:
        print("\n[*] Đã dừng bởi người dùng")
    
    finally:
        cap.release()
        client_socket.close()
        cv2.destroyAllWindows()
        print("[*] Đã đóng kết nối")

if __name__ == "__main__":
    SERVER_PORT = 9999
    CAMERA_ID = 0  # Thay đổi nếu có nhiều webcam
    
    # Lấy IP từ command line hoặc yêu cầu nhập
    if len(sys.argv) > 1:
        SERVER_IP = sys.argv[1]
    else:
        print("\n" + "=" * 50)
        print("  📷 SOCKET CLIENT - GỬI HÌNH ẢNH WEBCAM")
        print("=" * 50)
        print("\nCách 1: python socket_client.py <IP_SERVER>")
        print("Cách 2: Nhập IP bên dưới\n")
        SERVER_IP = input("👉 Nhập IP của Server: ").strip()
        
        if not SERVER_IP:
            print("[!] Bạn chưa nhập IP!")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("  📷 SOCKET CLIENT - GỬI HÌNH ẢNH WEBCAM")
    print("=" * 50)
    print(f"  Server IP : {SERVER_IP}")
    print(f"  Port      : {SERVER_PORT}")
    print(f"  Camera ID : {CAMERA_ID}")
    print("=" * 50 + "\n")
    
    start_client(SERVER_IP, SERVER_PORT, CAMERA_ID)

