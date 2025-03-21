from flask import Flask, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

# API dati
API_KEY = "421045bc-a402-4223-b048-52b65340e21a-98693"
API_TOKEN = "KcPtQHuxpxGbXCr4"

@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "Sveiki! Serviss darbojas. Izmanto /get-paytraq-orders lai ielādētu šodienas datus."})

@app.route('/get-paytraq-orders', methods=['GET'])
def get_orders():
    today = datetime.today().strftime('%Y-%m-%d')
    url = f"https://go.paytraq.com/api/sales?APIKey={API_KEY}&APIToken={API_TOKEN}&DateFrom={today}&DateTo={today}"

    response = requests.get(url)
    
    if response.status_code == 200:
        return jsonify({"status": "success", "data": response.text})
    else:
        return jsonify({"status": "error", "code": response.status_code, "message": response.text})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
