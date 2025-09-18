import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.api as sm

# Configuration de la page Streamlit
st.set_page_config(page_title="Pression Sanguine", layout="wide")

# Fonction pour créer la table si elle n'existe pas
def create_table_if_not_exists():
    conn = sqlite3.connect('mesures_sante.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PressionBrut (
            DateHeure TEXT PRIMARY KEY,
            Systolique INTEGER,
            Diastolique INTEGER,
            Pouls INTEGER,
            Note1 TEXT,
            Note2 TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PressionSynthese (
            DateHeure TEXT PRIMARY KEY,
            Systolique INTEGER,
            Diastolique INTEGER,
            Pouls INTEGER,
            Note1 TEXT,
            Note2 TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Fonction pour insérer de nouvelles données dans la table PressionBrut
def insert_new_data(df):
    conn = sqlite3.connect('mesures_sante.db')
    cursor = conn.cursor()
    new_rows_count = 0
    for index, row in df.iterrows():
        try:
            cursor.execute('''
                INSERT INTO PressionBrut (DateHeure, Systolique, Diastolique, Pouls, Note1, Note2)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (row['DateHeure'], row['Systolique'], row['Diastolique'], row['Pouls'], row['Note1'], row['Note2']))
            new_rows_count += 1
        except sqlite3.IntegrityError:
            # Gère les clés primaires en double (données déjà existantes)
            pass
    conn.commit()
    conn.close()
    return new_rows_count

# Fonction pour l'analyse des données et l'insertion dans PressionSynthese
def analyze_and_synthesize(df):
    df['DateHeure'] = pd.to_datetime(df['DateHeure'])
    df = df.sort_values(by='DateHeure')
    df['DateHeure_30min_group'] = df['DateHeure'].dt.floor('30T')
    
    synthese_df = df.loc[df.groupby('DateHeure_30min_group')['Systolique'].idxmin()]
    
    conn = sqlite3.connect('mesures_sante.db')
    synthese_df.to_sql('PressionSynthese', conn, if_exists='replace', index=False, dtype={'DateHeure': 'TEXT'})
    conn.close()
    
    return synthese_df

# Fonction pour lire les données d'une table
def read_data_from_db(table_name):
    conn = sqlite3.connect('mesures_sante.db')
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

# Créer les tables au démarrage de l'application
create_table_if_not_exists()

# Titre de la page
st.title("📊 Gestion des Données de Pression Sanguine")

# --- Section d'importation et de traitement des données ---
st.header("1. Intégration des Données Brutes")
st.write("Veuillez télécharger un fichier CSV ou Excel contenant vos données de pression sanguine.")
uploaded_file = st.file_uploader("Choisissez un fichier", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_brut = pd.read_csv(uploaded_file)
        else:
            df_brut = pd.read_excel(uploaded_file)
        
        st.write("Aperçu du fichier chargé :")
        st.dataframe(df_brut.head())
        
        st.subheader("Configuration des colonnes")
        st.write("Veuillez faire correspondre les colonnes de votre fichier aux champs de la base de données.")
        
        cols = df_brut.columns.tolist()
        col_mapping = {}
        db_cols = ["DateHeure", "Systolique", "Diastolique", "Pouls", "Note1", "Note2"]
        
        for db_col in db_cols:
            col_mapping[db_col] = st.selectbox(
                f"Colonne pour `{db_col}` :",
                options=[None] + cols,
                index=0,
                key=f"selectbox_{db_col}"
            )
        
        # Validation du mappage
        if st.button("Intégrer les données"):
            selected_values = list(col_mapping.values())
            if None in selected_values:
                st.error("⚠️ Veuillez sélectionner une colonne pour chaque champ de la base de données.")
            elif len(selected_values) != len(set(v for v in selected_values if v is not None)):
                st.error("⚠️ Une ou plusieurs colonnes ont été sélectionnées plusieurs fois. Veuillez vous assurer que chaque champ a une colonne unique.")
            else:
                try:
                    # Crée un nouveau DataFrame en sélectionnant et renommant les colonnes d'entrée
                    df_brut_to_insert = pd.DataFrame()
                    for db_col, source_col in col_mapping.items():
                        if source_col:
                            df_brut_to_insert[db_col] = df_brut[source_col]
                    
                    # Nettoyage des données
                    df_brut_to_insert['DateHeure'] = pd.to_datetime(df_brut_to_insert['DateHeure'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
                    df_brut_to_insert['Systolique'] = pd.to_numeric(df_brut_to_insert['Systolique'], errors='coerce').astype('Int64')
                    df_brut_to_insert['Diastolique'] = pd.to_numeric(df_brut_to_insert['Diastolique'], errors='coerce').astype('Int64')
                    df_brut_to_insert['Pouls'] = pd.to_numeric(df_brut_to_insert['Pouls'], errors='coerce').astype('Int64')
                    
                    # Insertion des données
                    new_rows_count = insert_new_data(df_brut_to_insert.dropna(subset=['DateHeure']))
                    st.success(f"✅ {new_rows_count} nouvelles lignes ont été intégrées dans la base de données.")
                    
                except KeyError as e:
                    st.error(f"Erreur de mappage : la colonne d'origine '{e.args[0]}' est introuvable. Veuillez vérifier vos sélections.")
                except Exception as e:
                    st.error(f"Une erreur inattendue est survenue : {e}")

    except Exception as e:
        st.error(f"Une erreur est survenue lors du chargement du fichier : {e}")

# --- Section d'affichage et d'analyse des données brutes ---
st.header("2. Visualisation des Données Brutes")
st.write("Graphiques basés sur toutes les données enregistrées dans la table `PressionBrut`.")

df_brut_db = read_data_from_db('PressionBrut')

if not df_brut_db.empty:
    df_brut_db['DateHeure'] = pd.to_datetime(df_brut_db['DateHeure'])
    df_brut_db = df_brut_db.sort_values('DateHeure')
    
    # Graphique de pression
    fig_pression = px.line(df_brut_db, 
                           x='DateHeure', 
                           y=['Systolique', 'Diastolique'], 
                           title='Évolution de la Pression Sanguine (Systolique et Diastolique)',
                           labels={'value': 'Pression (mmHg)', 'variable': 'Type'})
    st.plotly_chart(fig_pression, use_container_width=True)
    
    # Graphique de pouls
    fig_pouls = px.line(df_brut_db, 
                        x='DateHeure', 
                        y='Pouls', 
                        title='Évolution du Pouls',
                        labels={'Pouls': 'Pouls (bpm)'})
    st.plotly_chart(fig_pouls, use_container_width=True)
    
else:
    st.info("Aucune donnée brute n'est encore disponible dans la base de données.")

# --- Section d'analyse et de visualisation des données synthétisées ---
st.header("3. Analyse et Visualisation des Données Synthétisées")
st.write("Les données sont regroupées par tranches de 30 minutes. La mesure avec la pression systolique la plus basse est conservée.")

if st.button("Lancer l'analyse et la synthèse"):
    if not df_brut_db.empty:
        df_synthese = analyze_and_synthesize(df_brut_db.copy())
        st.success("🎉 Analyse terminée ! Les données synthétisées sont prêtes.")
    else:
        st.warning("⚠️ Aucune donnée brute n'est disponible pour l'analyse.")

df_synthese_db = read_data_from_db('PressionSynthese')

if not df_synthese_db.empty:
    df_synthese_db['DateHeure'] = pd.to_datetime(df_synthese_db['DateHeure'])
    df_synthese_db = df_synthese_db.sort_values('DateHeure')

    # Vérification et nettoyage des colonnes pour le traçage
    if all(col in df_synthese_db.columns for col in ['Systolique', 'Diastolique', 'Pouls']):
        df_synthese_db['Systolique'] = pd.to_numeric(df_synthese_db['Systolique'], errors='coerce')
        df_synthese_db['Diastolique'] = pd.to_numeric(df_synthese_db['Diastolique'], errors='coerce')
        df_synthese_db['Pouls'] = pd.to_numeric(df_synthese_db['Pouls'], errors='coerce')

        # Création du graphique de pression (go.Figure)
        fig_synthese_pression = go.Figure()
        
        # Ajout des tracés de données
        fig_synthese_pression.add_trace(go.Scatter(x=df_synthese_db['DateHeure'], y=df_synthese_db['Systolique'], mode='lines+markers', name='Systolique'))
        fig_synthese_pression.add_trace(go.Scatter(x=df_synthese_db['DateHeure'], y=df_synthese_db['Diastolique'], mode='lines+markers', name='Diastolique'))
        
        # Calcul et ajout de la ligne de tendance pour la pression systolique
        lowess_systolique = sm.nonparametric.lowess(endog=df_synthese_db['Systolique'], exog=df_synthese_db['DateHeure'].astype('int64'), frac=0.3)
        fig_synthese_pression.add_trace(go.Scatter(x=pd.to_datetime(lowess_systolique[:, 0]), y=lowess_systolique[:, 1], mode='lines', name='Tendance Systolique', line=dict(dash='dash')))

        # Calcul et ajout de la ligne de tendance pour la pression diastolique
        lowess_diastolique = sm.nonparametric.lowess(endog=df_synthese_db['Diastolique'], exog=df_synthese_db['DateHeure'].astype('int64'), frac=0.3)
        fig_synthese_pression.add_trace(go.Scatter(x=pd.to_datetime(lowess_diastolique[:, 0]), y=lowess_diastolique[:, 1], mode='lines', name='Tendance Diastolique', line=dict(dash='dash')))
        
        fig_synthese_pression.update_layout(title='Pression Sanguine Synthétisée', yaxis_title='Pression (mmHg)')
        st.plotly_chart(fig_synthese_pression, use_container_width=True)
        
        # Création du graphique de pouls (go.Figure)
        fig_synthese_pouls = go.Figure()
        fig_synthese_pouls.add_trace(go.Scatter(x=df_synthese_db['DateHeure'], y=df_synthese_db['Pouls'], mode='lines+markers', name='Pouls'))
        
        # Calcul et ajout de la ligne de tendance pour le pouls
        lowess_pouls = sm.nonparametric.lowess(endog=df_synthese_db['Pouls'], exog=df_synthese_db['DateHeure'].astype('int64'), frac=0.3)
        fig_synthese_pouls.add_trace(go.Scatter(x=pd.to_datetime(lowess_pouls[:, 0]), y=lowess_pouls[:, 1], mode='lines', name='Tendance Pouls', line=dict(dash='dash')))
        
        fig_synthese_pouls.update_layout(title='Pouls Synthétisé', yaxis_title='Pouls (bpm)')
        st.plotly_chart(fig_synthese_pouls, use_container_width=True)

        st.subheader("Aperçu des Données Synthétisées")
        st.dataframe(df_synthese_db)
    else:
        st.warning("Les colonnes de données requises pour les graphiques de synthèse n'ont pas été trouvées ou sont vides.")
else:
    st.info("Lancez l'analyse pour visualiser les données synthétisées.")