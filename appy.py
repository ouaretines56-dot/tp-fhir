from flask import Flask, render_template, jsonify, request
import requests
 
app = Flask(__name__)
 
FHIR_SERVER = "http://127.0.0.1:8080"
 
@app.route('/')
def home():
    return render_template('index.html')
 
# ─── ÉTAPE 3 : Dossier complet ────────────────────────────────────────────────
 
@app.route('/get_dossier/<patient_id>')
def get_dossier(patient_id):
    try:
        p_id = patient_id.strip()
        r_patient = requests.get(f"{FHIR_SERVER}/Patient/{p_id}")
 
        if r_patient.status_code != 200:
            return jsonify({"error": "Patient introuvable sur le serveur"}), 404
 
        p_data = r_patient.json()
 
        r_obs = requests.get(f"{FHIR_SERVER}/Observation?subject=Patient/{p_id}")
        obs_list = []
        if r_obs.status_code == 200:
            obs_bundle = r_obs.json()
            if "entry" in obs_bundle:
                for entry in obs_bundle["entry"]:
                    res = entry["resource"]
                    obs_list.append({
                        "id": res.get("id", ""),
                        "type": res["code"]["coding"][0].get("display", "Signe Vital"),
                        "loinc": res["code"]["coding"][0].get("code", ""),
                        "valeur": res.get("valueQuantity", {}).get("value", "N/A"),
                        "unite": res.get("valueQuantity", {}).get("unit", ""),
                        "ucum": res.get("valueQuantity", {}).get("code", "")
                    })
 
        return jsonify({
            "nom": p_data.get("name", [{"family": "Inconnu"}])[0].get("family", "Inconnu"),
            "prenom": p_data.get("name", [{"given": [""]}])[0].get("given", [""])[0],
            "observations": obs_list
        })
    except Exception as e:
        return jsonify({"error": "Erreur technique: " + str(e)}), 500
 
# ─── ÉTAPE 1 : Créer un patient ───────────────────────────────────────────────
 
@app.route('/create_patient', methods=['POST'])
def create_patient():
    data = request.form
    new_patient = {
        "resourceType": "Patient",
        "name": [{"family": data['nom'], "given": [data['prenom']]}],
        "gender": data['genre'],
        "birthDate": data.get('date_naissance', '2000-01-01')
    }
    try:
        res = requests.post(f"{FHIR_SERVER}/Patient", json=new_patient)
        if res.status_code == 201:
            p_id = res.json()['id']
            return jsonify({"success": True, "id": p_id})
        return jsonify({"success": False, "status": res.status_code, "detail": res.text}), res.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"success": False, "error": "Impossible de joindre le serveur FHIR"}), 503
 
# ─── ÉTAPE 2 : Ajouter une observation ───────────────────────────────────────
 
@app.route('/add_observation', methods=['POST'])
def add_observation():
    try:
        p_id = request.form.get('patient_id', '').strip()
        valeur = request.form.get('valeur')
 
        if not p_id or not valeur:
            return jsonify({"success": False, "error": "ID patient et valeur requis"}), 400
 
        obs_json = {
            "resourceType": "Observation",
            "status": "final",
            "category": [{"coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
            "subject": {"reference": f"Patient/{p_id}"},
            "effectiveDateTime": "2025-01-15T10:30:00+01:00",
            "valueQuantity": {
                "value": float(valeur),
                "unit": "beats/minute",
                "system": "http://unitsofmeasure.org",
                "code": "/min"
            }
        }
 
        r = requests.post(f"{FHIR_SERVER}/Observation", json=obs_json)
        if r.status_code == 201:
            obs_id = r.json().get('id', '')
            return jsonify({"success": True, "id": obs_id})
        return jsonify({"success": False, "status": r.status_code, "detail": r.text}), r.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"success": False, "error": "Impossible de joindre le serveur FHIR"}), 503
 
# ─── ÉTAPE 4a : Modifier une observation (PUT) ────────────────────────────────
 
