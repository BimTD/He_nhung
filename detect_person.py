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

# Khởi tạo ghi video (biến này sẽ lưu đối tượng VideoWriter)
video_writer = None
video_filenames = []  # Danh sách để lưu các tên tệp video

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

# Hàm cập nhật dữ liệu phát hiện (không lưu video_path)
def update_detection_data(count):
    today = datetime.now().strftime("%Y-%m-%d")  # Ngày hiện tại làm khóa
    current_month = get_current_month()  # Tháng hiện tại làm khóa

    time_period = get_time_period()  # Lấy khung giờ (Sáng, Trưa, v.v.)

    # Khởi tạo cấu trúc dữ liệu hàng ngày nếu thiếu
    if today not in detection_data:
        detection_data[today] = {"Sáng": 0, "Trưa": 0, "Chiều": 0, "Tối": 0, "videos": []}

    # Cập nhật số lượng hàng ngày
    detection_data[today][time_period] += count

    # Khởi tạo cấu trúc dữ liệu hàng tháng nếu thiếu
    if current_month not in detection_data:
        detection_data[current_month] = {"Sáng": 0, "Trưa": 0, "Chiều": 0, "Tối": 0}

    # Cập nhật số lượng hàng tháng
    detection_data[current_month][time_period] += count

    # Lưu dữ liệu đã cập nhật vào tệp JSON (không lưu video path)
    save_data_to_json()

# Hàm điều khiển LED và âm thanh cảnh báo trong một luồng riêng
def alert_person_detected():
    def alert():
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

# Biến để lưu trữ thời gian phát hiện lần cuối
last_detected_time = 0  # Thời gian phát hiện lần cuối
detection_interval = 1  # Thời gian ngưỡng giữa các lần đếm (giây)

# Bắt đầu ghi video với tên tệp duy nhất
def start_recording_video():
    global video_writer
    # Tạo tên tệp video duy nhất bằng timestamp
    video_filename = f'output_video_{datetime.now().strftime("%Y%m%d_%H%M%S")}.avi'
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video_writer = cv2.VideoWriter(video_filename, fourcc, 20.0, (640, 480))
    video_filenames.append(video_filename)  # Lưu tên tệp video vào danh sách
    print(f"Bắt đầu ghi video vào {video_filename}")
    return video_filename

# Bắt đầu quy trình phát hiện
while True:
    ret, frame = cap.read()  # Đọc khung hình từ camera

    if not ret:
        print("Không thể nhận khung hình.")
        break

    frame_resized = cv2.resize(frame, (640, 480))  # Thay đổi kích thước khung hình

    results = model(frame_resized)  # Phát hiện người trong khung hình

    person_detected = False  # Biến kiểm tra trạng thái phát hiện người
    current_time = time.time()  # Lấy thời gian hiện tại

    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) == 0:  # Lớp '0' là 'người'
                person_detected = True  # Đánh dấu rằng có người được phát hiện
                x1, y1, x2, y2 = map(int, box.xyxy[0])  # Lấy tọa độ khung bao
                cv2.rectangle(frame_resized, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Vẽ khung bao xung quanh người phát hiện

    app.update_status(person_detected)  # Cập nhật GUI khi phát hiện hoặc không phát hiện người

    # Nếu phát hiện người thì bắt đầu ghi video
    if person_detected and video_writer is None:
        video_filename = start_recording_video()  # Ghi video với tên tệp duy nhất

    if video_writer is not None:
        video_writer.write(frame_resized)  # Ghi khung hình vào tệp video

    # Nếu phát hiện người và đủ thời gian kể từ lần cuối, thực hiện các hành động
    if person_detected and current_time - last_detected_time > detection_interval:
        alert_person_detected()  # Kích hoạt cảnh báo
        person_count += 1  # Tăng số đếm
        update_lcd_count(person_count)  # Cập nhật đếm người lên LCD
        update_detection_data(1)  # Cập nhật số lượng người phát hiện
        last_detected_time = current_time  # Cập nhật thời gian phát hiện lần cuối

    # Hiển thị khung hình đã phát hiện
    cv2.imshow("Camera An Ninh", frame_resized)

    # Thoát vòng lặp nếu nhấn phím 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Khi kết thúc, giải phóng tài nguyên
cap.release()

# Dừng ghi video khi thoát
if video_writer is not None:
    video_writer.release()

cv2.destroyAllWindows()

# Đọc dữ liệu hiện có từ 'videos_path.json'
if os.path.exists('videos_path.json'):
    with open('videos_path.json', 'r') as f:
        try:
            videos_data = json.load(f)
        except json.JSONDecodeError:
            videos_data = {"videos": []}  # Nếu tệp bị lỗi, khởi tạo rỗng
else:
    videos_data = {"videos": []}  # Khởi tạo rỗng nếu tệp chưa tồn tại

# Thêm các video filenames mới vào danh sách
videos_data["videos"].extend(video_filenames)

# Lưu lại dữ liệu với các đường dẫn video mới vào tệp 'videos_path.json'
with open('videos_path.json', 'w') as f:
    json.dump(videos_data, f, indent=4)

print(f"Video paths đã được cập nhật và lưu vào tệp 'videos_path.json'.")

