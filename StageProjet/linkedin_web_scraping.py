from selenium import webdriver
from bs4 import BeautifulSoup
import csv
import time
import os


def main_linkedin(keyword, location, InternType):
    # Initialize the webdriver
    driver = webdriver.Chrome()

    if  InternType == "PFE":
        url = f'https://www.linkedin.com/jobs/search/?f_E=2&f_TP=1&keywords={keyword}&location={location}'
    elif InternType == "PFA":
        url = f'https://www.linkedin.com/jobs/search/?f_E=2&f_TP=1&f_JT=2&keywords={keyword}&location={location}'
    else :
        url = f'https://www.linkedin.com/jobs/search/?f_JT=F&geoId=103280457&keywords=stage%20{keyword}&location={location}'

    # Navigate to the LinkedIn job search page
    driver.get(url)

    # Wait for the page to load
    time.sleep(5)

    # Initialize a counter for the number of pages scraped
    page_count = 1

    # Open the file in append mode
    with open('linkedin_data.csv', mode='a', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)

        # Write the header row if the file is empty
        if os.stat('linkedin_data.csv').st_size == 0:
            header = ['Title', 'Company', 'Location', 'Description', 'Link']
            writer.writerow(header)

        # Loop through the first 4 pages of results
        while page_count <= 4:

            # Get the HTML of the current page
            page_html = driver.page_source

            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(page_html, 'html.parser')

            # Find all the job listings on the page
            jobs_list = soup.find_all('div', {'class': 'job-search-card'})

            # Loop through the job listings and extract the relevant data
            for job in jobs_list:
                title = job.h3.text.strip()
                company = job.h4.text.strip()
                location = job.find('span', class_='job-search-card__location').text.strip()
                link = job.a.get('href')

                # Open the job page to get the full job description
                driver.get(link)
                time.sleep(5)
                job_html = driver.page_source
                job_soup = BeautifulSoup(job_html, 'html.parser')
                description = job_soup.find('div', {'class': 'description__text'}).text.strip()

                # Write the job data to the CSV file
                writer.writerow([title, company, location, description, link])

                # Print the job data to the console
                #print(f'{title} ({company}) - {location}\nLink: {link}\nDescription: {description}\n')

            # Click the "Next" button to go to the next page
            try:
                next_button = driver.find_element_by_xpath('//button[@aria-label="Next"]')
                next_button.click()
                page_count += 1
                time.sleep(5)
            except:
                print('No more pages.')
                break

    # Close the webdriver
    driver.quit()
