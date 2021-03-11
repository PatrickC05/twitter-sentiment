import os
from flask import Flask

app = Flask(__name__)
app.run(os.environ.get('PORT'))

@app.route('/')
def index():
    return "Hello"

@app.route('/update')
def update():
    os.system('python3 upload-csv.py')
    return "Update"
