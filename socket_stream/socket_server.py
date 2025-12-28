"""
Socket Server - Chạy trên laptop để nhận hình ảnh từ webcam
"""
import socket
import cv2
import numpy as np
import struct
import os

def get_all_local_ips():
    """Lấy tất cả địa chỉ IP của máy trong mạng LAN"""
    ips = []
    
    # Cách 1: Kết nối ra ngoài để lấy IP chính
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        main_ip = s.getsockname()[0]
        s.close()
        ips.append(main_ip)
    except Exception:
        pass
    
    # Cách 2: Lấy từ hostname
    try:
        hostname = socket.gethostname()
        host_ips = socket.gethostbyname_ex(hostname)[2]
        for ip in host_ips:
            if ip not in ips and not ip.startswith('127.'):
                ips.append(ip)
    except Exception:
        pass
    
    if not ips:
        ips.append('127.0.0.1')
    
    return ips

def get_local_ip():
    """Lấy địa chỉ IP chính của máy"""
    ips = get_all_local_ips()
    return ips[0] if ips else '127.0.0.1'

def start_server(host='0.0.0.0', port=9999):
    """
    Khởi động server để nhận hình ảnh
    host='0.0.0.0' để chấp nhận kết nối từ mọi địa chỉ IP
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    
    # Tự động lấy IP của máy
    local_ip = get_local_ip()
    all_ips = get_all_local_ips()
    hostname = socket.gethostname()
    
    print("\n" + "=" * 60)
    print("        🖥️  SOCKET SERVER - NHẬN HÌNH ẢNH WEBCAM")
    print("=" * 60)
    print(f"  Tên máy tính : {hostname}")
    print(f"  IP chính     : {local_ip}")
    if len(all_ips) > 1:
        print(f"  Các IP khác  : {', '.join(all_ips[1:])}")
    print(f"  Port         : {port}")
    print("=" * 60)
    print(f"\n  👉 COPY IP NÀY CHO CLIENT: {local_ip}")
    print(f"     Hoặc dùng lệnh: python socket_client.py {local_ip}\n")
    print("=" * 60)
    print("\n⏳ Đang chờ kết nối từ client...")
    
    while True:
        try:
            client_socket, addr = server_socket.accept()
            print(f"\n[+] Đã kết nối với client: {addr}")
            
            data = b""
            payload_size = struct.calcsize("Q")  # 8 bytes cho kích thước frame
            
            while True:
                # Nhận kích thước của frame
                while len(data) < payload_size:
                    packet = client_socket.recv(4096)
                    if not packet:
                        break
                    data += packet
                
                if len(data) < payload_size:
                    print("[-] Client đã ngắt kết nối")
                    break
                
                # Giải mã kích thước frame
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("Q", packed_msg_size)[0]
                
                # Nhận dữ liệu frame
                while len(data) < msg_size:
                    packet = client_socket.recv(4096)
                    if not packet:
                        break
                    data += packet
                
                if len(data) < msg_size:
                    print("[-] Mất kết nối trong khi nhận frame")
                    break
                
                # Giải mã frame
                frame_data = data[:msg_size]
                data = data[msg_size:]
                
                # Chuyển đổi bytes thành hình ảnh
                frame = np.frombuffer(frame_data, dtype=np.uint8)
                frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # Mirror ảnh (lật ngang)
                    frame = cv2.flip(frame, 1)
                    
                    # Hiển thị hình ảnh
                    cv2.imshow("Webcam từ Client", frame)
                    
                    # Nhấn 'q' để thoát
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("[*] Đang đóng server...")
                        client_socket.close()
                        server_socket.close()
                        cv2.destroyAllWindows()
                        return
            
            client_socket.close()
            print("[*] Đang chờ kết nối mới...")
            
        except Exception as e:
            print(f"[!] Lỗi: {e}")
            continue
    
    cv2.destroyAllWindows()
    server_socket.close()

if __name__ == "__main__":
    # Có thể thay đổi port nếu cần
    PORT = 9999
    start_server(port=PORT)

