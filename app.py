from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import threading

# Konfiguracja aplikacji
app = Flask(__name__)
app.config['SECRET_KEY'] = 'bardzo-tajny-klucz'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicjalizacja bazy danych
db = SQLAlchemy(app)

# MODELE
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Nowe')
    admin_comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# DEKORATORY
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Dostęp tylko dla administratorów', 'danger')
            return redirect(url_for('user_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ROUTES OGÓLNE
@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['email'] = user.email
            session['role'] = user.role
            flash('Zalogowano pomyślnie!', 'success')
            return redirect(url_for('admin_dashboard') if user.role == 'admin' else url_for('user_dashboard'))
        else:
            flash('Nieprawidłowy email lub hasło', 'danger')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Hasła nie są identyczne', 'danger')
            return redirect(url_for('register'))
        if len(password) < 6:
            flash('Hasło musi mieć co najmniej 6 znaków', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email już istnieje', 'danger')
            return redirect(url_for('register'))
        new_user = User(email=email, password=generate_password_hash(password, method='sha256'))
        db.session.add(new_user)
        db.session.commit()
        flash('Konto utworzone pomyślnie! Zaloguj się.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Wylogowano pomyślnie', 'success')
    return redirect(url_for('login'))

# USER ROUTES
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    user_orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.created_at.desc()).limit(5).all()
    return render_template('user/dashboard.html', orders=user_orders)

@app.route('/user/orders')
@login_required
def user_orders():
    orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.created_at.desc()).all()
    return render_template('user/orders.html', orders=orders)

@app.route('/user/order/<int:order_id>')
@login_required
def order_status(order_id):
    order = Order.query.filter_by(id=order_id, user_id=session['user_id']).first_or_404()
    return render_template('user/order_status.html', order=order)

@app.route('/user/new_order', methods=['GET', 'POST'])
@login_required
def new_order():
    if request.method == 'POST':
        website_type = request.form['website_type']
        pages_count = request.form['pages_count']
        features = request.form['features']
        deadline = request.form['deadline']
        budget = request.form['budget']
        name = request.form['name']
        email = request.form['email']
        phone = request.form.get('phone', '')
        description = f"""
        Typ strony: {website_type}
        Liczba podstron: {pages_count}
        Funkcjonalności: {features}
        Termin realizacji: {deadline}
        Budżet: {budget} PLN
        Dane kontaktowe:
        - Imię i nazwisko: {name}
        - Email: {email}
        - Telefon: {phone or 'Nie podano'}
        """
        new_order = Order(
            title=f"Wycena strony: {website_type}",
            description=description,
            user_id=session['user_id']
        )
        db.session.add(new_order)
        db.session.commit()
        flash('Formularz wyceny został wysłany pomyślnie!', 'success')
        return redirect(url_for('order_status', order_id=new_order.id))
    return render_template('user/new_order_form.html')

# ADMIN ROUTES
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    new_orders_count = Order.query.filter_by(status='Nowe').count()
    in_progress_orders_count = Order.query.filter_by(status='W trakcie').count()
    completed_orders_count = Order.query.filter_by(status='Zakończone').count()
    users_count = User.query.count()
    return render_template('admin/dashboard.html',
                           recent_orders=recent_orders,
                           new_orders=new_orders_count,
                           in_progress=in_progress_orders_count,
                           completed=completed_orders_count,
                           users=users_count)

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    status = request.args.get('status', 'all')
    if status == 'new':
        orders = Order.query.filter_by(status='Nowe').order_by(Order.created_at.desc()).all()
    elif status == 'in_progress':
        orders = Order.query.filter_by(status='W trakcie').order_by(Order.created_at.desc()).all()
    elif status == 'completed':
        orders = Order.query.filter_by(status='Zakończone').order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders, status=status)

@app.route('/admin/order/<int:order_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if request.method == 'POST':
        order.status = request.form['status']
        order.admin_comment = request.form['admin_comment']
        db.session.commit()
        flash('Zamówienie zaktualizowane', 'success')
        return redirect(url_for('admin_order_detail', order_id=order.id))
    return render_template('admin/order_detail.html', order=order, user=order.user)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

# START APLIKACJI
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email='admin@example.com').first():
            admin = User(
                email='admin@example.com',
                password=generate_password_hash('admin123', method='sha256'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
    if __name__ == "__main__":
        app.run(host='0.0.0.0')
