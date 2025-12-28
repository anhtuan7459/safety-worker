using System.Diagnostics;
using System.IO.Ports;

namespace DualCameraApp;

public partial class MainForm : Form
{
    // Serial port for Modbus
    private SerialPort? modbusPort;
    private bool isConnected = false;
    
    // Paths
    private string projectPath = @"C:\Users\Acer\Documents\Kỉ niệm\-N-main";
    private string autorunPath;
    
    // Controls
    private RichTextBox logBox = null!;
    private RichTextBox modbusLog = null!;
    private ComboBox comPortCombo = null!;
    private ComboBox baudCombo = null!;
    private Button btnConnect = null!;
    private Button btnDisconnect = null!;
    private Label statusLabel = null!;

    public MainForm()
    {
        autorunPath = Path.Combine(projectPath, "autorun");
        
        InitializeComponent();
        InitializeUI();
        
        Log("🚀 Hệ thống đã khởi động");
        Log("📹 Camera 1: 192.168.66.15 (dog)");
        Log("📹 Camera 2: 192.168.66.14 (songoku)");
        
        RefreshComPorts();
    }

    private void InitializeComponent()
    {
        this.Text = "Dual Camera Detection System";
        this.Size = new Size(540, 800);
        this.StartPosition = FormStartPosition.CenterScreen;
        this.BackColor = Color.FromArgb(245, 247, 250);
        this.Font = new Font("Segoe UI", 10);
        this.FormBorderStyle = FormBorderStyle.FixedSingle;
        this.MaximizeBox = false;
    }

    private void InitializeUI()
    {
        // Tab control
        var tabControl = new TabControl
        {
            Location = new Point(10, 10),
            Size = new Size(505, 630),
            Font = new Font("Segoe UI", 10)
        };
        this.Controls.Add(tabControl);

        // Tab 1: Control
        var tabControl1 = new TabPage("🎮 Điều khiển");
        tabControl1.BackColor = Color.White;
        CreateControlTab(tabControl1);
        tabControl.TabPages.Add(tabControl1);

        // Tab 2: Modbus RS485
        var tabModbus = new TabPage("🔌 Modbus RS485");
        tabModbus.BackColor = Color.White;
        CreateModbusTab(tabModbus);
        tabControl.TabPages.Add(tabModbus);

        // Log area
        var logGroup = new GroupBox
        {
            Text = " 📋 Thông báo ",
            Location = new Point(10, 650),
            Size = new Size(505, 100),
            Font = new Font("Segoe UI", 9, FontStyle.Bold)
        };
        this.Controls.Add(logGroup);

        logBox = new RichTextBox
        {
            Location = new Point(10, 20),
            Size = new Size(485, 70),
            BackColor = Color.FromArgb(250, 252, 255),
            ForeColor = Color.FromArgb(40, 167, 69),
            Font = new Font("Consolas", 9),
            ReadOnly = true,
            BorderStyle = BorderStyle.None
        };
        logGroup.Controls.Add(logBox);
    }

