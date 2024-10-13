from flask import Flask, render_template, jsonify, request
import json
from collections import defaultdict

app = Flask(__name__)

# Đọc dữ liệu từ file JSON
def read_json_data():
    try:
        with open('detection_data.json', 'r') as json_file:
            data = json.load(json_file)
    except FileNotFoundError:
        data = {}
    return data

# Trang index sẽ hiển thị biểu đồ
@app.route('/')
def index():
    return render_template('chart.html')

# API trả về dữ liệu JSON dựa trên ngày hoặc tháng
@app.route('/get_chart_data')
def get_chart_data():
    data = read_json_data()  # Lấy dữ liệu từ file JSON
    time_range = request.args.get('range', 'day')  # Lấy tham số range (ngày hoặc tháng)

    if time_range == 'day':
        selected_date = request.args.get('date', '2024-10-13')  # Lấy ngày người dùng chọn, mặc định là 2024-10-13
        return jsonify(data.get(selected_date, {}))  # Trả về dữ liệu theo ngày
    elif time_range == 'month':
        selected_month = request.args.get('month', '2024-10')  # Lấy tháng người dùng chọn, mặc định là tháng 10 năm 2024
        # Khởi tạo dữ liệu cộng dồn cho các khung giờ
        accumulated_data = defaultdict(int)
        
        # Duyệt qua các ngày trong tháng và cộng dồn dữ liệu
        for date, values in data.items():
            if date.startswith(selected_month):  # Chỉ lấy các ngày trong tháng
                for time_period, count in values.items():
                    accumulated_data[time_period] += count
        
        # Trả về dữ liệu cộng dồn
        return jsonify(accumulated_data)
    


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
