import nltk
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)


from resume_parser import resumeparse
############ Utility functions ############
def skill(resume_file):
    data = resumeparse.read_file(resume_file)
    resume = data['skills']
    skills = []
    skills.append(' '.join(word for word in resume))
    return skills

def parser(resume_file):
    data = resumeparse.read_file(resume_file)
    return data
