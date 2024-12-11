import re
from cassandra.cluster import Cluster
import time
from cassandra.query import SimpleStatement
import os
import pandas as pd
from flask import Flask,render_template,redirect,request,session,url_for

from lxml import html
import uuid






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
    
    # Passer les données au template HTML
    return render_template(
        'upload.html',
        row_data=row_data  # Données pour la section HTML
    )


@app.route('/submit2', methods=['POST'])
def submit_data_filtre():
    if request.method == 'POST':
        # Créer les tables si elles n'existent pas
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
@app.route('/manage_job_offers', methods=['GET'])
def manage_job_offers():
    with open('joboffers-token.json', "r") as f:
        creds = json.load(f)
        ASTRA_DB_APPLICATION_TOKEN = creds["token"]

    cluster = Cluster(
        cloud={"secure_connect_bundle": 'secure-connect-joboffers.zip'},
        auth_provider=PlainTextAuthProvider("token", ASTRA_DB_APPLICATION_TOKEN),
    )
    
    session_cassandra = cluster.connect('jobscraping')

    # Créer la nouvelle table avec un UUID si elle n'existe pas
    session_cassandra.execute("""
        CREATE TABLE IF NOT EXISTS job_details_new (
            id UUID PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            description TEXT,
            link TEXT,
            min_salary INT,
            max_salary INT,
            contract_type TEXT
        )
    """)

    # Récupérer les nouvelles données depuis job_details_new
    query = "SELECT * FROM job_details_new"
    rows = session_cassandra.execute(query)
    job_offers = [
        (row.id, row.title, row.company, row.location, row.description, row.link, row.min_salary, row.max_salary, row.contract_type)
        for row in rows
    ]
    
    return render_template('manage_job_offers.html', job_offers=job_offers)

# Route pour éditer une offre d'emploi
@app.route('/edit_job_offer/<uuid:job_id>', methods=['GET', 'POST'])
def edit_job_offer(job_id):
    with open('joboffers-token.json', "r") as f:
        creds = json.load(f)
        ASTRA_DB_APPLICATION_TOKEN = creds["token"]

    cluster = Cluster(
        cloud={"secure_connect_bundle": 'secure-connect-joboffers.zip'},
        auth_provider=PlainTextAuthProvider("token", ASTRA_DB_APPLICATION_TOKEN),
    )
    
    session_cassandra = cluster.connect('jobscraping')

    if request.method == 'POST':
        # Récupérer les données du formulaire
        title = request.form['title']
        company = request.form['company']
        location = request.form['location']
        description = request.form['description']
        link = request.form['link']
        min_salary = int(request.form['min_salary'])
        max_salary = int(request.form['max_salary'])
        contract_type = request.form['contract_type']

        # Mettre à jour l'offre dans la base de données en utilisant l'ID (UUID) comme identifiant
        query = """
            UPDATE job_details_new
            SET title = %s, company = %s, location = %s, description = %s, link = %s, min_salary = %s, max_salary = %s, contract_type = %s
            WHERE id = %s
        """
        session_cassandra.execute(query, (title, company, location, description, link, min_salary, max_salary, contract_type, job_id))

        # Retourner à la page de gestion des offres après modification
        return redirect(url_for('manage_job_offers'))

    # Récupérer les informations de l'offre à modifier en utilisant 'job_id' (UUID)
    query = "SELECT * FROM job_details_new WHERE id = %s"
    row = session_cassandra.execute(query, (job_id,)).one()

    if row:
        return render_template('edit_job_offer.html', offer=row)
    else:
        return "Offre d'emploi non trouvée", 404
@app.route('/add_job_offer', methods=['GET', 'POST'])
def add_job_offer():
    if request.method == 'POST':
        # Récupérer les données du formulaire
        title = request.form['title']
        company = request.form['company']
        location = request.form['location']
        description = request.form['description']
        link = request.form['link']
        min_salary = int(request.form['min_salary'])
        max_salary = int(request.form['max_salary'])
        contract_type = request.form['contract_type']

        # Générer un UUID pour la nouvelle offre
        job_id =uuid.uuid4()

        # Ajouter l'offre à la base de données
        query = """
            INSERT INTO job_details_new (id, title, company, location, description, link, min_salary, max_salary, contract_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        session_cassandra.execute(query, (job_id, title, company, location, description, link, min_salary, max_salary, contract_type))

        # Rediriger vers la page de gestion des offres
        return redirect(url_for('manage_job_offers'))

    return render_template('add_job_offer.html')
@app.route('/delete_job_offer/<uuid:job_id>', methods=['GET'])
def delete_job_offer(job_id):
    # Supprimer l'offre de la base de données
    query = "DELETE FROM job_details_new WHERE id = %s"
    session_cassandra.execute(query, (job_id,))

    # Rediriger vers la page de gestion des offres après suppression
    return redirect(url_for('manage_job_offers'))


# Lancer l'application Flask
if __name__ == '__main__':
    app.run(debug=True)



if __name__ == "__main__":
    app.run()
