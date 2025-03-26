from flask import Flask, jsonify, Response
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import os

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY")
API_TOKEN = os.environ.get("API_TOKEN")


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "message": "Sveiki! Serviss darbojas. Izmanto /paytraq-full-report lai skatītu pēdējo dokumentu ar produktiem, klientu un grupām."
    })


@app.route("/paytraq-full-report", methods=["GET"])
def full_report():
    try:
        # 1. Iegūstam dokumentu sarakstu
        sales_url = f"https://go.paytraq.com/api/sales?APIKey={API_KEY}&APIToken={API_TOKEN}"
        sales_response = requests.get(sales_url)
        sales_response.raise_for_status()

        root = ET.fromstring(sales_response.content)
        first_doc = root.find(".//Document/DocumentID")
        if first_doc is None:
            return Response("❌ Nav atrasts neviens dokuments.", mimetype="text/plain")

        document_id = first_doc.text

        # 2. Iegūstam detalizēto dokumentu
        detail_url = f"https://go.paytraq.com/api/sale/{document_id}?APIKey={API_KEY}&APIToken={API_TOKEN}"
        detail_response = requests.get(detail_url)
        detail_response.raise_for_status()
        detail_root = ET.fromstring(detail_response.content)

        output = []

        # Dokumenta info
        doc_ref = detail_root.findtext(".//DocumentRef", default="—")
        client_name = detail_root.findtext(".//ClientName", default="—")

        output.append(f"✅ Jaunākais dokumenta ID: {document_id}")
        output.append(f"📄 Dokumenta Nr.: {doc_ref}")
        output.append(f"👤 Klients: {client_name}\n")

        # Produkti
        output.append("📦 Produkti dokumentā:")
        output.append("=" * 60)
        line_items = detail_root.findall(".//LineItem")
        item_groups = {}

        for idx, item in enumerate(line_items, 1):
            code = item.findtext(".//ItemCode", default="—")
            name = item.findtext(".//ItemName", default="—")
            qty = item.findtext("Qty", default="0")
            price = item.findtext("Price", default="0.00")
            total = item.findtext("LineTotal", default="0.00")
            unit = item.findtext(".//UnitName", default="gab.")
            item_id = item.findtext(".//ItemID", default="—")

            output.append(f"{idx}. {qty} x {name} ({code}) - {price} EUR [{unit}] → {total} EUR")
            output.append(f"      🔎 ItemID: {item_id}")

            # Grupas info
            try:
                product_url = f"https://go.paytraq.com/api/product/{item_id}?APIKey={API_KEY}&APIToken={API_TOKEN}"
                product_response = requests.get(product_url)
                product_response.raise_for_status()
                product_root = ET.fromstring(product_response.content)
                group_name = product_root.findtext(".//Group/GroupName", default="—").strip()
                total_float = float(total.replace(",", "."))

                item_groups[group_name] = item_groups.get(group_name, 0.0) + total_float
            except Exception as e:
                output.append(f"      ⚠️ Neizdevās iegūt grupu: {e}")

        # Grupas kopsavilkums
        output.append("\n📚 Produktu grupas dokumentā:")
        output.append("=" * 60)
        for group, total in item_groups.items():
            output.append(f"🗂️ {group}: {total:.2f} EUR")

        # Klienta papildus informācija
        client_id = detail_root.findtext(".//ClientID")
        client_url = f"https://go.paytraq.com/api/client/{client_id}?APIKey={API_KEY}&APIToken={API_TOKEN}"

        try:
            client_response = requests.get(client_url)
            client_response.raise_for_status()
            client_root = ET.fromstring(client_response.text)

            email = client_root.findtext(".//Email") or "—"
            phone = client_root.findtext(".//Phone") or "—"
            reg_number = client_root.findtext(".//RegNumber") or "—"
            address = client_root.findtext(".//Address") or "—"
            city = client_root.findtext(".//City") or "—"
            zip_code = client_root.findtext(".//Zip") or "—"
            country = client_root.findtext(".//Country") or "—"

            output.append("\n📇 Klienta informācija:")
            output.append("=" * 60)
            output.append(f"📛 Nosaukums: {client_name}")
            output.append(f"✉️ E-pasts: {email}")
            output.append(f"📞 Telefons: {phone}")
            output.append(f"🏢 Reģistrācijas nr.: {reg_number}")
            output.append(f"📍 Adrese: {address}, {city}, {zip_code}, {country}")
        except Exception as e:
            output.append(f"\n⚠️ Klienta info kļūda: {e}")

        return Response("\n".join(output), mimetype="text/plain")

    except Exception as e:
        return Response(f"❌ Kļūda: {str(e)}", mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
