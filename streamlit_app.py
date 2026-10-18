import requests
import streamlit as st

# Suivi unique des visites par session
if "visit_tracked" not in st.session_state:
  try:
    api_url = st.secrets["API_URL"]  # Doit être https://tracker.jhotton.ca/api/track-visit
    api_key = st.secrets["API_KEY"]

    payload = {
        "account_name": "jhotton",
        "app_name": "MyHealth",
        "page_name": "accueil",
    }
    headers = {"X-API-Key": api_key}

    # On lance la requête avec un timeout
    response = requests.post(api_url, json=payload, headers=headers, timeout=5)

    # Pour le test, affichons le résultat dans l'app
    if response.status_code == 200:
      st.session_state["visit_tracked"] = True
      st.success("Visite enregistrée avec succès !")
    else:
      st.error(
          f"Erreur API ({response.status_code}) : {response.text}"
      )  # <-- Très utile pour voir si c'est un 403 (clé incorrecte) ou autre

  except Exception as e:
    st.error(f"Impossible de joindre le tracker local : {e}")
    
# Définition des pages
main_page = st.Page("main.py", title="Accueil MyHealth", icon="🏠")
page_2 = st.Page("page2.py", title="Pression", icon="🩸")
page_3 = st.Page("page3.py", title="Glycémie", icon="🩸")
page_4 = st.Page("page4.py", title="Poids", icon="⚖️")
adminDB = st.Page("adminDB.py", title="Administration", icon="⚙️")

# Configuration de la navigation
pg = st.navigation([main_page, page_2, page_3, page_4, adminDB])

# Lancement
pg.run()
