import re
#import nltk
from cassandra.cluster import Cluster
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from cassandra.query import SimpleStatement
from nltk.corpus import stopwords
import os
import pandas as pd
from flask import Flask,render_template,redirect,request,session
#from resume_screening import resparser, match
from lxml import html





app=Flask(__name__)

os.makedirs(os.path.join(app.instance_path, 'resume_files'), exist_ok=True)

keyword=''
location=''
InternType=''
app.secret_key = 'secret'

try:
    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
except OSError:
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])

# Connexion à Cassandra
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import json

with open('.\\joboffers-token.json', "r") as f:
    creds = json.load(f)
    ASTRA_DB_APPLICATION_TOKEN = creds["token"]

cluster = Cluster(
    cloud={
        "secure_connect_bundle": '.\\secure-connect-joboffers.zip',
    },
    auth_provider=PlainTextAuthProvider(
        "token",
        ASTRA_DB_APPLICATION_TOKEN,
    ),
)

session_cassandra = cluster.connect('jobscraping')

# Initialiser le driver Selenium
service = Service(r'.\\chromedriver-win64\\chromedriver.exe')
driver = webdriver.Chrome(service=service)



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


# Fonction pour effectuer le scrapping d'Indeed
def scrape_indeed():
    print("Scrapping des offres Indeed en cours...")
    keyword = 'informatique'
    location = 'France'
    url = f'https://fr.indeed.com/jobs?q={keyword}&l={location}&lang=en'
    driver.get(url)
    time.sleep(5)

    for i in range(20):  # Limité à 20 pages
        jobs_list = driver.find_elements(By.XPATH, '//div[contains(@class, "job_seen_beacon")]')
        for job in jobs_list:
            title = job.find_element(By.XPATH, './/a[contains(@class, "jcs-JobTitle")]').text.strip()
            company = job.find_element(By.XPATH, './/span[contains(@data-testid, "company-name")]').text.strip()
            location = job.find_element(By.XPATH, './/div[contains(@data-testid, "text-location")]').text.strip()
            link = job.find_element(By.XPATH, './/a[contains(@class, "jcs-JobTitle")]').get_attribute('href')

            # Vérification et insertion
            query = "SELECT link FROM job_offers WHERE link = %s"
            existing_job = session_cassandra.execute(query, (link,)).one()
            if not existing_job:
                session_cassandra.execute("""
                    INSERT INTO job_offers (title, company, location, link) 
                    VALUES (%s, %s, %s, %s)
                """, (title, company, location, link))
                print(f"Ajout : {title}")

        try:
            next_button = driver.find_element(By.XPATH, '//a[@aria-label="Next"]')
            next_button.click()
            time.sleep(5)
        except:
            print("Pas de page suivante.")
            break

    print("Scrapping des offres Indeed terminé.")