    private void CreateControlTab(TabPage tab)
    {
        // Header
        var header = new Label
        {
            Text = "Chọn chế độ chạy:",
            Font = new Font("Segoe UI", 14, FontStyle.Bold),
            ForeColor = Color.FromArgb(0, 120, 212),
            Location = new Point(20, 20),
            AutoSize = true
        };
        tab.Controls.Add(header);

        int y = 60;
        int btnWidth = 420;
        int btnHeight = 60;

        // Full System
        var btnFull = CreateButton("🚀 FULL SYSTEM\n(Calibration + Detection)", 
            Color.FromArgb(0, 123, 255), new Point(20, y), new Size(btnWidth, btnHeight));
        btnFull.Click += (s, e) => RunBat("start_system.bat");
        tab.Controls.Add(btnFull);

        // Detection
        y += 70;
        var btnDetect = CreateButton("▶ DETECTION\n(Không cần Calibration)",
            Color.FromArgb(40, 167, 69), new Point(20, y), new Size(btnWidth, btnHeight));
        btnDetect.Click += (s, e) => RunBat("run_detection.bat");
        tab.Controls.Add(btnDetect);

        // Calibration
        y += 70;
        var btnCalib = CreateButton("🎯 CALIBRATION\n(Chỉ Calibrate Camera)",
            Color.FromArgb(255, 193, 7), new Point(20, y), new Size(btnWidth, btnHeight));
        btnCalib.ForeColor = Color.Black;
        btnCalib.Click += (s, e) => RunBat("run_calibration.bat");
        tab.Controls.Add(btnCalib);

        // Record
        y += 70;
        var btnRecord = CreateButton("📹 QUAY VIDEO\n(Để lấy ảnh Label)",
            Color.FromArgb(23, 162, 184), new Point(20, y), new Size(btnWidth, btnHeight));
        btnRecord.Click += (s, e) => RunBat("run_record.bat");
        tab.Controls.Add(btnRecord);

        // Separator
        y += 80;
        var separator = new Label
        {
            BorderStyle = BorderStyle.Fixed3D,
            Location = new Point(20, y),
            Size = new Size(btnWidth, 2)
        };
        tab.Controls.Add(separator);

        // Quick actions header
        y += 15;
        var quickLabel = new Label
        {
            Text = "Thao tác nhanh:",
            Font = new Font("Segoe UI", 12, FontStyle.Bold),
            ForeColor = Color.FromArgb(0, 120, 212),
            Location = new Point(20, y),
            AutoSize = true
        };
        tab.Controls.Add(quickLabel);

        // Quick buttons
        y += 35;
        var btnFolder = CreateButton("📁 Mở Output", Color.FromArgb(108, 117, 125), 
                                      new Point(20, y), new Size(200, 40));
        btnFolder.Click += (s, e) => OpenOutputFolder();
        tab.Controls.Add(btnFolder);

        var btnDb = CreateButton("🗃 Xem Database", Color.FromArgb(108, 117, 125), 
                                  new Point(240, y), new Size(200, 40));
        btnDb.Click += (s, e) => OpenDatabase();
        tab.Controls.Add(btnDb);
    }

