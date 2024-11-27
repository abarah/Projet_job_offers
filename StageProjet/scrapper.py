from cassandra.cluster import Cluster
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
from cassandra.query import SimpleStatement

def scrape_indeed():
  # Initialiser le driver de Selenium
  service = Service(r'C:\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe')
  driver = webdriver.Chrome(service=service)

 
  # Connexion à Cassandra
  cluster = Cluster(['127.0.0.1'])  # Remplacez par l'adresse IP de votre cluster si nécessaire
  session = cluster.connect()

  # Créer la keyspace si elle n'existe pas
  session.execute("""
      CREATE KEYSPACE IF NOT EXISTS job_scraping 
      WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
  """)

  # Utiliser la keyspace job_scraping
  session.set_keyspace('job_scraping')

  # Créer la table si elle n'existe pas
  session.execute("""
      CREATE TABLE IF NOT EXISTS job_offers (
          title TEXT,
          company TEXT,
          location TEXT,
          link TEXT,
          PRIMARY KEY (link)
      )
  """)

  # Se rendre sur la page de recherche d'offres d'emploi Indeed
  keyword = 'informatique'
  location = 'France'
  url = f'https://fr.indeed.com/jobs?q={keyword}&l={location}&lang=en'
  driver.get(url)

  # Attendre 5 secondes pour que tous les éléments soient chargés
  time.sleep(5)

  for i in range(20):  # Scraper jusqu'à 20 pages
      # Extraire les résultats
      jobs_list = driver.find_elements(By.XPATH, '//div[contains(@class, "job_seen_beacon")]')
      for job in jobs_list:
          # Titre de l'emploi
          title = job.find_element(By.XPATH, './/a[contains(@class, "jcs-JobTitle")]').text.strip()

          company_elements = job.find_elements(By.XPATH, './/span[contains(@data-testid, "company-name")]')
          company = company_elements[0].text.strip() if company_elements else "N/A"
          
          # Localisation de l'emploi
          location_elements = job.find_elements(By.XPATH, './/div[contains(@data-testid, "text-location")]')
          location = location_elements[0].text.strip() if location_elements else "N/A"
          
          # Lien vers l'offre
          link = job.find_element(By.XPATH, './/a[contains(@class, "jcs-JobTitle")]').get_attribute('href')

          # Vérifier si l'offre existe déjà dans la base de données
          query = "SELECT link FROM job_offers WHERE link = %s"
          existing_job = session.execute(query, (link,)).one()
          
          if existing_job:
              print(f"L'offre {title} existe déjà. Ignorer l'insertion.")
              continue  # Si l'offre existe déjà, passer à la suivante

          # Insérer les données dans Cassandra
          insert_statement = """
              INSERT INTO job_offers (title, company, location, link) 
              VALUES (%s, %s, %s, %s)
          """
          session.execute(insert_statement, (title, company, location, link))
          print(f"L'offre {title} a été insérée.")

      # Passer à la page suivante
      try:
          next_button = driver.find_element(By.XPATH, '//a[@aria-label="Next"]')
          next_button.click()
          time.sleep(5)
      except:
          print('No more pages')
          break

  # Fermer le driver
  driver.quit()


def scrape_and_store_jobs():
    # Connexion à Cassandra
    cluster = Cluster(['127.0.0.1'])  # Remplacez par l'adresse IP de votre cluster si nécessaire
    session = cluster.connect('job_scraping')  # Utiliser la keyspace job_scraping

    # Créer une nouvelle table si elle n'existe pas
    session.execute("""
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

    # Initialiser le driver Selenium
    service = Service(r'C:\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe')
    driver = webdriver.Chrome(service=service)

    # Fonction pour extraire la plage salariale
    def extract_salary_range(salary_text):
        salary_text = salary_text.replace("\u202f", " ").replace("€", "").replace(" ", "")
        salary_numbers = re.findall(r'\d+', salary_text)
        if len(salary_numbers) >= 2:
            min_salary = int(salary_numbers[0])
            max_salary = int(salary_numbers[1])
            return min_salary, max_salary
        elif len(salary_numbers) == 1:
            return int(salary_numbers[0]), int(salary_numbers[0])
        else:
            return None, None

    # Parcourir les éléments de la table job_offers
    rows = session.execute("SELECT * FROM job_offers")

    for row in rows:
        link = row.link  # Lien de l'offre d'emploi

        try:
            # Ouvrir la page de l'offre d'emploi
            driver.get(link)

            # Attendre que le texte de la description soit chargé
            description_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "jobDescriptionText"))
            )
            description = description_element.text.strip() if description_element else "N/A"

            # Extraire le salaire
            try:
                salary_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="jobDetailsSection"]/div/div[1]/div[2]/div[1]/div/div/ul/li/div/div/div[1]'))
                )
                salary = salary_element.text.strip() if salary_element else "N/A"
            except:
                salary = "N/A"

            min_salary, max_salary = extract_salary_range(salary)

            # Extraire le type de contrat
            try:
                contrat_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="jobDetailsSection"]/div/div[1]/div[2]/div[2]/div/div/ul/li/button/div/div[2]'))
                )
                contrat = contrat_element.text.strip()
            except Exception:
                try:
                    contrat_element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="salaryInfoAndJobType"]/span[2]/text()[2]'))
                    )
                    contrat = contrat_element.text.strip()
                except Exception:
                    contrat = "N/A"

            # Insérer les données dans la nouvelle table job_details
            insert_statement = """
                INSERT INTO job_details (title, company, location, link, description, min_salary, max_salary, contract_type) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            session.execute(insert_statement, (row.title, row.company, row.location, row.link, description, min_salary, max_salary, contrat))
            print(f"Les données de l'offre {row.title} ont été insérées dans job_details.")

        except Exception as e:
            print(f"Une erreur est survenue lors du traitement de l'offre {row.title}: {e}")

    # Fermer le driver Selenium
    driver.quit()