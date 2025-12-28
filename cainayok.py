from pymodbus.client.sync import ModbusSerialClient as ModbusClient
import time


def main():
    client = ModbusClient(
        method='rtu',
        port='COM7',     # đổi thành cổng USB RS485 của bạn
        baudrate=9600,
        parity='N',
        stopbits=1,
        bytesize=8,
        timeout=1
    )

    if not client.connect():
        print("Không thể kết nối tới cổng COM. Kiểm tra kết nối.")
        return

    # current default unit (slave id)
    current_unit = 1
    # track last known state per unit (optional, program-local)
    states = {}

    def set_coil(val, unit=current_unit):
        try:
            client.write_coil(0, bool(val), unit=unit)
            states[unit] = bool(val)
            print(f"Unit {unit}:", "ON" if states[unit] else "OFF")
        except Exception as e:
            print(f"Lỗi khi viết coil tới unit {unit}:", e)

    print("Chương trình điều khiển LED (coil 0). Lệnh: on [N], off [N], toggle [N], use N, status [N|all], exit")
    try:
        while True:
            raw = input("> ").strip()
            if not raw:
                continue
            parts = raw.lower().split()
            cmd = parts[0]
            arg_unit = None
            if len(parts) > 1:
                try:
                    arg_unit = int(parts[1])
                except ValueError:
                    arg_unit = None

            unit = arg_unit if arg_unit is not None else current_unit

            if cmd in ("use", "u"):
                if arg_unit is None:
                    print("Dùng: use N  (ví dụ: use 2)")
                else:
                    current_unit = arg_unit
                    print(f"Default unit set to {current_unit}")
            elif cmd in ("on", "bật", "1"):
                set_coil(True, unit=unit)
            elif cmd in ("off", "tắt", "0"):
                set_coil(False, unit=unit)
            elif cmd in ("toggle", "t"):
                new = not states.get(unit, False)
                set_coil(new, unit=unit)
            elif cmd in ("status", "s"):
                if parts and len(parts) > 1 and parts[1] == "all":
                    if not states:
                        print("Chưa có trạng thái nào được ghi.")
                    else:
                        for u, st in states.items():
                            print(f"Unit {u}:", "ON" if st else "OFF")
                else:
                    st = states.get(unit)
                    if st is None:
                        print(f"Unit {unit}: Unknown (chưa thay đổi từ chương trình)")
                    else:
                        print(f"Unit {unit}:", "ON" if st else "OFF")
            elif cmd in ("help", "h", "?"):
                print("Lệnh: on [N], off [N], toggle [N], use N, status [N|all], exit")
            elif cmd in ("exit", "quit", "q"):
                break
            else:
                print("Lệnh không hợp lệ. Dùng: on [N], off [N], toggle [N], use N, status [N|all], exit")
    finally:
        client.close()
        print("Kết thúc, client đóng kết nối.")


if __name__ == '__main__':
    main()
