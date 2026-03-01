import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Pression Artérielle", layout="wide")
st.title("🩺 Suivi et Synthèse de la Pression")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- SECTION 1 : IMPORTATION ---
st.header("📥 Importer et Synthétiser")
uploaded_file = st.file_uploader("Choisissez votre fichier Excel (.xlsx)", type="xlsx")

if uploaded_file is not None:
    df_raw = pd.read_excel(uploaded_file)
    cols = df_raw.columns.tolist()
    
    st.info("Associez les colonnes :")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sel_date = st.selectbox("Colonne Date", cols, index=0)
        sel_heure = st.selectbox("Colonne Heure", cols, index=1 if len(cols)>1 else 0)
    with c2:
        sel_sys = st.selectbox("Systolique (Max)", cols, index=2 if len(cols)>2 else 0)
        sel_dia = st.selectbox("Diastolique (Min)", cols, index=3 if len(cols)>3 else 0)
    with c3:
        sel_pouls = st.selectbox("Pouls", ["Aucun"] + cols)
    with c4:
        sel_n1 = st.selectbox("Note 1", ["Aucune"] + cols)

    # --- PRÉPARATION DES DONNÉES BRUTES ---
    try:
        df_prep = pd.DataFrame()
        combined_dt = df_raw[sel_date].astype(str) + " " + df_raw[sel_heure].astype(str)
        df_prep['DateHeure'] = pd.to_datetime(combined_dt, errors='coerce')
        df_prep['Systolique'] = pd.to_numeric(df_raw[sel_sys].astype(str).str.replace(',', '.'), errors='coerce')
        df_prep['Diastolique'] = pd.to_numeric(df_raw[sel_dia].astype(str).str.replace(',', '.'), errors='coerce')
        df_prep['Pouls'] = pd.to_numeric(df_raw[sel_pouls].astype(str).str.replace(',', '.'), errors='coerce') if sel_pouls != "Aucun" else 0
        df_prep = df_prep.dropna(subset=['DateHeure', 'Systolique'])

        if st.button("🚀 Synchroniser (Brut + Synthèse 30min)"):
            with st.spinner("Traitement en cours..."):
                
                # 1. MISE À JOUR DE PressionBrut
                df_to_push = df_prep.copy()
                df_to_push['DateHeure'] = df_to_push['DateHeure'].dt.strftime('%Y-%m-%d %H:%M:%S')
                existing_brut = conn.read(worksheet="PressionBrut", ttl=0)
                final_brut = pd.concat([existing_brut, df_to_push]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="PressionBrut", data=final_brut)

                # 2. LOGIQUE DE SYNTHÈSE (Intervalle 30min + Sys Min)
                df_syn = df_prep.copy()
                df_syn = df_syn.sort_values('DateHeure')
                
                # On crée des groupes de 30 minutes
                # '30min' définit l'intervalle, label='left' définit le début du créneau
                df_syn['Groupe30'] = df_syn['DateHeure'].dt.floor('30min')
                
                # Pour chaque groupe, on garde la ligne où la Systolique est la plus basse (idxmin)
                idx_min_sys = df_syn.groupby('Groupe30')['Systolique'].idxmin()
                df_final_syn = df_syn.loc[idx_min_sys].copy()
                
                # On prépare pour l'envoi (on enlève la colonne temporaire Groupe30)
                df_final_syn = df_final_syn.drop(columns=['Groupe30'])
                df_final_syn['DateHeure'] = df_final_syn['DateHeure'].dt.strftime('%Y-%m-%d %H:%M:%S')

                # 3. ENVOI VERS PressionSynthese
                try:
                    existing_syn = conn.read(worksheet="PressionSynthese", ttl=0)
                except:
                    existing_syn = pd.DataFrame(columns=df_final_syn.columns)
                
                # Fusion avec l'historique des synthèses
                final_syn_to_sheet = pd.concat([existing_syn, df_final_syn]).drop_duplicates(subset=['DateHeure'], keep='last')
                conn.update(worksheet="PressionSynthese", data=final_syn_to_sheet)

                st.success(f"✅ Données brutes et {len(df_final_syn)} points de synthèse enregistrés !")
                st.cache_data.clear()
                
                st.write("### Synthèse générée (Valeurs minimales par créneau de 30 min) :")
                st.dataframe(df_final_syn)

    except Exception as e:
        st.error(f"Erreur : {e}")

st.markdown("---")

# --- SECTION VISUALISATION ---
st.header("📈 Comparaison Graphique")

try:
    df_brut_plot = conn.read(worksheet="PressionBrut", ttl=0)
    df_syn_plot = conn.read(worksheet="PressionSynthese", ttl=0)

    if not df_brut_plot.empty:
        df_brut_plot['DateHeure'] = pd.to_datetime(df_brut_plot['DateHeure'])
        df_syn_plot['DateHeure'] = pd.to_datetime(df_syn_plot['DateHeure'])
        
        fig = go.Figure()
        
        # Données Brutes (en filigrane / transparence)
        fig.add_trace(go.Scatter(x=df_brut_plot['DateHeure'], y=df_brut_plot['Systolique'], 
                                 name='Systolique Brut', mode='markers', marker=dict(color='gray', opacity=0.3)))
        
        # Synthèse (Ligne principale)
        fig.add_trace(go.Scatter(x=df_syn_plot['DateHeure'], y=df_syn_plot['Systolique'], 
                                 name='Systolique (Min 30min)', mode='lines+markers', line=dict(color='#FF4B4B', width=3)))
        
        fig.add_trace(go.Scatter(x=df_syn_plot['DateHeure'], y=df_syn_plot['Diastolique'], 
                                 name='Diastolique (Min 30min)', mode='lines+markers', line=dict(color='#00CC96', width=2)))

        fig.update_layout(xaxis_title="Temps", yaxis_title="mmHg", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
except:
    st.info("Données en attente...")