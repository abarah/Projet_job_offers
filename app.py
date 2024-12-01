import re
import nltk
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
from resume_screening import resparser, match
from lxml import html

# Initialisation de Flask
app = Flask(__name__)
app.secret_key = 'secret'
os.makedirs(os.path.join(app.instance_path, 'resume_files'), exist_ok=True)



if __name__ == "__main__":
    app.run()
