from flask import Flask, Response, request
import requests
import xml.etree.ElementTree as ET
import os
from datetime import datetime, timedelta

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY")
API_TOKEN = os.environ.get("API_TOKEN")
SYNC_URL = "https://paytraq-to-pipedrive-basic-service-281111054789.us-central1.run.app/get-paytraq-orders"

global_last_client_id = None

def safe_text(el, path, default="—"):
    try:
        found = el.find(path)
        return found.text.strip() if found is not None and found.text else default
    except:
        return default

@app.route("/paytraq-full-report", methods=["GET"])
def paytraq_full_report():
    global global_last_client_id

    list_url = f"https://go.paytraq.com/api/sales?APIKey={API_KEY}&APIToken={API_TOKEN}"

    try:
        response = requests.get(list_url)
        response.raise_for_status()
    except Exception as e:
        return Response(f"❌ Kļūda saņemot dokumentu sarakstu: {e}", mimetype="text/plain")

    root = ET.fromstring(response.content)
    first_doc = root.find(".//Document/DocumentID")
    if first_doc is None:
        return Response("❌ Nav atrasts neviens dokuments.", mimetype="text/plain")

    document_id = first_doc.text
    detail_url = f"https://go.paytraq.com/api/sale/{document_id}?APIKey={API_KEY}&APIToken={API_TOKEN}"
    try:
        detail_response = requests.get(detail_url)
        detail_response.raise_for_status()
    except Exception as e:
        return Response(f"❌ Kļūda iegūstot dokumenta datus: {e}", mimetype="text/plain")

    xml_string = detail_response.content
    detail_root = ET.fromstring(xml_string)
    global_last_client_id = safe_text(detail_root, ".//ClientID")

    return Response("✅ Saglabāts pēdējais klienta ID: " + global_last_client_id, mimetype="text/plain")

@app.route("/get-orders-last-12-months-auto", methods=["GET"])
def get_orders_last_12_months_auto():
    global global_last_client_id
    if not global_last_client_id:
        return Response("❌ Nav pieejams neviena klienta ID no /paytraq-full-report", mimetype="text/plain")
    return get_orders_last_12_months_internal(global_last_client_id)

@app.route("/get-orders-last-12-months", methods=["GET"])
def get_orders_last_12_months():
    client_id = request.args.get("client_id")
    if not client_id:
        return Response("❌ Nav norādīts client_id", mimetype="text/plain")
    return get_orders_last_12_months_internal(client_id)

def get_orders_last_12_months_internal(client_id):
    output = [f"📥 Meklējam dokumentus klientam ID {client_id} pēdējo 12 mēnešu laikā...\n"]

    now = datetime.now()
    start_date = (now - timedelta(days=365)).strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")

    list_url = f"https://go.paytraq.com/api/sales?APIKey={API_KEY}&APIToken={API_TOKEN}"
    try:
        response = requests.get(list_url)
        response.raise_for_status()
    except Exception as e:
        return Response(f"❌ Kļūda saņemot dokumentu sarakstu: {e}", mimetype="text/plain")

    root = ET.fromstring(response.content)
    all_docs = root.findall(".//Sale")
    count = 0
    totals_by_group = {}

    for sale in all_docs:
        doc_id = safe_text(sale, ".//DocumentID")
        doc_date = safe_text(sale, ".//DocumentDate")
        doc_client_id = safe_text(sale, ".//ClientID")

        if doc_client_id != client_id:
            continue
        if not (start_date <= doc_date <= end_date):
            continue

        count += 1
        output.append(f"\n📄 Apstrādājam dokumentu {doc_id} ({doc_date})")

        detail_url = f"https://go.paytraq.com/api/sale/{doc_id}?APIKey={API_KEY}&APIToken={API_TOKEN}"
        try:
            detail_response = requests.get(detail_url)
            detail_response.raise_for_status()
            detail_root = ET.fromstring(detail_response.content)
        except Exception as e:
            output.append(f"❌ Neizdevās iegūt dokumentu {doc_id}: {e}")
            continue

        line_items = detail_root.findall(".//LineItem")
        doc_group_totals = {}

        for item in line_items:
            item_id = safe_text(item, ".//ItemID")
            line_total = safe_text(item, "LineTotal", "0").replace(",", ".")
            try:
                line_total = float(line_total)
            except:
                continue

            group_name = "—"
            if item_id != "—":
                product_url = f"https://go.paytraq.com/api/product/{item_id}?APIToken={API_TOKEN}&APIKey={API_KEY}"
                try:
                    product_response = requests.get(product_url)
                    product_response.raise_for_status()
                    product_root = ET.fromstring(product_response.content)
                    group_name = safe_text(product_root, ".//Group/GroupName")
                except:
                    group_name = "—"

            doc_group_totals[group_name] = doc_group_totals.get(group_name, 0.0) + line_total

        for group, val in doc_group_totals.items():
            totals_by_group[group] = totals_by_group.get(group, 0.0) + val
            output.append(f"   📂 {group}: +{val:.2f} EUR")

    output.append("\n📊 KOPSUMMAS PA VISU PERIODU:")
    output.append("=" * 50)
    for group, total in totals_by_group.items():
        output.append(f"📂 {group}: {total:.2f} EUR")

    if count == 0:
        output.append("\n⚠️ Netika atrasts neviens dokuments šim klientam pēdējo 12 mēnešu laikā.")

    return Response("\n".join(output), mimetype="text/plain")

@app.route("/", methods=["GET"])
def index():
    return "✅ Serviss darbojas. Izmanto /paytraq-full-report, lai skatītu detalizētu atskaiti."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
