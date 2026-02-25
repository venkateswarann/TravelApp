#!/usr/bin/env python3
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from urllib.parse import urlparse
import time
import requests
from bs4 import BeautifulSoup
import json
import qrcode
import io
from base64 import b64encode

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'force-logout-key-1771970186')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

from werkzeug.security import generate_password_hash, check_password_hash

# ... existing code ...

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Trips owned by this user
    trips = db.relationship('Trip', backref='owner', lazy=True)

# Join table for shared trips
trip_sharing = db.Table('trip_sharing',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('trip_id', db.Integer, db.ForeignKey('trip.id'), primary_key=True)
)

class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_location = db.Column(db.String(200))
    end_location = db.Column(db.String(200))
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    itineraries = db.relationship('Itinerary', backref='trip', lazy=True, cascade='all, delete-orphan')
    hotels = db.relationship('Hotel', backref='trip', lazy=True, cascade='all, delete-orphan')
    travel_infos = db.relationship('TravelInfo', backref='trip', lazy=True, cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='trip', lazy=True, cascade='all, delete-orphan')
    
    # Users this trip is shared with
    shared_with = db.relationship('User', secondary=trip_sharing, backref=db.backref('shared_trips', lazy='dynamic'))
    # Linked checklist items
    checklist_items = db.relationship('ChecklistItem', backref='trip', lazy=True, cascade='all, delete-orphan')

