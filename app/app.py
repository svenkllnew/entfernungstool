from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import openrouteservice
from openrouteservice import convert
import apikey  # Assuming apikey.py contains your OpenRouteService API key
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fahrtenbuch.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# OpenRouteService Client
ORS_API_KEY = apikey.KEY
ors_client = openrouteservice.Client(key=ORS_API_KEY)

# -------------------- MODEL -------------------- #
class Fahrt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kunde = db.Column(db.String(100))
    datum = db.Column(db.String(10))
    start = db.Column(db.String(100))
    ziel = db.Column(db.String(100))
    entfernung = db.Column(db.Float)
    fahrzeit = db.Column(db.Float)
    km_start = db.Column(db.Integer)
    km_ende = db.Column(db.Integer)
    gefahrene_km = db.Column(db.Integer)
    zweck = db.Column(db.String(200))
    partner = db.Column(db.String(100))
    kennzeichen = db.Column(db.String(50))
    fahrer = db.Column(db.String(100))

# -------------------- HILFSFUNKTION -------------------- #
def berechne_route(start_ort, ziel_ort):
    try:
        # Geocoding für Start/Ziel
        start_geo = ors_client.pelias_search(text=start_ort)["features"][0]["geometry"]["coordinates"]
        ziel_geo = ors_client.pelias_search(text=ziel_ort)["features"][0]["geometry"]["coordinates"]
        
        # Route berechnen
        route = ors_client.directions(
            coordinates=[start_geo, ziel_geo],
            profile='driving-car',
            format='geojson'
        )
        distanz_km = round(route["features"][0]["properties"]["summary"]["distance"] / 1000, 2)
        dauer_min = round(route["features"][0]["properties"]["summary"]["duration"] / 60, 1)
        return distanz_km, dauer_min
    except Exception as e:
        raise RuntimeError(f"Routing-Fehler: {e}")

# -------------------- INDEX -------------------- #
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            kunde = request.form["kunde"]
            datum = request.form["datum"]
            start = request.form["start"]
            ziel = request.form["ziel"]
            km_start = int(request.form["km_start"])
            km_ende = int(request.form["km_ende"])
            zweck = request.form["zweck"]
            partner = request.form.get("partner", "")
            kennzeichen = request.form["kennzeichen"]
            fahrer = request.form["fahrer"]

            # Strecke & Dauer via OpenRouteService
            entfernung, fahrzeit = berechne_route(start, ziel)
            gefahrene_km = km_ende - km_start

            result = {
                "kunde": kunde,
                "datum": datum,
                "start": start,
                "ziel": ziel,
                "entfernung": entfernung,
                "fahrzeit": fahrzeit,
                "km_start": km_start,
                "km_ende": km_ende,
                "gefahrene_km": gefahrene_km,
                "zweck": zweck,
                "partner": partner,
                "kennzeichen": kennzeichen,
                "fahrer": fahrer,
            }

            return render_template("index.html", result=result)
        except Exception as e:
            return render_template("index.html", error=f"Fehler: {e}")
    
    return render_template("index.html", current_date=datetime.now().strftime("%Y-%m-%d"))

# -------------------- SPEICHERN -------------------- #
@app.route("/save", methods=["POST"])
def save():
    try:
        fahrt = Fahrt(
            kunde=request.form["kunde"],
            datum=request.form["datum"],
            start=request.form["start"],
            ziel=request.form["ziel"],
            entfernung=float(request.form["entfernung"]),
            fahrzeit=float(request.form["fahrzeit"]),
            km_start=int(request.form["km_start"]),
            km_ende=int(request.form["km_ende"]),
            gefahrene_km=int(request.form["gefahrene_km"]),
            zweck=request.form["zweck"],
            partner=request.form.get("partner", ""),
            kennzeichen=request.form["kennzeichen"],
            fahrer=request.form["fahrer"]
        )
        db.session.add(fahrt)
        db.session.commit()
        return redirect(url_for("alle"))
    except Exception as e:
        return render_template("index.html", error=f"Fehler beim Speichern: {e}")

# -------------------- ALLE -------------------- #
@app.route("/alle")
def alle():
    fahrten = Fahrt.query.order_by(Fahrt.datum.desc()).all()
    return render_template("alle.html", fahrten=fahrten)

# --- AUTOCOMPLETE ENDPOINT ---
@app.route("/autocomplete")
def autocomplete():
    query = request.args.get('q', '')
    if len(query.strip()) < 2:
        return jsonify([])
    response = requests.get("https://nominatim.openstreetmap.org/search", params={
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": 5,
        "countrycodes": "de",
    }, headers={"User-Agent": "FahrtenbuchApp"})
    data = response.json()
    results = [item["display_name"] for item in data]
    return jsonify(results)

# -------------------- START -------------------- #
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
