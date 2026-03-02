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
        # Détection du format et lecture en ignorant la 1ère ligne
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        
        if file_extension == '.xlsx':
            # skiprows=1 pour ignorer la ligne de titre/metadata initiale
            df_raw = pd.read_excel(uploaded_file, skiprows=1)
        else:
            # sep=',' et skiprows=1 pour le format CSV spécifique
            df_raw = pd.read_csv(uploaded_file, skiprows=1, sep=',')
        
        cols = df_raw.columns.tolist()
        st.write("### 1. Aperçu du fichier lu (après avoir ignoré la 1ère ligne)")
        st.dataframe(df_raw.head(3))

        st.info("Associez les colonnes de votre fichier :")
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_date = st.selectbox("Date et Heure", cols, index=0)
        with c2:
            sel_kg = st.selectbox("Poids (kg)", ["Aucune"] + cols)
        with c3:
            sel_lbs = st.selectbox("Poids (lbs)", ["Aucune"] + cols)

        if st.button("🚀 Synchroniser le Poids"):
            df_prep = pd.DataFrame()
            
            # 1. Traitement Date (Format standard attendu après nettoyage éventuel)
            df_prep['DateHeure'] = pd.to_datetime(df_raw[sel_date], errors='coerce')
            
            # 2. Valeurs numériques (gestion de la virgule décimale)
            v_kg = pd.to_numeric(df_raw[sel_kg].astype(str).str.replace(',', '.'), errors='coerce') if sel_kg != "Aucune" else pd.Series([None]*len(df_raw))
            v_lbs = pd.to_numeric(df_raw[sel_lbs].astype(str).str.replace(',', '.'), errors='coerce') if sel_lbs != "Aucune" else pd.Series([None]*len(df_raw))

            # 3. Logique de conversion automatique
            # Si kg est présent mais pas lbs
            v_lbs = v_lbs.fillna(v_kg * 2.20462)
            # Si lbs est présent mais pas kg
            v_kg = v_kg.fillna(v_lbs / 2.20462)

            df_prep['Poids_kg'] = v_kg
            df_prep['Poids_lbs'] = v_lbs

            # Nettoyage
            df_prep = df_prep.dropna(subset=['DateHeure', 'Poids_kg'])
            
            if not df_prep.empty:
                # Formatage pour Google Sheets
                df_to_push = df_prep.copy()
                df_to_push['DateHeure'] = df_to_push['DateHeure'].dt.strftime('%Y-%m-%d %H:%M:%S')

                existing = conn.read(worksheet="poids", ttl=0)
                final = pd.concat([existing, df_to_push]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="poids", data=final)
                
                st.success(f"✅ {len(df_to_push)} mesures synchronisées !")
                st.cache_data.clear()
            else:
                st.error("Aucune donnée valide trouvée. Vérifiez le format des dates et des nombres.")

    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {e}")

st.markdown("---")

# --- SECTION 2 : VISUALISATION ---
st.header("📈 Courbe de Poids")

try:
    df_poids = conn.read(worksheet="poids", ttl=0)
    if not df_poids.empty:
        df_poids['DateHeure'] = pd.to_datetime(df_poids['DateHeure'])
        df_poids = df_poids.sort_values('DateHeure')

        unit_disp = st.radio("Unité d'affichage :", ["kg", "lbs"], horizontal=True)
        col_plot = 'Poids_kg' if unit_disp == "kg" else 'Poids_lbs'

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_poids['DateHeure'], 
            y=df_poids[col_plot], 
            mode='lines+markers',
            name=f'Poids ({unit_disp})',
            line=dict(color='#2ec4b6', width=3)
        ))

        fig.update_layout(template="plotly_dark", xaxis_title="Date", yaxis_title=f"Poids ({unit_disp})")
        st.plotly_chart(fig, use_container_width=True)
except:
    st.info("Aucune donnée à afficher.")