import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin import app
from flask import render_template
from db.connection import get_db
from db.repository import ReservationRepository

# Get database session
db = next(get_db())
reservation_repo = ReservationRepository(db)

@app.route('/')
def index():
    return render_template('index.html')

# API Routes
@app.route('/api/reservations', methods=['GET'])
def get_reservations():
    reservations = reservation_repo.to_dataframe()
    return reservations.to_json(orient='records', date_format='iso')

@app.route('/api/reservations/<order_id>', methods=['DELETE'])
def delete_reservation(order_id):
    result = reservation_repo.delete_reservation(order_id)
    return {'success': result is not None}

# @app.route('/api/reservations/<order_id>', methods=['PUT'])
# def update_reservation(order_id):
#     # TODO: Implement update logic
#     pass