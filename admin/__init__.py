from flask import Flask
from flask_cors import CORS

app = Flask(__name__,
    static_folder='static',
    template_folder='templates'
)
CORS(app)

from admin import routes