class Itinerary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    from_location = db.Column(db.String(200))
    to_location = db.Column(db.String(200))
    from_lat = db.Column(db.Float)
    from_lng = db.Column(db.Float)
    to_lat = db.Column(db.Float)
    to_lng = db.Column(db.Float)
    transport_mode = db.Column(db.String(100))  # train, flight, car, bus, etc.
    transport_time = db.Column(db.String(100))
    estimated_duration = db.Column(db.String(100))
    notes = db.Column(db.Text)
    morning_plan = db.Column(db.Text)
    afternoon_plan = db.Column(db.Text)
    evening_plan = db.Column(db.Text)
    night_plan = db.Column(db.Text)
    ticket_id = db.Column(db.Integer, db.ForeignKey('travel_info.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # New dynamic activities relationship
    activities = db.relationship('Activity', backref='itinerary', lazy=True, cascade='all, delete-orphan')

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    itinerary_id = db.Column(db.Integer, db.ForeignKey('itinerary.id'), nullable=False)
    start_time = db.Column(db.String(10)) # e.g. "09:00"
    end_time = db.Column(db.String(10))   # e.g. "11:00"
    title = db.Column(db.String(100))     # e.g. "Lunch"
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Linked expenses for this activity
    expenses = db.relationship('Expense', backref='activity', lazy=True, cascade='all, delete-orphan')
    # Linked sub-activities
    sub_activities = db.relationship('SubActivity', backref='activity', lazy=True, cascade='all, delete-orphan')

class ChecklistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SubActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def get_coords(location_name):
    """Fetch coordinates from OpenStreetMap Nominatim API"""
    if not location_name:
        return None, None
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={location_name}&format=json&limit=1"
        headers = {'User-Agent': 'TravelPlannerApp/1.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"Geocoding error for {location_name}: {e}")
    return None, None

class Hotel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    name = db.Column(db.String(200))
    url = db.Column(db.String(500))
    address = db.Column(db.Text)
    check_in = db.Column(db.Date)
    check_out = db.Column(db.Date)
    notes = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    pdf_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TravelInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    name = db.Column(db.String(200))
    type = db.Column(db.String(50))  # flight, train, bus
    number = db.Column(db.String(100))  # flight number, train number
    departure = db.Column(db.String(200))
    arrival = db.Column(db.String(200))
    departure_time = db.Column(db.DateTime)
    arrival_time = db.Column(db.DateTime)
    booking_reference = db.Column(db.String(100))
    seat = db.Column(db.String(50))
    notes = db.Column(db.Text)
    pdf_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Backref for linked itinerary items
    linked_itineraries = db.relationship('Itinerary', backref='ticket', lazy=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=True) # NEW: Link to activity
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='EUR')  # EUR, CHF, GBP
    category = db.Column(db.String(100))  # transport, hotel, food, activities, etc.
    paid_by = db.Column(db.String(100), nullable=False)  # your name or friend's name
    date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables and default admin
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin created (admin / admin123)")

@app.before_request
def check_auth():
    # Allow access to login page and static files without password
    if request.endpoint in ['login', 'static'] or not request.endpoint:
        return
    # Ensure BOTH authenticated flag and user_id exist
    if not session.get('authenticated') or not session.get('user_id'):
        session.clear() # Clear stale sessions
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session.clear() # Start fresh
            session['authenticated'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            return redirect(url_for('index'))
        flash('Invalid username or password!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Routes
@app.route('/')
def index():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    
    if not user:
        session.clear()
        return redirect(url_for('login'))

    # Show trips owned by user OR shared with user
    my_trips = Trip.query.filter_by(user_id=user_id).all()
    shared_trips = user.shared_trips.all()
    
    # Combine and sort by start date
    all_trips = sorted(my_trips + shared_trips, key=lambda x: x.start_date, reverse=True)
    
    # Calculate unique locations as a proxy for countries
    locations = set()
    for t in all_trips:
        if t.start_location: locations.add(t.start_location.split(',')[-1].strip())
        if t.end_location: locations.add(t.end_location.split(',')[-1].strip())
    
    return render_template('index.html', trips=all_trips, location_count=len(locations))

@app.route('/add-trip', methods=['GET', 'POST'])
def add_trip():
    if request.method == 'POST':
        try:
            trip = Trip(
                user_id=session['user_id'],
                name=request.form['name'],
                description=request.form.get('description'),
                start_location=request.form.get('start_location'),
                end_location=request.form.get('end_location'),
                start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d'),
                end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d')
            )
            db.session.add(trip)
            db.session.commit()
            flash('Trip created successfully!', 'success')
            return redirect(url_for('trip_detail', trip_id=trip.id))
        except Exception as e:
            flash(f'Error creating trip: {str(e)}', 'error')
            return redirect(url_for('index'))
    return render_template('add_trip.html')

@app.route('/trip/<int:trip_id>/edit', methods=['GET', 'POST'])
def edit_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if request.method == 'POST':
        try:
            trip.name = request.form['name']
            trip.description = request.form.get('description')
            trip.start_location = request.form.get('start_location')
            trip.end_location = request.form.get('end_location')
            trip.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            trip.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
            db.session.commit()
            flash('Trip updated successfully!', 'success')
            return redirect(url_for('trip_detail', trip_id=trip_id))
        except Exception as e:
            flash(f'Error updating trip: {str(e)}', 'error')
    return render_template('edit_trip.html', trip=trip)

@app.route('/trip/<int:trip_id>/delete', methods=['POST'])
def delete_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    try:
        db.session.delete(trip)
        db.session.commit()
        flash('Trip deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting trip: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/trip/<int:trip_id>')
def trip_detail(trip_id):
    trip = Trip.query.get_or_404(trip_id)

    # Calculate expense summary
    total_expenses = db.session.query(db.func.sum(Expense.amount)).filter_by(trip_id=trip_id).scalar() or 0
    expenses_by_person = db.session.query(
        Expense.paid_by,
        db.func.sum(Expense.amount).label('total'),
        db.func.count(Expense.id).label('count')
    ).filter_by(trip_id=trip_id).group_by(Expense.paid_by).all()

    # Calculate what each person owes
    owes = {}
    if len(expenses_by_person) == 2:
        amounts = {person.paid_by: person.total for person in expenses_by_person}
        people = list(amounts.keys())
        if len(people) == 2:
            avg_amount = sum(amounts.values()) / 2
            owes[people[0]] = amounts[people[1]] - avg_amount
            owes[people[1]] = amounts[people[0]] - avg_amount

    # Calculate breakdown by category (Label)
    category_breakdown = db.session.query(
        Expense.category,
        db.func.sum(Expense.amount).label('total')
    ).filter_by(trip_id=trip_id).group_by(Expense.category).all()

    return render_template('trip_detail.html', trip=trip,
                         total_expenses=total_expenses,
                         expenses_by_person=expenses_by_person,
                         owes=owes,
                         category_breakdown=category_breakdown)

@app.route('/api/trip/<int:trip_id>/itineraries-by-date')
def api_itineraries_by_date(trip_id):
    itineraries = Itinerary.query.filter_by(trip_id=trip_id).order_by(Itinerary.date).all()
    by_date = {}
    for itin in itineraries:
        date_str = itin.date.isoformat()
        if date_str not in by_date:
            by_date[date_str] = []
        by_date[date_str].append({
            'id': itin.id,
            'from': itin.from_location,
            'to': itin.to_location,
            'transport': itin.transport_mode,
            'time': itin.transport_time,
            'duration': itin.estimated_duration,
            'notes': itin.notes
        })
    return jsonify(by_date)

@app.route('/trip/<int:trip_id>/add-itinerary', methods=['POST'])
def add_itinerary(trip_id):
    data = request.form
    try:
        from_loc = data.get('from_location')
        to_loc = data.get('to_location')
        
        # Geocode locations
        f_lat, f_lng = get_coords(from_loc)
        time.sleep(1) # Rate limiting
        t_lat, t_lng = get_coords(to_loc)

        # Estimate travel time if not provided
        duration = data.get('duration')
        if not duration and from_loc and to_loc:
            duration = estimate_travel_time(from_loc, to_loc, data.get('transport_mode'))

        itinerary = Itinerary(
            trip_id=trip_id,
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            from_location=from_loc,
            to_location=to_loc,
            from_lat=f_lat,
            from_lng=f_lng,
            to_lat=t_lat,
            to_lng=t_lng,
            transport_mode=data.get('transport_mode'),
            transport_time=data.get('transport_time'),
            estimated_duration=duration,
            notes=data.get('notes'),
            morning_plan=data.get('morning_plan'),
            afternoon_plan=data.get('afternoon_plan'),
            evening_plan=data.get('evening_plan'),
            night_plan=data.get('night_plan'),
            ticket_id=data.get('ticket_id') if data.get('ticket_id') else None
        )
        db.session.add(itinerary)
        db.session.commit()
        flash('Itinerary added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding itinerary: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#itin')

@app.route('/trip/<int:trip_id>/itinerary/<int:itinerary_id>/add-activity', methods=['POST'])
def add_activity(trip_id, itinerary_id):
    try:
        activity = Activity(
            itinerary_id=itinerary_id,
            start_time=request.form.get('start_time'),
            end_time=request.form.get('end_time'),
            title=request.form.get('title'),
            description=request.form.get('description')
        )
        db.session.add(activity)
        db.session.flush() # Get activity ID before commit

        # If expense added
        amount = request.form.get('expense_amount')
        if amount and float(amount) > 0:
            expense = Expense(
                trip_id=trip_id,
                activity_id=activity.id,
                description=f"Activity: {activity.title}",
                amount=float(amount),
                currency=request.form.get('currency', 'EUR'),
                category=request.form.get('category', 'Activity'), # Added category
                paid_by=session.get('username', 'Me'),
                date=db.session.get(Itinerary, itinerary_id).date
            )
            db.session.add(expense)

        db.session.commit()
        flash('Activity and Expense added!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#itin')

@app.route('/trip/<int:trip_id>/activity/<int:activity_id>/edit', methods=['POST'])
def edit_activity(trip_id, activity_id):
    activity = Activity.query.get_or_404(activity_id)
    try:
        activity.start_time = request.form.get('start_time')
        activity.end_time = request.form.get('end_time')
        activity.title = request.form.get('title')
        activity.description = request.form.get('description')
        
        # Update or create linked expense
        amount = request.form.get('expense_amount')
        if amount and float(amount) > 0:
            expense = Expense.query.filter_by(activity_id=activity.id).first()
            if not expense:
                expense = Expense(trip_id=trip_id, activity_id=activity.id, paid_by=session.get('username', 'Me'), date=activity.itinerary.date)
                db.session.add(expense)
            
            expense.description = f"Activity: {activity.title}"
            expense.amount = float(amount)
            expense.currency = request.form.get('currency', 'EUR')
            expense.category = request.form.get('category', 'Activity') # Added category
        else:
            # If amount is removed, delete existing expense
            expense = Expense.query.filter_by(activity_id=activity.id).first()
            if expense: db.session.delete(expense)

        db.session.commit()
        flash('Activity updated!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#itin')

@app.route('/trip/<int:trip_id>/activity/<int:activity_id>/delete', methods=['POST'])
def delete_activity(trip_id, activity_id):
    activity = Activity.query.get_or_404(activity_id)
    db.session.delete(activity)
    db.session.commit()
    return redirect(url_for('trip_detail', trip_id=trip_id))

@app.route('/trip/<int:trip_id>/activity/<int:activity_id>/add-sub', methods=['POST'])
def add_sub_activity(trip_id, activity_id):
    try:
        sub = SubActivity(
            activity_id=activity_id,
            description=request.form.get('description')
        )
        db.session.add(sub)
        db.session.commit()
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#itin')

@app.route('/trip/<int:trip_id>/sub-activity/<int:sub_id>/delete', methods=['POST'])
def delete_sub_activity(trip_id, sub_id):
    sub = SubActivity.query.get_or_404(sub_id)
    db.session.delete(sub)
    db.session.commit()
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#itin')

@app.route('/trip/<int:trip_id>/edit-itinerary/<int:itinerary_id>', methods=['POST'])
def edit_itinerary(trip_id, itinerary_id):
    itinerary = Itinerary.query.get_or_404(itinerary_id)
    data = request.form
    try:
        from_loc = data.get('from_location')
        to_loc = data.get('to_location')
        
        # Only re-geocode if locations changed
        if from_loc != itinerary.from_location:
            itinerary.from_lat, itinerary.from_lng = get_coords(from_loc)
        if to_loc != itinerary.to_location:
            itinerary.to_lat, itinerary.to_lng = get_coords(to_loc)

        itinerary.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        itinerary.from_location = from_loc
        itinerary.to_location = to_loc
        itinerary.transport_mode = data.get('transport_mode')
        itinerary.transport_time = data.get('transport_time')
        itinerary.notes = data.get('notes')
        itinerary.morning_plan = data.get('morning_plan')
        itinerary.afternoon_plan = data.get('afternoon_plan')
        itinerary.evening_plan = data.get('evening_plan')
        itinerary.night_plan = data.get('night_plan')
        itinerary.ticket_id = data.get('ticket_id') if data.get('ticket_id') else None
        
        db.session.commit()
        flash('Itinerary updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating itinerary: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#itin')

@app.route('/trip/<int:trip_id>/delete-itinerary/<int:itinerary_id>', methods=['POST'])
def delete_itinerary(trip_id, itinerary_id):
    try:
        itinerary = Itinerary.query.get_or_404(itinerary_id)
        if itinerary.trip_id != trip_id:
            flash('Itinerary not found in this trip', 'error')
        else:
            db.session.delete(itinerary)
            db.session.commit()
            flash('Itinerary deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting itinerary: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#itin')
# Hotel, Travel, Expense routes


# Additional Routes - Hotel Management
@app.route('/trip/<int:trip_id>/add-hotel', methods=['POST'])
def add_hotel(trip_id):
    data = request.form
    try:
        # Handle PDF upload
        pdf_filename = None
        if 'pdf' in request.files:
            file = request.files['pdf']
            if file and file.filename:
                filename = secure_filename(file.filename)
                pdf_filename = f"hotel_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename))

        # Scrape hotel info if URL provided
        address = data.get('address') or ""
        lat, lng = None, None

        if data.get('url'):
            scraped_info = scrape_hotel_info(data['url'])
            if scraped_info:
                address = scraped_info.get('address', '') or address
                lat = scraped_info.get('lat')
                lng = scraped_info.get('lng')

        hotel = Hotel(
            trip_id=trip_id,
            name=data.get('name'),
            url=data.get('url'),
            address=address,
            check_in=datetime.strptime(data['check_in'], '%Y-%m-%d').date() if data.get('check_in') else None,
            check_out=datetime.strptime(data['check_out'], '%Y-%m-%d').date() if data.get('check_out') else None,
            notes=data.get('notes'),
            latitude=lat,
            longitude=lng,
            pdf_filename=pdf_filename
        )
        db.session.add(hotel)
        db.session.commit()
        flash('Hotel added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding hotel: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#hotel')

@app.route('/trip/<int:trip_id>/delete-hotel/<int:hotel_id>', methods=['POST'])
def delete_hotel(trip_id, hotel_id):
    try:
        hotel = Hotel.query.get_or_404(hotel_id)
        if hotel.trip_id != trip_id:
            flash('Hotel not found in this trip', 'error')
        else:
            # Delete associated PDF if exists
            if hotel.pdf_filename:
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], hotel.pdf_filename)
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            db.session.delete(hotel)
            db.session.commit()
            flash('Hotel deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting hotel: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#hotel')

# Travel Info Routes
@app.route('/trip/<int:trip_id>/add-travel-info', methods=['POST'])
def add_travel_info(trip_id):
    try:
        # Handle PDF upload
        pdf_filename = None
        if 'pdf' in request.files:
            file = request.files['pdf']
            if file and file.filename:
                filename = secure_filename(file.filename)
                pdf_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename))

        travel_info = TravelInfo(
            trip_id=trip_id,
            name=request.form.get('name'),
            type=request.form['type'],
            number=request.form.get('number'),
            departure=request.form.get('departure'),
            arrival=request.form.get('arrival'),
            departure_time=datetime.fromisoformat(request.form['departure_time']).replace(tzinfo=None) if request.form.get('departure_time') else None,
            arrival_time=datetime.fromisoformat(request.form['arrival_time']).replace(tzinfo=None) if request.form.get('arrival_time') else None,
            booking_reference=request.form.get('booking_reference'),
            seat=request.form.get('seat'),
            notes=request.form.get('notes'),
            pdf_filename=pdf_filename
        )
        db.session.add(travel_info)
        db.session.commit()
        flash('Travel info added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding travel info: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#docs')

