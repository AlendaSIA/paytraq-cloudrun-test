from flask import Flask, Response
import requests
import xml.etree.ElementTree as ET
import os
import re

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY")
API_TOKEN = os.environ.get("API_TOKEN")

def safe_text(el, path, default="—"):
    try:
        found = el.find(path)
        return found.text.strip() if found is not None and found.text else default
    except:
        return default

@app.route("/paytraq-full-report", methods=["GET"])
def paytraq_full_report():
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
    output = [f"✅ Jaunākais dokumenta ID: {document_id}"]

    detail_url = f"https://go.paytraq.com/api/sale/{document_id}?APIKey={API_KEY}&APIToken={API_TOKEN}"
    try:
        detail_response = requests.get(detail_url)
        detail_response.raise_for_status()
    except Exception as e:
        return Response(f"❌ Kļūda iegūstot dokumenta datus: {e}", mimetype="text/plain")

    detail_root = ET.fromstring(detail_response.content)

    doc_ref = safe_text(detail_root, ".//DocumentRef")
    client_name = safe_text(detail_root, ".//ClientName")
    comment = safe_text(detail_root, ".//Comment")
    output.append(f"📄 Dokumenta Nr.: {doc_ref}")
    output.append(f"🧾 Komentārs: {comment}")

    # Estimate no visa XML (ne tikai <Comment>)
    comment_raw = ET.tostring(detail_root, encoding='unicode')
    match = re.search(r'\bPAS/\d{4}/\d{5}\b', comment_raw)
    estimate_ref = match.group(0) if match else "—"
    output.append(f"📦 Estimate / Sales Order: {estimate_ref}")

    output.append(f"🧑 Klients: {client_name}")

    # Produkti
    output.append("\n📦 Produkti dokumentā:")
    output.append("=" * 60)
    line_items = detail_root.findall(".//LineItem")
    if not line_items:
        output.append("❌ Produkti nav atrasti.")
    else:
        for idx, item in enumerate(line_items, 1):
            code = safe_text(item, ".//ItemCode")
            name = safe_text(item, ".//ItemName")
            qty = safe_text(item, "Qty")
            price = safe_text(item, "Price")
            total = safe_text(item, "LineTotal")
            unit = safe_text(item, ".//UnitName", default="gab.")
            item_id = safe_text(item, ".//ItemID")

            output.append(f"{idx}. {qty} x {name} ({code}) - {price} EUR [{unit}] → {total} EUR")
            output.append(f"   🔎 ItemID: {item_id}")

    # Klienta info
    client_id = safe_text(detail_root, ".//ClientID")
    output.append(f"\n🔎 ClientID: {client_id}")
    client_url = f"https://go.paytraq.com/api/client/{client_id}?APIToken={API_TOKEN}&APIKey={API_KEY}"
    try:
        client_response = requests.get(client_url)
        client_response.raise_for_status()
        client_root = ET.fromstring(client_response.text)

        email = safe_text(client_root, ".//Email")
        phone = safe_text(client_root, ".//Phone")
        reg_number = safe_text(client_root, ".//RegNumber")
        address = safe_text(client_root, ".//Address")
        city = safe_text(client_root, ".//City")
        zip_code = safe_text(client_root, ".//Zip")
        country = safe_text(client_root, ".//Country")

        output.append("\n📇 Klienta informācija:")
        output.append("=" * 60)
        output.append(f"📛 Nosaukums: {client_name}")
        output.append(f"✉️ E-pasts: {email}")
        output.append(f"📞 Telefons: {phone}")
        output.append(f"🏢 Reģistrācijas nr.: {reg_number}")
        output.append(f"📍 Adrese: {address}")
        output.append(f"       Pilsēta: {city}")
        output.append(f"       Pasta indekss: {zip_code}")
        output.append(f"       Valsts: {country}")
    except Exception as e:
        output.append(f"❌ Neizdevās iegūt klienta datus: {e}")

    # Produktu grupas
    output.append("\n📊 Produktu grupas pasūtījumā ar kopsummām:")
    output.append("=" * 60)
    group_totals = {}
    for item in line_items:
        item_id = safe_text(item, ".//ItemID")
        line_total_raw = safe_text(item, "LineTotal")
        try:
            line_total = float(line_total_raw.replace(",", ".")) if line_total_raw not in ("", "—") else 0.0
        except:
            line_total = 0.0

        if item_id == "—":
            continue

        product_url = f"https://go.paytraq.com/api/product/{item_id}?APIToken={API_TOKEN}&APIKey={API_KEY}"
        try:
            response = requests.get(product_url)
            response.raise_for_status()
            product_root = ET.fromstring(response.content)
            group_name = safe_text(product_root, ".//Group/GroupName")
            group_totals[group_name] = group_totals.get(group_name, 0.0) + line_total
        except Exception as e:
            output.append(f"❌ Neizdevās iegūt grupas info produktam {item_id}: {e}")

    for group_name, total in group_totals.items():
        output.append(f"🗂️ {group_name}: {total:.2f} EUR")

    return Response("\n".join(output), mimetype="text/plain")

@app.route("/", methods=["GET"])
def index():
    return "✅ Serviss darbojas. Izmanto /paytraq-full-report, lai skatītu detalizētu atskaiti."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
