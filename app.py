import re
from cassandra.cluster import Cluster
import time
from cassandra.query import SimpleStatement
import os
import pandas as pd
from flask import Flask,render_template,redirect,request,session
from lxml import html





app=Flask(__name__)

os.makedirs(os.path.join(app.instance_path, 'resume_files'), exist_ok=True)

keyword=''
location=''
InternType=''
app.secret_key = 'secret'



# Connexion à Cassandra
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import json



# Initialiser le driver Selenium
#service = Service(r'.\\chromedriver-win64\\chromedriver.exe')
#driver = webdriver.Chrome(service=service)



# Créer les tables si elles n'existent pas
session_cassandra.execute("""
    CREATE TABLE IF NOT EXISTS job_offers (
        title TEXT,
        company TEXT,
        location TEXT,
        link TEXT PRIMARY KEY
    )
""")
session_cassandra.execute("""
    CREATE TABLE IF NOT EXISTS job_details (
        title TEXT,
        company TEXT,
        location TEXT,
        link TEXT PRIMARY KEY,
        description TEXT,
        min_salary INT,
        max_salary INT,
        contract_type TEXT
    )
""")





    
@app.route('/')
def index():
    
    return render_template("index.html")

@app.route("/uploadInit")
def uploadInit():
    global InternType
    InternType='Init'
    print(InternType)
    return render_template("upload.html")

@app.route("/home")
def home():
    return redirect('/')





    
@app.route('/submit', methods=['POST'])
def job_recommendations():
    global cvPath
    global InternType

    if request.method == 'POST':        
        f = request.files['userfile']
        cvPath = os.path.join(app.instance_path, 'resume_files', f.filename)
        f.save(cvPath)
    with open('joboffers-token.json', "r") as f:
        creds = json.load(f)
        ASTRA_DB_APPLICATION_TOKEN = creds["token"]

    cluster = Cluster(
        cloud={
            "secure_connect_bundle": 'secure-connect-joboffers.zip',
        },
        auth_provider=PlainTextAuthProvider(
            "token",
            ASTRA_DB_APPLICATION_TOKEN,
        ),
    )
    
    session_cassandra = cluster.connect('jobscraping')

        # Ajoutez ici toute la logique pour générer les recommandations et les insérer dans Cassandra, comme dans la fonction précédente.

    # Récupérer les données de la base Cassandra
    query = "SELECT title, company, skills_match, link, contract_type, location FROM job_recommended"
    rows = session_cassandra.execute(query)
    print(query)
    # Transformer les résultats en une liste pour le template
    row_data = [
        (row.title, row.company, row.skills_match, row.link, row.contract_type, row.location)
        for row in rows
    ]
    print(row_dat)
    # Passer les données au template HTML
    return render_template(
        'upload.html',
        row_data=row_data  # Données pour la section HTML
    )


@app.route('/submit2', methods=['POST'])
def submit_data_filtre():
    if request.method == 'POST':
        # Récupération des filtres depuis le formulaire
        location_filter = request.form.get('location', '').strip()
        contract_filter = request.form.get('contract', '').strip()
        salary_filter = request.form.get('min_salary', '').strip()

        # Construction de la requête avec filtres dynamiques
        query = "SELECT * FROM job_recommended"
        filters = []

        if salary_filter :
           
                filters.append(f"min_salary = '{salary_filter}'")
            

        if contract_filter:
            filters.append(f"contract_type = '{contract_filter}'")
        
        if location_filter:
            filters.append(f"location = '{location_filter}'")

        # Ajout des conditions à la requête SQL
        if filters:
            query += " WHERE " + " AND ".join(filters)

        print(f"Requête exécutée : {query}")

        # Exécution de la requête sur Cassandra
        rows = session_cassandra.execute(query)

        # Conversion des résultats en DataFrame
        job_data = pd.DataFrame(rows)

        # Vérification que les colonnes nécessaires existent
        if not job_data.empty:
            result = job_data[['title', 'company', 'skills_match', 'link', 'contract_type', 'location']]
            result.columns = [
                'Titre de l\'emploi', 'Entreprise', 'Correspondance des compétences', 'Lien', 'Type de contrat', 'Localisation'
            ]
            result = result.sort_values('Correspondance des compétences', ascending=False).reset_index(drop=True).head(20)
        else:
            result = pd.DataFrame(columns=[
                'Titre de l\'emploi', 'Entreprise', 'Correspondance des compétences', 'Lien', 'Type de contrat', 'Localisation'
            ])

        # Renvoyer les résultats au template HTML
        return render_template(
            'upload.html',
            column_names=result.columns.values,
            row_data=list(result.values.tolist()),
            link_column="Lien",
            zip=zip
        )



if __name__ == "__main__":
    app.run()
