from admin.app import app
from db.connection import Database
from dotenv import load_dotenv
import os

if __name__ == '__main__':
    load_dotenv()
    reservations_db = Database()
    app.config['DATABASE'] = reservations_db
    app.run(host='0.0.0.0', port=os.getenv('PORT', 5000))