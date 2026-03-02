import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
import os

# Toujours configurer la page en premier
st.set_page_config(page_title="Suivi du Poids", layout="wide")
st.title("⚖️ Suivi du Poids")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1 : IMPORTATION ---
st.header("📥 Importer des données")
uploaded_file = st.file_uploader("Choisissez un fichier (CSV ou XLSX)", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        
        if file_extension == '.xlsx':
            df_raw = pd.read_excel(uploaded_file, skiprows=1)
        else:
            df_raw = pd.read_csv(uploaded_file, skiprows=1, sep=',', index_col=False)
        
        # Nettoyage des colonnes fantômes
        df_raw = df_raw.loc[:, ~df_raw.columns.str.contains('^Unnamed')]
        cols = df_raw.columns.tolist()
        
        st.write("### 1. Aperçu du fichier lu")
        st.dataframe(df_raw.head(3))

        st.info("Associez les colonnes :")
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_date = st.selectbox("Date et Heure", cols, index=0)
        with c2:
            sel_kg = st.selectbox("Poids (kg)", ["Aucune"] + cols)
        with c3:
            sel_lbs = st.selectbox("Poids (lbs)", ["Aucune"] + cols)

        if st.button("🚀 Synchroniser le Poids"):
            df_prep = pd.DataFrame()
            df_prep['DateHeure'] = pd.to_datetime(df_raw[sel_date], errors='coerce')
            
            def clean_num(val):
                if pd.isna(val): return None
                return float(str(val).replace(',', '.').replace(' ', ''))

            v_kg = df_raw[sel_kg].apply(clean_num) if sel_kg != "Aucune" else pd.Series([None]*len(df_raw))
            v_lbs = df_raw[sel_lbs].apply(clean_num) if sel_lbs != "Aucune" else pd.Series([None]*len(df_raw))

            # Calcul croisé
            v_lbs = v_lbs.fillna(v_kg * 2.20462)
            v_kg = v_kg.fillna(v_lbs / 2.20462)

            df_prep['Poids_kg'] = v_kg
            df_prep['Poids_lbs'] = v_lbs
            df_prep = df_prep.dropna(subset=['DateHeure', 'Poids_kg'])
            
            if not df_prep.empty:
                df_to_push = df_prep.copy()
                df_to_push['DateHeure'] = df_to_push['DateHeure'].dt.strftime('%Y-%m-%d %H:%M:%S')

                existing = conn.read(worksheet="poids", ttl=0)
                final = pd.concat([existing, df_to_push]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="poids", data=final)
                
                st.success(f"✅ {len(df_to_push)} mesures synchronisées !")
                st.cache_data.clear()

    except Exception as e:
        st.error(f"Erreur lors de la lecture : {e}")

st.markdown("---")

# --- SECTION 2 : VISUALISATION ---
st.header("📈 Évolution du Poids")

try:
    df_plot = conn.read(worksheet="poids", ttl=0)
    if not df_plot.empty:
        df_plot['DateHeure'] = pd.to_datetime(df_plot['DateHeure'])
        df_plot = df_plot.sort_values('DateHeure')

        c1, c2 = st.columns([1, 3])
        with c1:
            unit_choice = st.radio("Unité :", ["kg", "lbs"], horizontal=True)
        
        col_to_show = 'Poids_kg' if unit_choice == "kg" else 'Poids_lbs'
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_plot['DateHeure'], 
            y=df_plot[col_to_show],
            mode='lines+markers',
            line=dict(color='#2ec4b6', width=3)
        ))
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)
except:
    st.info("En attente de données...")