@app.route('/trip/<int:trip_id>/delete-travel-info/<int:travel_info_id>', methods=['POST'])
def delete_travel_info(trip_id, travel_info_id):
    try:
        travel = TravelInfo.query.get_or_404(travel_info_id)
        if travel.trip_id != trip_id:
            flash('Travel info not found in this trip', 'error')
        else:
            # Delete associated PDF if exists
            if travel.pdf_filename:
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], travel.pdf_filename)
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            db.session.delete(travel)
            db.session.commit()
            flash('Travel info deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting travel info: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#docs')

# Expense Routes
@app.route('/trip/<int:trip_id>/add-expense', methods=['POST'])
def add_expense(trip_id):
    try:
        expense = Expense(
            trip_id=trip_id,
            description=request.form['description'],
            amount=float(request.form['amount']),
            currency=request.form.get('currency', 'EUR'),
            category=request.form.get('category', 'Other'),
            paid_by=request.form['paid_by'],
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            notes=request.form.get('notes')
        )
        db.session.add(expense)
        db.session.commit()
        flash('Expense added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding expense: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#exp')

@app.route('/trip/<int:trip_id>/delete-expense/<int:expense_id>', methods=['POST'])
def delete_expense(trip_id, expense_id):
    try:
        expense = Expense.query.get_or_404(expense_id)
        if expense.trip_id != trip_id:
            flash('Expense not found in this trip', 'error')
        else:
            db.session.delete(expense)
            db.session.commit()
            flash('Expense deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting expense: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#exp')

