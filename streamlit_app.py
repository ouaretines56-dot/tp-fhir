import streamlit as st
import requests

# Serveur FHIR Public (obligatoire pour le web)
FHIR_SERVER = "http://hapi.fhir.org/baseR4"

st.title("🏥 Mon Dashboard FHIR Public")

menu = ["Créer Patient", "Ajouter Mesure", "Voir Dossier"]
choix = st.sidebar.selectbox("Actions", menu)

if choix == "Créer Patient":
    st.subheader("Étape 1 : Nouveau Patient")
    nom = st.text_input("Nom")
    prenom = st.text_input("Prénom")
    genre = st.selectbox("Genre", ["female", "male", "other", "unknown"])
    
    if st.button("Enregistrer"):
        payload = {"resourceType": "Patient", "name": [{"family": nom, "given": [prenom]}], "gender": genre}
        res = requests.post(f"{FHIR_SERVER}/Patient", json=payload)
        if res.status_code == 201:
            st.success(f"ID créé : {res.json()['id']}")

elif choix == "Ajouter Mesure":
    st.subheader("Étape 2 : Fréquence Cardiaque")
    p_id = st.text_input("ID du Patient")
    bpm = st.number_input("BPM", min_value=30, max_value=250, value=70)
    
    if st.button("Ajouter"):
        obs = {
            "resourceType": "Observation", "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
            "subject": {"reference": f"Patient/{p_id}"},
            "valueQuantity": {"value": bpm, "unit": "bpm", "system": "http://unitsofmeasure.org", "code": "/min"}
        }
        res = requests.post(f"{FHIR_SERVER}/Observation", json=obs)
        if res.status_code == 201:
            st.success("Mesure enregistrée !")

elif choix == "Voir Dossier":
    st.subheader("Étape 3 : Historique")
    p_id = st.text_input("Entrez l'ID")
    if st.button("Chercher"):
        r_pat = requests.get(f"{FHIR_SERVER}/Patient/{p_id}")
        if r_pat.status_code == 200:
            st.write(f"### Dossier de {r_pat.json()['name'][0]['family']}")
            r_obs = requests.get(f"{FHIR_SERVER}/Observation?patient={p_id}")
            if r_obs.status_code == 200 and "entry" in r_obs.json():
                for e in r_obs.json()["entry"]:
                    res = e["resource"]
                    st.info(f"❤️ {res['valueQuantity']['value']} bpm")
        else:
            st.error("ID introuvable")