    private void CreateModbusTab(TabPage tab)
    {
        // Connection group
        var connGroup = new GroupBox
        {
            Text = " Kết nối RS485 ",
            Location = new Point(10, 10),
            Size = new Size(470, 130),
            Font = new Font("Segoe UI", 9, FontStyle.Bold)
        };
        tab.Controls.Add(connGroup);

        // COM Port
        var lblPort = new Label { Text = "COM:", Location = new Point(15, 35), AutoSize = true };
        connGroup.Controls.Add(lblPort);

        comPortCombo = new ComboBox
        {
            Location = new Point(60, 32),
            Size = new Size(100, 25),
            DropDownStyle = ComboBoxStyle.DropDownList
        };
        connGroup.Controls.Add(comPortCombo);

        var btnRefresh = new Button
        {
            Text = "🔄",
            Location = new Point(165, 30),
            Size = new Size(35, 28),
            FlatStyle = FlatStyle.Flat,
            BackColor = Color.FromArgb(108, 117, 125),
            ForeColor = Color.White
        };
        btnRefresh.Click += (s, e) => RefreshComPorts();
        connGroup.Controls.Add(btnRefresh);

        // Baud rate
        var lblBaud = new Label { Text = "Baud:", Location = new Point(220, 35), AutoSize = true };
        connGroup.Controls.Add(lblBaud);

        baudCombo = new ComboBox
        {
            Location = new Point(270, 32),
            Size = new Size(100, 25),
            DropDownStyle = ComboBoxStyle.DropDownList
        };
        baudCombo.Items.AddRange(new object[] { "9600", "115200" });
        baudCombo.SelectedItem = "9600";
        connGroup.Controls.Add(baudCombo);

        // Connect buttons
        btnConnect = CreateButton("🔗 Kết nối", Color.FromArgb(40, 167, 69), 
                                   new Point(15, 75), new Size(130, 40));
        btnConnect.Click += (s, e) => ConnectModbus();
        connGroup.Controls.Add(btnConnect);

        btnDisconnect = CreateButton("❌ Ngắt", Color.FromArgb(220, 53, 69), 
                                      new Point(155, 75), new Size(130, 40));
        btnDisconnect.Enabled = false;
        btnDisconnect.Click += (s, e) => DisconnectModbus();
        connGroup.Controls.Add(btnDisconnect);

        // Status
        statusLabel = new Label
        {
            Text = "⚫ Chưa kết nối",
            Location = new Point(300, 85),
            AutoSize = true,
            ForeColor = Color.FromArgb(220, 53, 69),
            Font = new Font("Segoe UI", 9, FontStyle.Bold)
        };
        connGroup.Controls.Add(statusLabel);

        // Control group
        var controlGroup = new GroupBox
        {
            Text = " Điều khiển đèn ",
            Location = new Point(10, 150),
            Size = new Size(470, 200),
            Font = new Font("Segoe UI", 9, FontStyle.Bold)
        };
        tab.Controls.Add(controlGroup);

        // Slave 1
        var lblSlave1 = new Label
        {
            Text = "Slave 1 (ESP32 - songoku):",
            Location = new Point(15, 30),
            Font = new Font("Segoe UI", 10, FontStyle.Bold),
            AutoSize = true
        };
        controlGroup.Controls.Add(lblSlave1);

        var btnOn1 = CreateButton("🔆 BẬT", Color.FromArgb(255, 193, 7), new Point(300, 25), new Size(70, 30));
        btnOn1.ForeColor = Color.Black;
        btnOn1.Click += (s, e) => SetLight(1, true);
        controlGroup.Controls.Add(btnOn1);

        var btnOff1 = CreateButton("⚫ TẮT", Color.FromArgb(52, 58, 64), new Point(380, 25), new Size(70, 30));
        btnOff1.Click += (s, e) => SetLight(1, false);
        controlGroup.Controls.Add(btnOff1);

        // Slave 2
        var lblSlave2 = new Label
        {
            Text = "Slave 2 (ESP8266 - dog):",
            Location = new Point(15, 70),
            Font = new Font("Segoe UI", 10, FontStyle.Bold),
            AutoSize = true
        };
        controlGroup.Controls.Add(lblSlave2);

        var btnOn2 = CreateButton("🔆 BẬT", Color.FromArgb(255, 193, 7), new Point(300, 65), new Size(70, 30));
        btnOn2.ForeColor = Color.Black;
        btnOn2.Click += (s, e) => SetLight(2, true);
        controlGroup.Controls.Add(btnOn2);

        var btnOff2 = CreateButton("⚫ TẮT", Color.FromArgb(52, 58, 64), new Point(380, 65), new Size(70, 30));
        btnOff2.Click += (s, e) => SetLight(2, false);
        controlGroup.Controls.Add(btnOff2);

        // All
        var btnOnAll = CreateButton("💡 BẬT TẤT CẢ", Color.FromArgb(40, 167, 69), new Point(15, 115), new Size(150, 35));
        btnOnAll.Click += (s, e) => { SetLight(1, true); SetLight(2, true); };
        controlGroup.Controls.Add(btnOnAll);

        var btnOffAll = CreateButton("🌑 TẮT TẤT CẢ", Color.FromArgb(220, 53, 69), new Point(175, 115), new Size(150, 35));
        btnOffAll.Click += (s, e) => { SetLight(1, false); SetLight(2, false); };
        controlGroup.Controls.Add(btnOffAll);

        var btnTest = CreateButton("🧪 TEST NHẤP NHÁY", Color.FromArgb(23, 162, 184), new Point(335, 115), new Size(120, 35));
        btnTest.Click += (s, e) => TestBlink();
        controlGroup.Controls.Add(btnTest);

        // Note
        var noteLabel = new Label
        {
            Text = "⚠ Modbus RTU: Coil 0, Slave 1 = ESP32 (songoku), Slave 2 = ESP8266 (dog)",
            Location = new Point(15, 165),
            Font = new Font("Segoe UI", 8),
            ForeColor = Color.Gray,
            AutoSize = true
        };
        controlGroup.Controls.Add(noteLabel);

        // Log Modbus
        var logGroup = new GroupBox
        {
            Text = " Log Modbus ",
            Location = new Point(10, 360),
            Size = new Size(470, 220),
            Font = new Font("Segoe UI", 9, FontStyle.Bold)
        };
        tab.Controls.Add(logGroup);

        modbusLog = new RichTextBox
        {
            Location = new Point(10, 25),
            Size = new Size(450, 185),
            BackColor = Color.FromArgb(250, 252, 255),
            ForeColor = Color.FromArgb(0, 100, 180),
            Font = new Font("Consolas", 9),
            ReadOnly = true,
            BorderStyle = BorderStyle.FixedSingle
        };
        logGroup.Controls.Add(modbusLog);
    }

