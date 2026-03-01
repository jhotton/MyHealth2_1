import streamlit as st

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