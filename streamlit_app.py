import requests
import streamlit as st

# Suivi unique des visites par session
if "visit_tracked" not in st.session_state:
  try:
    api_url = st.secrets["API_URL"]
    api_key = st.secrets["API_KEY"]

    # Récupération optionnelle du User-Agent si disponible
    # (Streamlit ne l'expose pas nativement facilement, on peut mettre une valeur par défaut ou le header HTTP)
    payload = {
        "account_name": "jhotton",  # Le nom de votre compte Streamlit
        "app_name": "MyHealth",  # Le nom de l'application
        "page_name": "accueil",  # Le nom de la page (ou onglet)
    }

    headers = {"X-API-Key": api_key}

    response = requests.post(api_url, json=payload, headers=headers, timeout=3)
    if response.status_code == 200:
      st.session_state["visit_tracked"] = True
  except Exception as e:
    # On attrape l'erreur pour ne jamais bloquer l'application si le serveur local est injoignable
    pass
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
