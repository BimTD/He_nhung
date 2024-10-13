import cv2
from ultralytics import YOLO
import threading
import tkinter as tk
import time
from datetime import datetime
import json  
import os  
from EmulatorGUI import GPIO
import winsound  
from pnhLCD1602 import LCD1602

# Khởi tạo GPIO
GPIO.setmode(GPIO.BCM)

# Danh sách các chân GPIO
GPIONames = [14, 15, 18, 23, 24, 25, 8, 7]

# Thiết lập các chân GPIO
for pin in GPIONames:
    GPIO.setup(pin, GPIO.OUT)

# Khởi tạo LCD
lcd = LCD1602()

# Biến đếm số người
person_count = 0

# Tạo đối tượng YOLO
model = YOLO("yolov8n.pt")  # Sử dụng phiên bản YOLO phù hợp

# Mở camera
cap = cv2.VideoCapture(0)

# Kiểm tra xem camera có thể truy cập không
if not cap.isOpened():
    print("Không thể truy cập camera.")
    exit()

# Hàm lấy tháng hiện tại
def get_current_month():
    today = datetime.now()
    return today.strftime("%Y-%m")  # Định dạng: Năm-Tháng (ví dụ: "2024-10")

# Hàm đọc dữ liệu từ tệp JSON
def load_data_from_json():
    if os.path.exists('detection_data.json'):
        with open('detection_data.json', 'r') as json_file:
            try:
                return json.load(json_file)
            except json.JSONDecodeError:
                return {}  # Trả về rỗng nếu có lỗi
    else:
        return {}  # Trả về rỗng nếu tệp không tồn tại

# Hàm lưu dữ liệu vào tệp JSON
def save_data_to_json():
    with open('detection_data.json', 'w') as json_file:
        json.dump(detection_data, json_file, indent=4)

# Hàm lấy khung giờ trong ngày
def get_time_period():
    current_hour = datetime.now().hour
    if 6 <= current_hour < 12:
        return "Sáng"
    elif 12 <= current_hour < 18:
        return "Trưa"
    elif 18 <= current_hour < 21:
        return "Chiều"
    else:
        return "Tối"

# Tải dữ liệu phát hiện hiện có hoặc tạo cấu trúc mới
detection_data = load_data_from_json()

# Hàm cập nhật dữ liệu phát hiện (hàng ngày và hàng tháng)
def update_detection_data(count):
    today = datetime.now().strftime("%Y-%m-%d")  # Ngày hiện tại làm khóa
    current_month = get_current_month()  # Tháng hiện tại làm khóa

    time_period = get_time_period()  # Lấy khung giờ (Sáng, Trưa, v.v.)

    # Khởi tạo cấu trúc dữ liệu hàng ngày nếu thiếu
    if today not in detection_data:
        detection_data[today] = {"Sáng": 0, "Trưa": 0, "Chiều": 0, "Tối": 0}

    # Cập nhật số lượng hàng ngày
    detection_data[today][time_period] += count

    # Khởi tạo cấu trúc dữ liệu hàng tháng nếu thiếu
    if current_month not in detection_data:
        detection_data[current_month] = {"Sáng": 0, "Trưa": 0, "Chiều": 0, "Tối": 0}
    
    # Cập nhật số lượng hàng tháng
    detection_data[current_month][time_period] += count

    # Lưu dữ liệu đã cập nhật vào tệp JSON
    save_data_to_json()

# Hàm điều khiển LED và âm thanh cảnh báo trong một luồng riêng
def alert_person_detected():
    def alert():
        current_time = datetime.now().time()
        start_time = datetime.strptime("00:01:00", "%H:%M:%S").time()
        end_time = datetime.strptime("23:59:00", "%H:%M:%S").time()

        if start_time <= current_time <= end_time:
            GPIO.output(GPIONames[0], GPIO.HIGH)  # Bật LED
            winsound.Beep(1000, 500)  # Phát âm thanh 1000 Hz trong 500 ms
            time.sleep(0.5)
            GPIO.output(GPIONames[0], GPIO.LOW)  # Tắt LED

    threading.Thread(target=alert).start()  # Chạy hàm alert trong luồng riêng

# Lớp điều khiển LED và giao diện GUI cho trạng thái phát hiện
class LEDController(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.person_detected = False  # Biến kiểm tra người có bị phát hiện không
        self.start()

    def run(self):
        self.root = tk.Tk()  # Tạo cửa sổ GUI
        self.root.wm_title("Camera An Ninh")  # Tiêu đề cửa sổ

        self.status_label = tk.Label(self.root, text="Không có người phát hiện", font=("Arial", 18))  # Nhãn trạng thái
        self.status_label.pack(pady=20)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)  # Đóng cửa sổ
        self.root.mainloop()  # Bắt đầu vòng lặp GUI

    def update_status(self, detected):
        self.person_detected = detected  # Cập nhật trạng thái phát hiện
        if detected:
            self.status_label.config(text="Người phát hiện!", fg="green")  # Thay đổi màu sắc và văn bản nếu phát hiện
        else:
            self.status_label.config(text="Không có người phát hiện", fg="red")

    def on_close(self):
        GPIO.cleanup()  # Dọn dẹp GPIO khi đóng cửa sổ
        self.root.destroy()  # Đóng cửa sổ GUI

# Hàm cập nhật LCD với số lượng người
def update_lcd_count(count):
    lcd.clear()  # Xóa màn hình LCD
    lcd.set_cursor(0, 0)  # Đặt con trỏ về đầu dòng
    lcd.print("So nguoi: " + str(count))  # Hiển thị số người phát hiện

# Khởi tạo điều khiển LED và GUI
app = LEDController()

while True:
    ret, frame = cap.read()  # Đọc khung hình từ camera

    if not ret:
        print("Không thể nhận khung hình.")
        break

    frame_resized = cv2.resize(frame, (640, 480))  # Thay đổi kích thước khung hình

    results = model(frame_resized)  # Phát hiện người trong khung hình

    person_detected = False  # Biến kiểm tra trạng thái phát hiện người
    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) == 0:  # Lớp '0' là 'người'
                person_detected = True
                x1, y1, x2, y2 = map(int, box.xyxy[0])  # Lấy tọa độ khung bao
                cv2.rectangle(frame_resized, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Vẽ khung bao xung quanh người phát hiện

    if person_detected:
        person_count += 1  # Tăng biến đếm số người phát hiện
        alert_person_detected()  # Gọi hàm cảnh báo khi phát hiện người
        update_lcd_count(person_count)  # Cập nhật số lượng người trên LCD
        update_detection_data(1)  # Cập nhật dữ liệu phát hiện

    app.update_status(person_detected)  # Cập nhật trạng thái trên GUI

    cv2.imshow('Phát hiện người với YOLOv8', frame_resized)  # Hiển thị khung hình với người phát hiện

    if cv2.waitKey(1) & 0xFF == ord('q'):  # Nhấn 'q' để thoát
        break

cap.release()  # Giải phóng camera
cv2.destroyAllWindows()  # Đóng tất cả cửa sổ
GPIO.cleanup()  # Dọn dẹp GPIO
