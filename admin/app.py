# admin/app.py
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime
from db.connection import Database

app = Flask(__name__, 
    static_folder='static',
    template_folder='templates'
)
CORS(app)

# Get database instance
db = Database()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    today = datetime.now().date()
    todays_reservations = db.get_reservations_for_date(today)
    pending_payments = len([r for r in todays_reservations if r.payed == "False"])
    
    return jsonify({
        'todayBookings': len(todays_reservations),
        'pendingPayments': pending_payments
    })

@app.route('/api/reservations', methods=['GET'])
def get_reservations():
    date = request.args.get('date')
    if date:
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        # Get reservations for specific date
        reservations = db.get_reservations_for_date(target_date)
        # Convert to list of dictionaries
        reservations_list = []
        for res in reservations:
            reservations_list.append({
                'id': res.id,
                'order_id': res.order_id,
                'telegram_id': res.telegram_id,
                'name': res.name,
                'type': res.type,
                'place': res.place,
                'day': res.day.isoformat() if res.day else None,
                'time_from': res.time_from.isoformat() if res.time_from else None,
                'time_to': res.time_to.isoformat() if res.time_to else None,
                'period': res.period,
                'payed': res.payed
            })
        return jsonify(reservations_list)
    else:
        # For all reservations, use the existing to_dataframe method
        reservations_df = db.to_dataframe()
        return reservations_df.to_json(orient='records', date_format='iso')

@app.route('/api/reservations/<order_id>', methods=['DELETE'])
def delete_reservation(order_id):
    result = db.delete_reservation(order_id)
    return jsonify({'success': result is not None})

@app.route('/api/reservations/<order_id>', methods=['PUT'])
def update_reservation(order_id):
    data = request.json
    success = db.update_reservation(order_id, data)
    return jsonify({'success': success})

if __name__ == '__main__':
    app.run(debug=True, port=5000)