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





app=Flask(__name__)

os.makedirs(os.path.join(app.instance_path, 'resume_files'), exist_ok=True)

keyword=''
location=''
InternType=''
app.secret_key = 'secret'


    
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






if __name__ == "__main__":
    app.run()
