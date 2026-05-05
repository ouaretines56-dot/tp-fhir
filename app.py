from flask import Flask, render_template, jsonify, request
import requests

app = Flask(__name__)

# L'adresse de ton serveur HAPI FHIR local
FHIR_SERVER = "http://127.0.0.1:8080" 

@app.route('/')
def home():
    return render_template('index.html')

# --- ÉTAPE 1 : CRÉATION DU PATIENT ---
@app.route('/create_patient', methods=['POST'])
def create_patient():
    try:
        data = request.form
        # .get() évite le crash si 'genre' ou 'nom' manque
        nom = data.get('nom', 'Inconnu')
        prenom = data.get('prenom', 'Inconnu')
        genre = data.get('genre', 'unknown') 

        new_patient = {
            "resourceType": "Patient",
            "name": [{"family": nom, "given": [prenom]}],
            "gender": genre
        }
        
        res = requests.post(f"{FHIR_SERVER}/Patient", json=new_patient)
        
        if res.status_code == 201:
            p_id = res.json()['id']
            return f"<h1>Succès !</h1><p>Patient créé avec l'ID : <b>{p_id}</b></p><a href='/'>Retour au Dashboard</a>"
        return f"Erreur serveur FHIR : {res.status_code}", 500
    except Exception as e:
        return f"Erreur Flask (Création) : {str(e)}", 500

# --- ÉTAPE 2 : AJOUT D'UNE OBSERVATION ---
@app.route('/add_observation', methods=['POST'])
def add_observation():
    try:
        p_id = request.form.get('patient_id', '').strip()
        valeur = request.form.get('valeur')
        
        if not p_id or not valeur:
            return "ID ou Valeur manquante", 400

        obs_json = {
            "resourceType": "Observation",
            "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
            "subject": {"reference": f"Patient/{p_id}"},
            "valueQuantity": {
                "value": float(valeur), 
                "unit": "bpm", 
                "system": "http://unitsofmeasure.org", 
                "code": "/min"
            }
        }
        
        r = requests.post(f"{FHIR_SERVER}/Observation", json=obs_json)
        if r.status_code == 201:
            return f"<h1>Mesure ajoutée !</h1><p>Enregistré pour {p_id}.</p><a href='/'>Retour</a>"
        return f"Erreur lors de l'ajout : {r.text}", 500
    except Exception as e:
        return f"Erreur technique (Observation) : {str(e)}", 500

# --- ÉTAPE 3 : RÉCUPÉRATION DU DOSSIER (VERSION BLINDÉE) ---
@app.route('/get_dossier/<patient_id>')
def get_dossier(patient_id):
    try:
        # 1. Nettoyage de l'ID (on enlève les espaces qui font rater les requêtes)
        clean_id = patient_id.strip()
        print(f"--- Tentative de récupération pour l'ID : {clean_id} ---")

        # 2. Requête Patient
        r_pat = requests.get(f"{FHIR_SERVER}/Patient/{clean_id}")
        if r_pat.status_code != 200:
            print(f"Patient {clean_id} introuvable.")
            return jsonify({"error": "Patient introuvable"}), 404
        
        p_data = r_pat.json()

        # 3. Requête Observations (on cherche par l'ID du patient)
        r_obs = requests.get(f"{FHIR_SERVER}/Observation?patient={clean_id}")
        
        obs_list = []
        if r_obs.status_code == 200:
            bundle = r_obs.json()
            if "entry" in bundle:
                for entry in bundle["entry"]:
                    res = entry["resource"]
                    # On sécurise l'extraction pour éviter les crashs si un champ manque
                    label = "Signe Vital"
                    try:
                        label = res["code"]["coding"][0].get("display", "Mesure")
                    except: pass
                    
                    val = res.get("valueQuantity", {}).get("value", "N/A")
                    unit = res.get("valueQuantity", {}).get("unit", "")
                    
                    obs_list.append({"type": label, "valeur": val, "unite": unit})

        # 4. Extraction sécurisée du nom
        nom_famille = "Inconnu"
        prenom_patient = ""
        if "name" in p_data and len(p_data["name"]) > 0:
            nom_famille = p_data["name"][0].get("family", "Inconnu")
            prenom_patient = p_data["name"][0].get("given", [""])[0]

        print(f"Succès : Dossier de {prenom_patient} {nom_famille} envoyé.")
        return jsonify({
            "nom": nom_famille,
            "prenom": prenom_patient,
            "observations": obs_list
        })

    except Exception as e:
        print(f"CRASH ÉTAPE 3 : {str(e)}")
        return jsonify({"error": "Erreur interne du serveur"}), 500

if __name__ == "__main__":
    # Port 5001 pour ne pas être bloqué par AirPlay sur Mac
    app.run(port=5001, debug=True)