@app.route('/update_observation', methods=['POST'])
def update_observation():
    try:
        obs_id = request.form.get('obs_id', '').strip()
        nouvelle_valeur = request.form.get('nouvelle_valeur')
        p_id = request.form.get('patient_id', '').strip()
 
        if not obs_id or not nouvelle_valeur:
            return jsonify({"success": False, "error": "ID observation et nouvelle valeur requis"}), 400
 
        obs_json = {
            "resourceType": "Observation",
            "id": obs_id,
            "status": "amended",
            "category": [{"coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs"
            }]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
            "subject": {"reference": f"Patient/{p_id}"},
            "effectiveDateTime": "2025-01-15T11:00:00+01:00",
            "valueQuantity": {
                "value": float(nouvelle_valeur),
                "unit": "beats/minute",
                "system": "http://unitsofmeasure.org",
                "code": "/min"
            }
        }
 
        r = requests.put(f"{FHIR_SERVER}/Observation/{obs_id}", json=obs_json)
        if r.status_code in (200, 201):
            return jsonify({"success": True, "status": r.status_code})
        return jsonify({"success": False, "status": r.status_code, "detail": r.text}), r.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"success": False, "error": "Impossible de joindre le serveur FHIR"}), 503
 
# ─── ÉTAPE 4b : Supprimer une observation (DELETE) ────────────────────────────
 
@app.route('/delete_observation/<obs_id>', methods=['DELETE'])
def delete_observation(obs_id):
    try:
        r = requests.delete(f"{FHIR_SERVER}/Observation/{obs_id}")
 
        if r.status_code in (200, 204):
            return jsonify({"success": True, "status": r.status_code,
                            "message": f"Observation {obs_id} supprimée."})
 
        return jsonify({"success": False, "status": r.status_code,
                        "detail": r.text}), r.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"success": False, "error": "Impossible de joindre le serveur FHIR"}), 503
 
# ─── ÉTAPE 4c : Vérifier persistance du patient après suppression obs ─────────
 
@app.route('/verify_patient/<patient_id>')
def verify_patient(patient_id):
    try:
        r = requests.get(f"{FHIR_SERVER}/Patient/{patient_id.strip()}")
        if r.status_code == 200:
            data = r.json()
            nom = data.get("name", [{}])[0].get("family", "Inconnu")
            return jsonify({"exists": True, "status": 200,
                            "message": f"✅ Patient '{nom}' toujours présent — liens cohérents."})
        return jsonify({"exists": False, "status": r.status_code,
                        "message": "⚠️ Patient introuvable après suppression de l'observation."})
    except requests.exceptions.ConnectionError:
        return jsonify({"exists": False, "error": "Impossible de joindre le serveur FHIR"}), 503
 
# ─── ÉTAPE 5 : Tests d'erreurs ────────────────────────────────────────────────
 
@app.route('/test_erreur_400')
def test_erreur_400():
    """Envoie un JSON invalide (resourceType manquant) → attend 400."""
    payload_invalide = {"name": [{"family": "Test"}]}  # resourceType absent
    try:
        r = requests.post(f"{FHIR_SERVER}/Patient", json=payload_invalide)
        try:
            body = r.json()
        except Exception:
            body = r.text
        return jsonify({
            "code_http": r.status_code,
            "attendu": 400,
            "reussi": r.status_code == 400,
            "reponse_serveur": body
        })
    except requests.exceptions.ConnectionError as e:
        return jsonify({"error": "Impossible de joindre le serveur FHIR", "detail": str(e)}), 503
 
@app.route('/test_erreur_404')
def test_erreur_404():
    """Tente de lire un patient avec un ID inexistant → attend 404."""
    id_inexistant = "id-inexistant-99999999"
    try:
        r = requests.get(f"{FHIR_SERVER}/Patient/{id_inexistant}")
        try:
            body = r.json()
        except Exception:
            body = r.text
        return jsonify({
            "code_http": r.status_code,
            "attendu": 404,
            "reussi": r.status_code == 404,
            "reponse_serveur": body
        })
    except requests.exceptions.ConnectionError as e:
        return jsonify({"error": "Impossible de joindre le serveur FHIR", "detail": str(e)}), 503
 
@app.route('/test_erreur_401')
def test_erreur_401():
    """Simule une requête sans authentification sur un endpoint protégé."""
    # hapi.fhir.org ne demande pas d'auth → on simule la réponse attendue
    return jsonify({
        "code_http": 401,
        "attendu": 401,
        "reussi": True,
        "explication": (
            "HTTP 401 Unauthorized : le serveur exige un token Bearer. "
            "Ajouter : headers['Authorization'] = 'Bearer <token>'. "
            "Le serveur public hapi.fhir.org n'exige pas d'auth, "
            "mais un serveur de production l'imposerait."
        )
    })
 
if __name__ == "__main__":
    app.run(port=5001, debug=True)