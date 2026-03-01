import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go

st.set_page_config(page_title="Pression Artérielle", layout="wide")
st.title("🩺 Suivi de la Pression Artérielle")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1 : IMPORTATION XLSX ---
st.header("📥 Importer des données (Excel)")
uploaded_file = st.file_uploader("Choisissez votre fichier Excel (.xlsx)", type="xlsx")

if uploaded_file is not None:
    df_raw = pd.read_excel(uploaded_file)
    cols = df_raw.columns.tolist()
    
    st.write("### 1. Aperçu du fichier Excel sélectionné")
    st.dataframe(df_raw.head(3))

    st.info("Associez les colonnes de votre Excel aux champs de destination :")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sel_date = st.selectbox("Colonne Date", cols, index=0)
        sel_heure = st.selectbox("Colonne Heure", cols, index=1 if len(cols)>1 else 0)
    with c2:
        sel_sys = st.selectbox("Systolique (Max)", cols, index=2 if len(cols)>2 else 0)
        sel_dia = st.selectbox("Diastolique (Min)", cols, index=3 if len(cols)>3 else 0)
    with c3:
        sel_pouls = st.selectbox("Pouls", ["Aucun"] + cols)
        sel_n1 = st.selectbox("Note 1", ["Aucune"] + cols)
    with c4:
        sel_n2 = st.selectbox("Note 2", ["Aucune"] + cols)

    # --- PRÉPARATION ---
    try:
        df_prep = pd.DataFrame()
        # Fusion Date + Heure
        combined_dt = df_raw[sel_date].astype(str) + " " + df_raw[sel_heure].astype(str)
        df_prep['DateHeure'] = pd.to_datetime(combined_dt, errors='coerce')
        
        # Valeurs numériques
        df_prep['Systolique'] = pd.to_numeric(df_raw[sel_sys].astype(str).str.replace(',', '.'), errors='coerce')
        df_prep['Diastolique'] = pd.to_numeric(df_raw[sel_dia].astype(str).str.replace(',', '.'), errors='coerce')
        df_prep['Pouls'] = pd.to_numeric(df_raw[sel_pouls].astype(str).str.replace(',', '.'), errors='coerce') if sel_pouls != "Aucun" else 0
        df_prep['Note1'] = df_raw[sel_n1] if sel_n1 != "Aucune" else ""
        df_prep['Note2'] = df_raw[sel_n2] if sel_n2 != "Aucune" else ""
        
        df_prep = df_prep.dropna(subset=['DateHeure', 'Systolique'])

        st.write("### 2. Aperçu des données prêtes à être ajoutées")
        st.dataframe(df_prep.head(3))
        
    except Exception as e:
        st.error(f"Erreur de préparation : {e}")

    if st.button("🚀 Synchroniser avec PressionBrut"):
        with st.spinner("Mise à jour de la feuille PressionBrut..."):
            try:
                # Formatage pour l'envoi
                df_to_push = df_prep.copy()
                df_to_push['DateHeure'] = df_to_push['DateHeure'].dt.strftime('%Y-%m-%d %H:%M:%S')

                # Lecture de l'existant dans "PressionBrut"
                existing = conn.read(worksheet="PressionBrut", ttl=0)
                
                # Fusion et Dédoublonnage
                final = pd.concat([existing, df_to_push]).drop_duplicates(subset=['DateHeure'], keep='last')
                
                # Envoi
                conn.update(worksheet="PressionBrut", data=final)
                
                st.success("✅ Synchronisation réussie dans PressionBrut !")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Erreur lors de l'accès à la feuille 'PressionBrut' : {e}")

st.markdown("---")

# --- SECTION 2 : VISUALISATION ---
st.header("📈 Historique (depuis PressionBrut)")

try:
    df_plot = conn.read(worksheet="PressionBrut", ttl=0)
    if not df_plot.empty:
        df_plot['DateHeure'] = pd.to_datetime(df_plot['DateHeure'])
        df_plot = df_plot.sort_values('DateHeure')

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot['DateHeure'], y=df_plot['Systolique'], mode='lines+markers', name='Systolique'))
        fig.add_trace(go.Scatter(x=df_plot['DateHeure'], y=df_plot['Diastolique'], mode='lines+markers', name='Diastolique'))
        
        fig.update_layout(xaxis_title="Date", yaxis_title="mmHg", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
except:
    st.info("En attente de données dans PressionBrut.")