@app.route('/trip/<int:trip_id>/edit-expense/<int:expense_id>', methods=['POST'])
def edit_expense(trip_id, expense_id):
    expense = Expense.query.get_or_404(expense_id)
    try:
        expense.description = request.form['description']
        expense.amount = float(request.form['amount'])
        expense.currency = request.form.get('currency', 'EUR')
        expense.category = request.form.get('category', 'Other')
        expense.paid_by = request.form['paid_by']
        expense.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        db.session.commit()
        flash('Expense updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating expense: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#exp')

# CHECKLIST ROUTES
@app.route('/trip/<int:trip_id>/checklist/add', methods=['POST'])
def add_checklist_item(trip_id):
    try:
        item = ChecklistItem(
            trip_id=trip_id,
            description=request.form.get('description')
        )
        db.session.add(item)
        db.session.commit()
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#check')

@app.route('/trip/<int:trip_id>/checklist/<int:item_id>/toggle', methods=['POST'])
def toggle_checklist_item(trip_id, item_id):
    item = ChecklistItem.query.get_or_404(item_id)
    item.is_completed = not item.is_completed
    db.session.commit()
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#check')

@app.route('/trip/<int:trip_id>/checklist/<int:item_id>/delete', methods=['POST'])
def delete_checklist_item(trip_id, item_id):
    item = ChecklistItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('trip_detail', trip_id=trip_id) + '#check')

