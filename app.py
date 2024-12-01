import os
import re
import time
import json
import pandas as pd
from flask import Flask, render_template, request, redirect
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Initialisation de Flask
app = Flask(__name__)
app.secret_key = 'secret'
os.makedirs(os.path.join(app.instance_path, 'resume_files'), exist_ok=True)

# Connexion à Cassandra
def connect_to_cassandra():
    with open('./joboffers-token.json', "r") as f:
        creds = json.load(f)
        token = creds["token"]

    cluster = Cluster(
        cloud={"secure_connect_bundle": './secure-connect-joboffers.zip'},
        auth_provider=PlainTextAuthProvider("token", token)
    )
    session = cluster.connect()
    session.set_keyspace('jobscraping')
    return session

session_cassandra = connect_to_cassandra()

# Initialisation du driver Selenium
def init_webdriver():
    service = Service('./chromedriver')
    return webdriver.Chrome(service=service)

driver = init_webdriver()

# Création des tables si elles n'existent pas
session_cassandra.execute("""
CREATE TABLE IF NOT EXISTS job_offers (
    title TEXT, company TEXT, location TEXT, link TEXT PRIMARY KEY
)""")
session_cassandra.execute("""
CREATE TABLE IF NOT EXISTS job_details (
    title TEXT, company TEXT, location TEXT, link TEXT PRIMARY KEY,
    description TEXT, min_salary INT, max_salary INT, contract_type TEXT
)""")

# Fonction pour extraire les plages de salaires
def extract_salary_range(salary_text):
    salary_text = salary_text.replace("\u202f", "").replace("€", "").replace(" ", "")
    salary_numbers = re.findall(r'\d+', salary_text)
    if len(salary_numbers) >= 2:
        return int(salary_numbers[0]), int(salary_numbers[1])
    elif len(salary_numbers) == 1:
        return int(salary_numbers[0]), int(salary_numbers[0])
    return None, None

# Scraper les offres d'emploi sur Indeed
def scrape_indeed():
    print("Scraping des offres Indeed...")
    keyword = 'informatique'
    location = 'France'
    url = f'https://fr.indeed.com/jobs?q={keyword}&l={location}&lang=en'
    driver.get(url)
    time.sleep(5)

    for _ in range(5):  # Limité à 5 pages pour la démo
        jobs_list = driver.find_elements(By.XPATH, '//div[contains(@class, "job_seen_beacon")]')
        for job in jobs_list:
            try:
                title = job.find_element(By.XPATH, './/a[contains(@class, "jcs-JobTitle")]').text.strip()
                company = job.find_element(By.XPATH, './/span[contains(@data-testid, "company-name")]').text.strip()
                location = job.find_element(By.XPATH, './/div[contains(@data-testid, "text-location")]').text.strip()
                link = job.find_element(By.XPATH, './/a[contains(@class, "jcs-JobTitle")]').get_attribute('href')

                # Vérifier si l'offre existe déjà
                if not session_cassandra.execute("SELECT link FROM job_offers WHERE link = %s", (link,)).one():
                    session_cassandra.execute("""
                        INSERT INTO job_offers (title, company, location, link)
                        VALUES (%s, %s, %s, %s)
                    """, (title, company, location, link))
            except Exception as e:
                print(f"Erreur lors du scraping : {e}")

        # Aller à la page suivante
        try:
            next_button = driver.find_element(By.XPATH, '//a[@aria-label="Next"]')
            next_button.click()
            time.sleep(5)
        except:
            print("Fin des pages.")
            break

# Récupérer les détails des offres d'emploi
def fetch_job_details():
    print("Récupération des détails...")
    rows = session_cassandra.execute("SELECT * FROM job_offers")
    for row in rows:
        try:
            driver.get(row.link)
            description = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "jobDescriptionText"))
            ).text.strip()

            # Récupérer le salaire
            salary_text = driver.find_element(By.XPATH, './/span[contains(@class, "css-19j1a75 eu4oa1w0")]').text
            min_salary, max_salary = extract_salary_range(salary_text)

            # Type de contrat
            contract_type = driver.find_element(By.XPATH, './/span[contains(@class, "css-k5flys eu4oa1w0")]').text.strip()

            # Enregistrer dans Cassandra
            session_cassandra.execute("""
                INSERT INTO job_details (title, company, location, link, description, min_salary, max_salary, contract_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (row.title, row.company, row.location, row.link, description, min_salary, max_salary, contract_type))
        except Exception as e:
            print(f"Erreur pour {row.link} : {e}")

# Route principale
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run()
