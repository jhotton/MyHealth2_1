import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Suivi du Poids", layout="wide")
st.title("⚖️ Suivi du Poids")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1 : IMPORTATION ---
st.header("📥 Importer des données")
uploaded_file = st.file_uploader("Choisissez un fichier (CSV ou XLSX)", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        
        # LECTURE AVEC CORRECTION DU DÉCALAGE
        if file_extension == '.xlsx':
            # On saute la 1ère ligne et on s'assure de ne pas prendre d'index
            df_raw = pd.read_excel(uploaded_file, skiprows=1)
        else:
            # Pour le CSV, index_col=False empêche de décaler les colonnes vers la gauche
            # si la première colonne est vide ou numérique
            df_raw = pd.read_csv(uploaded_file, skiprows=1, sep=',', index_col=False)
        
        # Nettoyage immédiat des colonnes nommées "Unnamed" (souvent dues à des virgules en trop)
        df_raw = df_raw.loc[:, ~df_raw.columns.str.contains('^Unnamed')]
        
        cols = df_raw.columns.tolist()
        
        st.write("### 1. Aperçu du fichier (Vérifiez l'alignement)")
        st.dataframe(df_raw.head(5))

        st.info("Associez les colonnes de votre fichier :")
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_date = st.selectbox("Date et Heure", cols, index=0)
        with c2:
            # On cherche intelligemment si "kg" est dans le nom d'une colonne pour aider l'index
            idx_kg = next((i for i, c in enumerate(cols) if 'kg' in c.lower()), 0) + 1
            sel_kg = st.selectbox("Poids (kg)", ["Aucune"] + cols, index=idx_kg if idx_kg <= len(cols) else 0)
        with c3:
            sel_lbs = st.selectbox("Poids (lbs)", ["Aucune"] + cols)

        if st.button("🚀 Synchroniser le Poids"):
            df_prep = pd.DataFrame()
            
            # Conversion Date
            df_prep['DateHeure'] = pd.to_datetime(df_raw[sel_date], errors='coerce')
            
            # Conversion Numérique (on enlève les espaces éventuels pour éviter les erreurs)
            def clean_num(val):
                if pd.isna(val): return None
                return float(str(val).replace(',', '.').replace(' ', ''))

            v_kg = df_raw[sel_kg].apply(clean_num) if sel_kg != "Aucune" else pd.Series([None]*len(df_raw))
            v_lbs = df_raw[sel_lbs].apply(clean_num) if sel_lbs != "Aucune" else pd.Series([None]*len(df_raw))

            # Calcul croisé des unités
            v_lbs = v_lbs.fillna(v_kg * 2.20462)
            v_kg = v_kg.fillna(v_lbs / 2.20462)

            df_prep['Poids_kg'] = v_kg
            df_prep['Poids_lbs'] = v_lbs

            # On ne garde que ce qui est valide
            df_prep = df_prep.dropna(subset=['DateHeure', 'Poids_kg'])
            
            if not df_prep.empty:
                df_to_push = df_prep.copy()
                df_to_push['DateHeure'] = df_to_push['DateHeure'].dt.strftime('%Y-%m-%d %H:%M:%S')

                existing = conn.read(worksheet="poids", ttl=0)
                final = pd.concat([existing, df_to_push]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="poids", data=final)
                
                st.success(f"✅ {len(df_to_push)} mesures synchronisées !")
                st.cache_data.clear()
            else:
                st.error("Données invalides. Vérifiez si les colonnes choisies contiennent bien des chiffres.")

    except Exception as e:
        st.error(f"Erreur lors de la lecture : {e}")