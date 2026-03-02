import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Suivi du Poids", layout="wide")
st.title("⚖️ Suivi du Poids (Multi-format)")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1 : IMPORTATION ---
st.header("📥 Importer des données")
uploaded_file = st.file_uploader("Choisissez un fichier (CSV ou XLSX)", type=["csv", "xlsx"])

if uploaded_file is not None:
    # Détection du format et lecture
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    if file_extension == '.xlsx':
        df_raw = pd.read_excel(uploaded_file)
    else:
        df_raw = pd.read_csv(uploaded_file)
    
    cols = df_raw.columns.tolist()
    st.write("### 1. Aperçu du fichier lu")
    st.dataframe(df_raw.head(3))

    st.info("Associez les colonnes :")
    c1, c2, c3 = st.columns(3)
    with c1:
        sel_date = st.selectbox("Colonne Date/Heure", cols, index=0)
    with c2:
        sel_kg = st.selectbox("Colonne Poids (kg)", ["Aucune"] + cols)
    with c3:
        sel_lbs = st.selectbox("Colonne Poids (lbs)", ["Aucune"] + cols)

    if st.button("🚀 Synchroniser le Poids"):
        try:
            df_prep = pd.DataFrame()
            
            # 1. Traitement Date
            df_prep['DateHeure'] = pd.to_datetime(df_raw[sel_date], errors='coerce')
            
            # 2. Récupération des valeurs numériques
            v_kg = pd.to_numeric(df_raw[sel_kg].astype(str).str.replace(',', '.'), errors='coerce') if sel_kg != "Aucune" else pd.Series([None]*len(df_raw))
            v_lbs = pd.to_numeric(df_raw[sel_lbs].astype(str).str.replace(',', '.'), errors='coerce') if sel_lbs != "Aucune" else pd.Series([None]*len(df_raw))

            # 3. LOGIQUE DE CONVERSION (Si l'un manque, on calcule l'autre)
            # kg -> lbs
            v_lbs = v_lbs.fillna(v_kg * 2.20462)
            # lbs -> kg
            v_kg = v_kg.fillna(v_lbs / 2.20462)

            df_prep['Poids_kg'] = v_kg
            df_prep['Poids_lbs'] = v_lbs

            # Nettoyage des lignes sans date ou sans poids
            df_prep = df_prep.dropna(subset=['DateHeure', 'Poids_kg'])
            
            st.write("### 2. Données prêtes pour le Cloud")
            st.dataframe(df_prep.head(3))

            with st.spinner("Mise à jour de la Google Sheet..."):
                # Formatage date pour l'envoi
                df_to_push = df_prep.copy()
                df_to_push['DateHeure'] = df_to_push['DateHeure'].dt.strftime('%Y-%m-%d %H:%M:%S')

                # Lecture de l'onglet "poids"
                try:
                    existing = conn.read(worksheet="poids", ttl=0)
                except:
                    existing = pd.DataFrame(columns=['DateHeure', 'Poids_kg', 'Poids_lbs'])

                final = pd.concat([existing, df_to_push]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="poids", data=final)
                
                st.success(f"✅ {len(df_to_push)} mesures de poids synchronisées !")
                st.cache_data.clear()

        except Exception as e:
            st.error(f"Erreur technique : {e}")

st.markdown("---")

# --- SECTION 2 : VISUALISATION ---
st.header("📈 Courbe de Poids")

try:
    df_poids = conn.read(worksheet="poids", ttl=0)
    if not df_poids.empty:
        df_poids['DateHeure'] = pd.to_datetime(df_poids['DateHeure'])
        df_poids = df_poids.sort_values('DateHeure')

        unit_disp = st.radio("Afficher le graphique en :", ["Kilogrammes (kg)", "Livres (lbs)"], horizontal=True)
        col_plot = 'Poids_kg' if unit_disp == "Kilogrammes (kg)" else 'Poids_lbs'
        suffix = "kg" if col_plot == 'Poids_kg' else "lbs"

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_poids['DateHeure'], 
            y=df_poids[col_plot], 
            mode='lines+markers',
            name=f'Poids ({suffix})',
            line=dict(color='#00B4D8', width=3),
            marker=dict(size=8)
        ))

        fig.update_layout(
            template="plotly_dark",
            xaxis_title="Date",
            yaxis_title=f"Masse ({suffix})",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Voir le tableau historique"):
            st.dataframe(df_poids, use_container_width=True)
except:
    st.info("Aucune donnée de poids disponible.")