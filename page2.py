import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Pression Artérielle", layout="wide")
st.title("🩺 Suivi et Synthèse de la Pression & Pouls")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1 : IMPORTATION ---
st.header("📥 Importer et Synthétiser")
uploaded_file = st.file_uploader("Choisissez votre fichier Excel (.xlsx)", type="xlsx")

if uploaded_file is not None:
    df_raw = pd.read_excel(uploaded_file)
    cols = df_raw.columns.tolist()
    
    st.info("Associez les colonnes de votre Excel :")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sel_date = st.selectbox("Date", cols, index=0)
        sel_heure = st.selectbox("Heure", cols, index=1 if len(cols)>1 else 0)
    with c2:
        sel_sys = st.selectbox("Systolique (Max)", cols, index=2 if len(cols)>2 else 0)
        sel_dia = st.selectbox("Diastolique (Min)", cols, index=3 if len(cols)>3 else 0)
    with c3:
        sel_pouls = st.selectbox("Pouls", cols, index=4 if len(cols)>4 else 0)
    with c4:
        sel_n1 = st.selectbox("Note 1", ["Aucune"] + cols)

    # --- TRAITEMENT DES DONNÉES ---
    try:
        df_prep = pd.DataFrame()
        combined_dt = df_raw[sel_date].astype(str) + " " + df_raw[sel_heure].astype(str)
        df_prep['DateHeure'] = pd.to_datetime(combined_dt, errors='coerce')
        df_prep['Systolique'] = pd.to_numeric(df_raw[sel_sys].astype(str).str.replace(',', '.'), errors='coerce')
        df_prep['Diastolique'] = pd.to_numeric(df_raw[sel_dia].astype(str).str.replace(',', '.'), errors='coerce')
        df_prep['Pouls'] = pd.to_numeric(df_raw[sel_pouls].astype(str).str.replace(',', '.'), errors='coerce')
        df_prep['Note1'] = df_raw[sel_n1] if sel_n1 != "Aucune" else ""
        
        df_prep = df_prep.dropna(subset=['DateHeure', 'Systolique'])

        if st.button("🚀 Synchroniser (Brut + Synthèse 30min)"):
            with st.spinner("Traitement et envoi..."):
                # 1. Mise à jour PressionBrut
                df_brut_push = df_prep.copy()
                df_brut_push['DateHeure'] = df_brut_push['DateHeure'].dt.strftime('%Y-%m-%d %H:%M:%S')
                existing_brut = conn.read(worksheet="PressionBrut", ttl=0)
                final_brut = pd.concat([existing_brut, df_brut_push]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="PressionBrut", data=final_brut)

                # 2. Logique de Synthèse (Min Sys par 30 min)
                df_syn = df_prep.copy().sort_values('DateHeure')
                df_syn['Groupe30'] = df_syn['DateHeure'].dt.floor('30min')
                idx_min_sys = df_syn.groupby('Groupe30')['Systolique'].idxmin()
                df_final_syn = df_syn.loc[idx_min_sys].drop(columns=['Groupe30'])
                df_final_syn['DateHeure'] = df_final_syn['DateHeure'].dt.strftime('%Y-%m-%d %H:%M:%S')

                # 3. Mise à jour PressionSynthese
                try:
                    existing_syn = conn.read(worksheet="PressionSynthese", ttl=0)
                except:
                    existing_syn = pd.DataFrame(columns=df_final_syn.columns)
                
                final_syn = pd.concat([existing_syn, df_final_syn]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="PressionSynthese", data=final_syn)

                st.success("✅ Données brutes et Synthèse à jour !")
                st.cache_data.clear()

    except Exception as e:
        st.error(f"Erreur de traitement : {e}")

st.markdown("---")

# --- SECTION VISUALISATION ---
st.header("📈 Tableaux de bord")

try:
    df_p = conn.read(worksheet="PressionSynthese", ttl=0)
    if not df_p.empty:
        df_p['DateHeure'] = pd.to_datetime(df_p['DateHeure'])
        df_p = df_p.sort_values('DateHeure')

        # --- Graphique 1 : Pression Artérielle ---
        st.subheader("Évolution de la Pression (Synthèse)")
        fig_pres = go.Figure()
        fig_pres.add_trace(go.Scatter(x=df_p['DateHeure'], y=df_p['Systolique'], name='Systolique', line=dict(color='#FF4B4B', width=3)))
        fig_pres.add_trace(go.Scatter(x=df_p['DateHeure'], y=df_p['Diastolique'], name='Diastolique', line=dict(color='#00CC96', width=2)))
        fig_pres.update_layout(height=400, template="plotly_dark", xaxis_title="Date", yaxis_title="mmHg")
        st.plotly_chart(fig_pres, use_container_width=True)

        # --- Graphique 2 : Pouls ---
        st.subheader("Fréquence Cardiaque (Pouls)")
        fig_pouls = go.Figure()
        fig_pouls.add_trace(go.Scatter(
            x=df_p['DateHeure'], 
            y=df_p['Pouls'], 
            name='Pouls (BPM)', 
            mode='lines+markers',
            line=dict(color='#636EFA', dash='dot'),
            marker=dict(size=8)
        ))
        fig_pouls.update_layout(height=300, template="plotly_dark", xaxis_title="Date", yaxis_title="BPM")
        st.plotly_chart(fig_pouls, use_container_width=True)

        with st.expander("Voir le tableau des données de synthèse"):
            st.dataframe(df_p, use_container_width=True)
except:
    st.info("Aucune donnée de synthèse à afficher.")