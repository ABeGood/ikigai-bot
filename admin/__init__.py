from flask import Flask
from flask_cors import CORS
from .app import app

app = Flask(__name__,
    static_folder='static',
    template_folder='templates'
)
CORS(app)