    private Button CreateButton(string text, Color backColor, Point location, Size size)
    {
        return new Button
        {
            Text = text,
            Location = location,
            Size = size,
            FlatStyle = FlatStyle.Flat,
            BackColor = backColor,
            ForeColor = Color.White,
            Font = new Font("Segoe UI", 10, FontStyle.Bold),
            Cursor = Cursors.Hand
        };
    }

    // ============ FUNCTIONS ============

    private void RunBat(string batName)
    {
        var batPath = Path.Combine(autorunPath, batName);
        if (!File.Exists(batPath))
        {
            MessageBox.Show($"Không tìm thấy: {batPath}", "Lỗi", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        Log($"🚀 Đang chạy: {batName}");
        try
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = batPath,
                WorkingDirectory = projectPath,
                UseShellExecute = true
            });
        }
        catch (Exception ex)
        {
            Log($"❌ Lỗi: {ex.Message}");
        }
    }

    private void OpenOutputFolder()
    {
        var outputPath = Path.Combine(projectPath, "output");
        if (Directory.Exists(outputPath))
        {
            Process.Start("explorer.exe", outputPath);
            Log("📁 Đã mở Output");
        }
    }

    private void OpenDatabase()
    {
        var dbPath = Path.Combine(projectPath, "output", "data.db");
        if (File.Exists(dbPath))
        {
            Process.Start(new ProcessStartInfo { FileName = dbPath, UseShellExecute = true });
            Log("🗃 Đã mở Database");
        }
        else
        {
            MessageBox.Show("Database chưa tồn tại!", "Cảnh báo", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
    }

    private void RefreshComPorts()
    {
        comPortCombo.Items.Clear();
        var ports = SerialPort.GetPortNames();
        comPortCombo.Items.AddRange(ports);
        if (ports.Length > 0)
        {
            comPortCombo.SelectedIndex = 0;
            Log($"🔌 Tìm thấy: {string.Join(", ", ports)}");
        }
        else
        {
            Log("⚠ Không tìm thấy COM");
        }
    }

    private void ConnectModbus()
    {
        if (comPortCombo.SelectedItem == null)
        {
            MessageBox.Show("Chưa chọn COM!", "Cảnh báo", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        try
        {
            var port = comPortCombo.SelectedItem.ToString()!;
            var baud = int.Parse(baudCombo.SelectedItem?.ToString() ?? "9600");

            modbusPort = new SerialPort(port, baud, Parity.None, 8, StopBits.One);
            modbusPort.ReadTimeout = 1000;
            modbusPort.WriteTimeout = 1000;
            modbusPort.Open();

            isConnected = true;
            btnConnect.Enabled = false;
            btnDisconnect.Enabled = true;
            statusLabel.Text = $"🟢 {port}";
            statusLabel.ForeColor = Color.FromArgb(40, 167, 69);

            Log($"🔗 Đã kết nối RS485 tại {port}");
            ModbusLog($"[CONNECTED] {port} @ {baud}");
            ModbusLog("Slave 1: ESP32 (songoku)");
            ModbusLog("Slave 2: ESP8266 (dog)");
        }
        catch (Exception ex)
        {
            Log($"❌ Lỗi: {ex.Message}");
        }
    }

    private void DisconnectModbus()
    {
        SetLight(1, false);
        SetLight(2, false);
        
        if (modbusPort != null && modbusPort.IsOpen)
        {
            modbusPort.Close();
            modbusPort.Dispose();
            modbusPort = null;
        }

        isConnected = false;
        btnConnect.Enabled = true;
        btnDisconnect.Enabled = false;
        statusLabel.Text = "⚫ Đã ngắt";
        statusLabel.ForeColor = Color.FromArgb(220, 53, 69);

        Log("❌ Đã ngắt RS485");
    }

    private void SetLight(int slaveId, bool state)
    {
        if (!isConnected || modbusPort == null)
        {
            return;
        }

        try
        {
            // Modbus RTU Write Single Coil (Function 05)
            // Frame: [SlaveID][FuncCode][AddrHi][AddrLo][ValueHi][ValueLo][CRCLo][CRCHi]
            byte[] frame = new byte[8];
            frame[0] = (byte)slaveId;           // Slave ID
            frame[1] = 0x05;                     // Function code: Write Single Coil
            frame[2] = 0x00;                     // Address Hi
            frame[3] = 0x00;                     // Address Lo (Coil 0)
            frame[4] = state ? (byte)0xFF : (byte)0x00;  // Value Hi
            frame[5] = 0x00;                     // Value Lo

            // Calculate CRC16
            ushort crc = CalculateCRC16(frame, 6);
            frame[6] = (byte)(crc & 0xFF);       // CRC Lo
            frame[7] = (byte)(crc >> 8);          // CRC Hi

            modbusPort.Write(frame, 0, 8);

            var status = state ? "🔆 BẬT" : "⚫ TẮT";
            var device = slaveId == 1 ? "ESP32 (songoku)" : "ESP8266 (dog)";
            ModbusLog($"[TX] Slave {slaveId}: {status} - {device}");
        }
        catch (Exception ex)
        {
            ModbusLog($"[ERROR] Slave {slaveId}: {ex.Message}");
        }
    }

    private ushort CalculateCRC16(byte[] buffer, int length)
    {
        ushort crc = 0xFFFF;
        for (int i = 0; i < length; i++)
        {
            crc ^= buffer[i];
            for (int j = 0; j < 8; j++)
            {
                if ((crc & 0x0001) != 0)
                {
                    crc >>= 1;
                    crc ^= 0xA001;
                }
                else
                {
                    crc >>= 1;
                }
            }
        }
        return crc;
    }

    private void TestBlink()
    {
        if (!isConnected)
        {
            MessageBox.Show("Chưa kết nối Modbus!", "Cảnh báo", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        ModbusLog("[TEST] Bắt đầu test nhấp nháy...");
        
        Task.Run(async () =>
        {
            for (int i = 0; i < 3; i++)
            {
                this.Invoke(() => { SetLight(1, true); SetLight(2, true); });
                await Task.Delay(300);
                this.Invoke(() => { SetLight(1, false); SetLight(2, false); });
                await Task.Delay(300);
            }
            this.Invoke(() => ModbusLog("[TEST] Hoàn tất!"));
        });
    }

    private void Log(string message)
    {
        var timestamp = DateTime.Now.ToString("HH:mm:ss");
        logBox.AppendText($"[{timestamp}] {message}\n");
        logBox.ScrollToCaret();
    }

    private void ModbusLog(string message)
    {
        var timestamp = DateTime.Now.ToString("HH:mm:ss");
        modbusLog.AppendText($"[{timestamp}] {message}\n");
        modbusLog.ScrollToCaret();
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        DisconnectModbus();
        base.OnFormClosing(e);
    }
}