# ADMIN ROUTES
@app.route('/admin/users')
def admin_users():
    if not session.get('is_admin'):
        flash('Unauthorized!', 'error')
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/add-user', methods=['POST'])
def admin_add_user():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    username = request.form.get('username')
    password = request.form.get('password')
    if User.query.filter_by(username=username).first():
        flash('User already exists!', 'error')
    else:
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            is_admin=False
        )
        db.session.add(new_user)
        db.session.commit()
        flash(f'User {username} created!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    user = User.query.get_or_404(user_id)
    if user.username == 'admin':
        flash('Cannot delete main admin!', 'error')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted!', 'success')
    return redirect(url_for('admin_users'))

# SHARING ROUTE
@app.route('/trip/<int:trip_id>/share', methods=['POST'])
def share_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    # Only owner can share
    if trip.user_id != session.get('user_id'):
        flash('Only the owner can share this trip!', 'error')
        return redirect(url_for('trip_detail', trip_id=trip_id))
    
    target_username = request.form.get('username')
    target_user = User.query.filter_by(username=target_username).first()
    
    if not target_user:
        flash('User not found!', 'error')
    elif target_user.id == trip.user_id:
        flash('You already own this trip!', 'info')
    elif target_user in trip.shared_with:
        flash('Trip already shared with this user!', 'info')
    else:
        trip.shared_with.append(target_user)
        db.session.commit()
        flash(f'Trip shared with {target_username}!', 'success')
    
    return redirect(url_for('trip_detail', trip_id=trip_id))

@app.route('/trip/<int:trip_id>/revoke-share/<int:user_id>', methods=['POST'])
def revoke_share(trip_id, user_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != session.get('user_id'):
        flash('Unauthorized!', 'error')
        return redirect(url_for('trip_detail', trip_id=trip_id))
    
    target_user = User.query.get_or_404(user_id)
    if target_user in trip.shared_with:
        trip.shared_with.remove(target_user)
        db.session.commit()
        flash(f'Access revoked for {target_user.username}', 'success')
    
    return redirect(url_for('trip_detail', trip_id=trip_id))

# PDF Serving
@app.route('/uploads/<filename>')
def serve_pdf(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Helper Functions
def estimate_travel_time(from_loc, to_loc, transport_mode):
    """Estimate travel time between locations"""
    if not from_loc or not to_loc:
        return None

    # Simple heuristics based on transport mode
    if transport_mode == 'flight':
        if any(c in [from_loc, to_loc] for c in ['London', 'Paris', 'Zurich', 'Geneva']):
            return "2h 30m"
        return "3h 30m"
    elif transport_mode == 'train':
        if from_loc == 'London' and to_loc == 'Paris':
            return "2h 20m"
        elif from_loc == 'Paris' and to_loc == 'Zurich':
            return "4h 30m"
        elif from_loc == 'Zurich' and to_loc == 'London':
            return "8h 00m"
        return "5h 00m"
    elif transport_mode == 'bus':
        return "6h 00m"
    elif transport_mode == 'car':
        return "4h 30m"
    return "3h 00m"

def scrape_hotel_info(url):
    """Scrape hotel information from booking URL"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        info = {}

        # Try to find address
        address_selectors = [
            '[data-testid="address"]', '[class*="address"]',
            '[class*="Address"]'
        ]
        for selector in address_selectors:
            address_elem = soup.select_one(selector)
            if address_elem:
                info['address'] = address_elem.get_text(strip=True)
                break

        # Try to find latitude/longitude from meta
        lat = soup.find('meta', {'property': 'place:location:latitude'})
        lng = soup.find('meta', {'property': 'place:location:longitude'})
        if lat and lng:
            info['lat'] = float(lat['content'])
            info['lng'] = float(lng['content'])

        # Try to get hotel name from title
        if soup.title:
            title_text = soup.title.get_text()
            info['name'] = title_text.split('|')[0].split('-')[0].strip()

        return info
    except Exception as e:
        print(f"Error scraping hotel info: {e}")
        return None

@app.route('/api/estimate-travel-time')
def api_estimate_travel_time():
    from_loc = request.args.get('from')
    to_loc = request.args.get('to')
    mode = request.args.get('mode')
    duration = estimate_travel_time(from_loc, to_loc, mode)
    return jsonify({'duration': duration})

# Initialize and run
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("Starting Travel Planner app...")
    print("Access via: http://jetsonvivek:5000 or http://jetsonvivek.tailnetname.ts.net:5000")
    app.run(host='0.0.0.0', port=5001, debug=True)
