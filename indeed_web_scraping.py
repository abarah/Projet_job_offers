from selenium import webdriver
import csv
from selenium.webdriver.common.by import By
import time

def main_indeed(keyword,location, InternType):
    # Initialiser le driver de Selenium
    driver = webdriver.Chrome()
    # Se rendre sur la page de recherche d'offres d'emploi Indeed
    if InternType == "PFE":
        url =f'https://www.indeed.com/jobs?q=PFE+{keyword}&l={location}&lang=en'
    elif InternType == "PFA":
        url =f'https://www.indeed.com/jobs?q=PFA+{keyword}&l={location}&lang=en'
    else :
        url =f'https://www.indeed.com/jobs?q=internship+{keyword}&l={location}&lang=en'
    #url = f'https://ma.indeed.com/jobs?q={keyword}&l={location}&lang=en'
    driver.get(url)

    # Attendre 5 secondes pour que tous les éléments soient chargés
    time.sleep(5)


    # Extraire les résultats
    jobs_list = driver.find_elements(By.XPATH,'//div[contains(@class, "job_seen_beacon")]')

    # Écrire les résultats dans un fichier CSV
    with open('indeed_data.csv', mode='w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Title', 'Company', 'Location', 'Description', 'Link'])

        for job in jobs_list:
            title = job.find_element(By.XPATH,'.//a[contains(@class, "jcs-JobTitle")]').text.strip()
            # Vérifier si la liste contenant les éléments de la société n'est pas vide avant d'extraire la chaîne de texte
            company = job.find_elements(By.CSS_SELECTOR, 'span.companyName')
            if company:
                company = company[0].text.strip()
            else:
                company = ""
            description = driver.find_element(By.ID, 'jobDescriptionText').text.strip()
            location = job.find_element(By.XPATH,'.//div[contains(@data-testid, "text-location")]').text.strip()
            link = job.find_element(By.XPATH,'.//a[contains(@class, "jcs-JobTitle")]').get_attribute('href')
            writer.writerow([title, company, location, description, link])
            #print(f'{title} ({company}) - {location}\nLink: {link}\n')
