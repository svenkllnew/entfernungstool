from flask import Flask, render_template, request, redirect, url_for, session
import openrouteservice
from geopy.geocoders import Nominatim
import openpyxl
import os
import platform
import subprocess
import apikey

app = Flask(__name__)
app.secret_key = 'geheim123' # benötigt für session

API_KEY = apikey.KEY
EXCEL_DATEI = "fahrten.xlsx"

def speichere_in_excel(kunde, datum, start, ziel, entfernung, fahrzeit):
    if os.path.exists(EXCEL_DATEI):
        wb = openpyxl.load_workbook(EXCEL_DATEI)
        ws = wb.active
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Kunde", "Datum", "Startort", "Zielort", "Entfernung (km)", "Fahrzeit (Minuten)"])

    ws.append([kunde, datum, start, ziel, entfernung, fahrzeit])
    wb.save(EXCEL_DATEI)

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    result = {}

    if request.method == "POST":
        kunde = request.form.get("kunde")
        datum = request.form.get("datum")
        start = request.form.get("start")
        ziel = request.form.get("ziel")

        if not kunde or not datum or not start or not ziel:
            error = "Bitte alle Felder ausfüllen."
        else:
            try:
                geolocator = Nominatim(user_agent="entfernungsrechner")
                start_loc = geolocator.geocode(start)
                ziel_loc = geolocator.geocode(ziel)

                if not start_loc or not ziel_loc:
                    error = "Ort nicht gefunden."
                else:
                    coords = [
                        (start_loc.longitude, start_loc.latitude),
                        (ziel_loc.longitude, ziel_loc.latitude)
                    ]

                    client = openrouteservice.Client(key=API_KEY)
                    route = client.directions(coords, profile='driving-car', format='geojson')

                    props = route['features'][0]['properties']['segments'][0]
                    entfernung = round(props['distance'] / 1000, 2)
                    fahrzeit = round(props['duration'] / 60, 1)

                    result = {
                        "kunde": kunde,
                        "datum": datum,
                        "start": start,
                        "ziel": ziel,
                        "entfernung": entfernung,
                        "fahrzeit": fahrzeit
                    }

                    # Temporär speichern in Session
                    session["result"] = result

            except Exception as e:
                error = f"Fehler bei der Berechnung: {str(e)}"

    return render_template("index.html", result=session.get("result"), error=error, api_key=API_KEY)

@app.route("/save", methods=["POST"])
def save():
    result = session.get("result")
    if result:
        speichere_in_excel(**result)
        session.pop("result", None)
        return "Daten wurden gespeichert in fahrten.xlsx"
    else:
        return "Keine Daten zum Speichern vorhanden."

@app.route("/open_excel")
def open_excel():
    try:
        if os.path.exists(EXCEL_DATEI):
            if platform.system() == "Windows":
                os.startfile(EXCEL_DATEI)
            elif platform.system() == "Darwin":
                subprocess.call(["open", EXCEL_DATEI])
            elif platform.system() == "Linux":
                subprocess.call(["xdg-open", EXCEL_DATEI])
            return "Excel-Datei wurde geöffnet."
        else:
            return "Excel-Datei existiert noch nicht."
    except Exception as e:
        return f"Fehler beim Öffnen: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True)
