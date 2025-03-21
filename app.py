from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Sveiki no Cloud Run testa aplikācijas!"})

@app.route("/paytraq-webhook", methods=["POST"])
def paytraq_webhook():
    data = request.json
    print("Saņemts dati no PayTraq:", data)
    return jsonify({"status": "dati saņemti"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
