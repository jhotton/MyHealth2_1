import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go

st.set_page_config(page_title="Pression Artérielle", layout="wide")
st.title("🩺 Suivi de la Pression Artérielle")

# Connexion à Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1 : IMPORTATION XLSX ---
st.header("📥 Importer des données (Excel)")
uploaded_file = st.file_uploader("Choisissez votre fichier Excel (.xlsx)", type="xlsx")

if uploaded_file is not None:
    # Lecture du fichier Excel
    df_raw = pd.read_excel(uploaded_file)
    cols = df_raw.columns.tolist()
    
    st.info("Associez les colonnes de votre Excel aux champs de destination :")
    
    # Interface de mapping
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

    if st.button("🚀 Synchroniser avec Google Sheets"):
        try:
            df_to_push = pd.DataFrame()
            
            # --- FUSION DATE ET HEURE ---
            # On combine les deux colonnes en une chaîne, puis on convertit en datetime
            combined_dt = df_raw[sel_date].astype(str) + " " + df_raw[sel_heure].astype(str)
            df_to_push['DateHeure'] = pd.to_datetime(combined_dt, errors='coerce')
            
            # --- NETTOYAGE NUMÉRIQUE ---
            df_to_push['Systolique'] = pd.to_numeric(df_raw[sel_sys].astype(str).str.replace(',', '.'), errors='coerce')
            df_to_push['Diastolique'] = pd.to_numeric(df_raw[sel_dia].astype(str).str.replace(',', '.'), errors='coerce')
            
            if sel_pouls != "Aucun":
                df_to_push['Pouls'] = pd.to_numeric(df_raw[sel_pouls].astype(str).str.replace(',', '.'), errors='coerce')
            else:
                df_to_push['Pouls'] = 0

            # --- NOTES ---
            df_to_push['Note1'] = df_raw[sel_n1] if sel_n1 != "Aucune" else ""
            df_to_push['Note2'] = df_raw[sel_n2] if sel_n2 != "Aucune" else ""

            # Suppression des lignes invalides (date ou systolique manquante)
            df_to_push = df_to_push.dropna(subset=['DateHeure', 'Systolique'])
            
            # Formatage pour Google Sheets
            df_to_push['DateHeure'] = df_to_push['DateHeure'].dt.strftime('%Y-%m-%d %H:%M:%S')

            # --- ENVOI ---
            with st.spinner("Mise à jour du Cloud..."):
                try:
                    existing = conn.read(worksheet="pression", ttl=0)
                except:
                    existing = pd.DataFrame(columns=['DateHeure', 'Systolique', 'Diastolique', 'Pouls', 'Note1', 'Note2'])

                final = pd.concat([existing, df_to_push]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="pression", data=final)
                
                st.success(f"✅ {len(df_to_push)} mesures de pression synchronisées !")
                st.cache_data.clear()

        except Exception as e:
            st.error(f"Erreur technique : {e}")

st.markdown("---")

# --- SECTION 2 : GRAPHIQUE ---
st.header("📈 Historique de Pression")

try:
    df_plot = conn.read(worksheet="pression", ttl=0)
    if not df_plot.empty:
        df_plot['DateHeure'] = pd.to_datetime(df_plot['DateHeure'])
        df_plot = df_plot.sort_values('DateHeure')

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot['DateHeure'], y=df_plot['Systolique'], mode='lines+markers', name='Systolique (Max)'))
        fig.add_trace(go.Scatter(x=df_plot['DateHeure'], y=df_plot['Diastolique'], mode='lines+markers', name='Diastolique (Min)'))
        
        fig.update_layout(xaxis_title="Date", yaxis_title="mmHg", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📋 Données enregistrées")
        st.dataframe(df_plot, use_container_width=True)
except:
    st.info("Aucune donnée de pression à afficher.")