from flask import Flask, render_template, jsonify, request
import requests

app = Flask(__name__)

# Ton serveur FHIR local tourne sur le 8080
FHIR_SERVER = "http://127.0.0.1:8080" 

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_dossier/<patient_id>')
def get_dossier(patient_id):
    try:
        p_id = patient_id.strip()
        
        # 1. On demande au serveur les infos du Patient
        r_patient = requests.get(f"{FHIR_SERVER}/Patient/{p_id}")
        
        # --- MODIFICATION ICI : On vérifie si ça existe AVANT de faire .json() ---
        if r_patient.status_code != 200:
            return jsonify({"error": "Patient introuvable sur le serveur"}), 404
            
        p_data = r_patient.json()

        # 2. On demande les observations liées à ce Patient
        r_obs = requests.get(f"{FHIR_SERVER}/Observation?subject=Patient/{p_id}")
        
        obs_list = []
        if r_obs.status_code == 200:
            obs_bundle = r_obs.json()
            if "entry" in obs_bundle:
                for entry in obs_bundle["entry"]:
                    res = entry["resource"]
                    obs_list.append({
                        "type": res["code"]["coding"][0].get("display", "Signe Vital"),
                        "valeur": res.get("valueQuantity", {}).get("value", "N/A"),
                        "unite": res.get("valueQuantity", {}).get("unit", "")
                    })

        return jsonify({
            "nom": p_data.get("name", [{"family": "Inconnu"}])[0].get("family", "Inconnu"),
            "prenom": p_data.get("name", [{"given": [""]}])[0].get("given", [""])[0],
            "observations": obs_list
        })
    except Exception as e:
        return jsonify({"error": "Erreur technique: " + str(e)}), 500

@app.route('/create_patient', methods=['POST'])
def create_patient():
    data = request.form
    new_patient = {
        "resourceType": "Patient",
        "name": [{"family": data['nom'], "given": [data['prenom']]}],
        "gender": data['genre'],
        "birthDate": data.get('date_naissance','2000-01-01')
    }
    res = requests.post(f"{FHIR_SERVER}/Patient", json=new_patient)
    if res.status_code == 201:
        p_id = res.json()['id']
        return f"<h1>Succès !</h1><p>Patient créé avec l'ID : <b>{p_id}</b>.</p><a href='/'>Retour</a>"
    return "Erreur lors de la création", 500

@app.route('/add_observation', methods=['POST'])
def add_observation():
    p_id = request.form.get('patient_id').strip()
    valeur = request.form.get('valeur')
    
    obs_json = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
        "subject": {"reference": f"Patient/{p_id}"},
        "valueQuantity": {"value": float(valeur), "unit": "bpm", "system": "http://unitsofmeasure.org", "code": "per min"}
    }
    
    r = requests.post(f"{FHIR_SERVER}/Observation", json=obs_json)
    if r.status_code == 201:
        return f"<h1>Mesure ajoutée !</h1><p>Donnée enregistrée pour le patient {p_id}.</p><a href='/'>Retour</a>"
    return "Erreur lors de l'ajout", 500

if __name__ == "__main__":
    app.run(port=5001, debug=True)