# Fonction pour compléter les détails des offres
def fetch_job_details():
    print("Récupération des détails des offres en cours...")
    rows = session_cassandra.execute("SELECT * FROM job_offers")

    for row in rows:
        link = row.link
        try:
            driver.get(link)
            description = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "jobDescriptionText"))
            ).text.strip()

            salary_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, './/span[contains(@class, "css-19j1a75 eu4oa1w0")]'))
            )
            salary = salary_element.text.strip() if salary_element else "N/A"
            
            # Fonction pour extraire les salaires min et max sous forme de nombres
            def extract_salary_range(salary_text):
                # Remplacer les espaces insécables et supprimer les caractères non numériques sauf '-'
                salary_text = salary_text.replace("\u202f", " ").replace("€", "").replace(" ", "")
                
                # Trouver tous les nombres dans le texte (gestion des salaires avec plages)
                salary_numbers = re.findall(r'\d+', salary_text)
                if len(salary_numbers) >= 2:
                    # Convertir en entiers et assigner min et max
                    min_salary = int(salary_numbers[0])
                    max_salary = int(salary_numbers[1])
                    return min_salary, max_salary
                elif len(salary_numbers) == 1:
                    # Si un seul nombre est trouvé, supposer qu'il est à la fois min et max
                    return int(salary_numbers[0]), int(salary_numbers[0])
                else:
                    # Si aucun nombre n'est trouvé, retourner None
                    return None, None

            # Utiliser la fonction pour extraire min et max
            min_salary, max_salary = extract_salary_range(salary)

            print("Salaire minimum:", min_salary)
            print("Salaire maximum:", max_salary)

            contrat_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, './/span[contains(@class, "css-k5flys eu4oa1w0")]'))
            )
            contract_type= contrat_element.text.strip() if contrat_element else "N/A"

            print("contrat",contract_type) 

            session_cassandra.execute("""
                INSERT INTO job_details (title, company, location, link, description, min_salary, max_salary, contract_type) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (row.title, row.company, row.location, link, description, min_salary, max_salary, contract_type))
            print(f"Détails ajoutés pour : {row.title}")
        except Exception as e:
            print(f"Erreur pour {row.title} : {e}")

    print("Récupération des détails terminée.")

"""@app.before_first_request
def initialize_scraping():
    scrape_indeed()
    fetch_job_details()"""
    
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
def submit_data():
    global cvPath 
    global InternType
    if request.method == 'POST':        
        f = request.files['userfile']
        cvPath = os.path.join(app.instance_path, 'resume_files', f.filename)
        f.save(cvPath)
        
    stopw  = set(stopwords.words('french'))  # Utilisation des stopwords en français
    
    # Charger les données depuis la base Cassandra plutôt que depuis un fichier CSV
    query = "SELECT * FROM job_details"
    rows = session_cassandra.execute(query)
    job = pd.DataFrame(rows)  # Conversion des résultats de Cassandra en DataFrame
    
    job['test'] = job['description'].apply(lambda x: ' '.join([word for word in str(x).split() if len(word) > 2 and word not in stopw]))
    df = job.drop_duplicates(subset='test').reset_index(drop=True)
    df['clean'] = df['test'].apply(match.preprocessing)  # Assurez-vous que la fonction de pré-traitement fonctionne avec le français
    jobdesc = df['clean'].values.astype('U')  # Conversion des descriptions en tableau numpy
    
    # Extraction des compétences depuis le CV
    skills = resparser.skill(f'instance/resume_files/{f.filename}')
    skills.append(match.preprocessing(skills[0]))
    del skills[0]

    # Calcul de la similarité entre compétences et descriptions d'emploi
    count_matrix = match.vectorizing(skills[0], jobdesc)
    matchPercentage = match.coSim(count_matrix)
    matchPercentage = pd.DataFrame(matchPercentage, columns=['Skills Match'])

    # Recommandations d'offres d'emploi basées sur la similarité des compétences
    result_cosine = df[['title', 'company', 'link','contract_type','location']]  # Assurez-vous que les noms de colonnes sont corrects
    result_cosine = result_cosine.join(matchPercentage)
    result_cosine = result_cosine[['title', 'company', 'Skills Match', 'link','contract_type']]
    result_cosine.columns = ['Titre de l\'emploi', 'Entreprise', 'Correspondance des compétences', 'Lien','contrat']
    result_cosine = result_cosine.sort_values('Correspondance des compétences', ascending=False).reset_index(drop=True).head(20)
    
    print(result_cosine)
    return render_template('upload.html', column_names=result_cosine.columns.values, row_data=list(result_cosine.values.tolist()),
                           link_column="Lien", zip=zip)

@app.route('/submit2', methods=['POST'])
def submit_data_filtre():
    if request.method == 'POST':
        print(cvPath)
        # Récupération des filtres
        location_filter = request.form.get('location', '').strip()
        contract_filter = request.form.get('contract', '').strip()
        salary_filter = request.form.get('min_salary', '').strip()

        stopw = set(stopwords.words('french'))

        # Chargement des données de Cassandra avec filtres
        query = "SELECT * FROM job_details"
        filters = []
        
       
        
        if salary_filter and salary_filter.startswith(">"):
            try:
                min_salary = int(salary_filter[1:])
                filters.append(f"min_salary >= {min_salary}")
            except ValueError:
                pass

        if filters:
            query += " WHERE " + " AND ".join(filters)
        
        print(query)
        rows = session_cassandra.execute(query)
        job = pd.DataFrame(rows)
        if contract_filter:
            cf=f'{contract_filter}'
            job2=job[job['contract_type'].str.contains(cf)==True]
            job=job2
        if location_filter:
           lc=f'{location_filter}'
           job1=job[job['location'].str.contains(lc)==True]
           job=job1
        job['test'] = job['description'].apply(lambda x: ' '.join([word for word in str(x).split() if len(word) > 2 and word not in stopw]))
        df = job.drop_duplicates(subset='test').reset_index(drop=True)
        df['clean'] = df['test'].apply(match.preprocessing)
        jobdesc = df['clean'].values.astype('U')

        skills = resparser.skill(cvPath)
        skills.append(match.preprocessing(skills[0]))
        del skills[0]

        count_matrix = match.vectorizing(skills[0], jobdesc)
        matchPercentage = match.coSim(count_matrix)
        matchPercentage = pd.DataFrame(matchPercentage, columns=['Skills Match'])

        result_cosine = df[['title', 'company', 'link', 'contract_type','location']]
        result_cosine = result_cosine.join(matchPercentage)
        result_cosine = result_cosine[['title', 'company', 'Skills Match', 'link', 'contract_type','location']]
        result_cosine.columns = ['Titre de l\'emploi', 'Entreprise', 'Correspondance des compétences', 'Lien', 'contrat','location']
        result_cosine = result_cosine.sort_values('Correspondance des compétences', ascending=False).reset_index(drop=True).head(20)

        return render_template('upload.html', column_names=result_cosine.columns.values, row_data=list(result_cosine.values.tolist()),
                               link_column="Lien", zip=zip)






if __name__ == "__main__":
    app.run()
