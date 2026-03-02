st.markdown("---")

# --- SECTION 2 : VISUALISATION ---
st.header("📈 Évolution du Poids")

try:
    # Lecture des données depuis Google Sheets
    df_plot = conn.read(worksheet="poids", ttl=0)
    
    if not df_plot.empty:
        # Nettoyage et tri pour le graphique
        df_plot['DateHeure'] = pd.to_datetime(df_plot['DateHeure'])
        df_plot['Poids_kg'] = pd.to_numeric(df_plot['Poids_kg'], errors='coerce')
        df_plot['Poids_lbs'] = pd.to_numeric(df_plot['Poids_lbs'], errors='coerce')
        df_plot = df_plot.sort_values('DateHeure')

        # Choix de l'unité pour l'affichage
        c1, c2 = st.columns([1, 3])
        with c1:
            unit_choice = st.radio("Unité d'affichage :", ["kg", "lbs"], horizontal=True)
        
        col_to_show = 'Poids_kg' if unit_choice == "kg" else 'Poids_lbs'
        color_line = '#2ec4b6' if unit_choice == "kg" else '#e71d36'

        # Création du graphique Plotly
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_plot['DateHeure'], 
            y=df_plot[col_to_show],
            mode='lines+markers',
            name=f'Poids ({unit_choice})',
            line=dict(color=color_line, width=3),
            marker=dict(size=8, symbol='circle')
        ))

        fig.update_layout(
            template="plotly_dark",
            xaxis_title="Date de pesée",
            yaxis_title=f"Masse ({unit_choice})",
            height=500,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # Petit tableau récapitulatif sous le graphique
        with st.expander("Consulter l'historique complet des pesées"):
            st.dataframe(df_plot.sort_values('DateHeure', ascending=False), use_container_width=True)
            
    else:
        st.info("💡 Aucune donnée de poids n'a encore été enregistrée dans Google Sheets.")

except Exception as e:
    st.error(f"Erreur lors de l'affichage du graphique : {e}")