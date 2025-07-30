from flask import Flask, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from db.db_manager import FitnessDB
import secrets

app = Flask(__name__)
app.secret_key = 'sadjknaskdnkjasndkasjndkj'
app.config['CHAT_SERVICE_URL'] = 'http://localhost:8000'


db = FitnessDB()

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = db.get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            resp = redirect(url_for('dashboard'))
            return resp

        flash('Invalid credentials.', 'error')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        if db.get_user_by_email(email):
            flash('Email already registered.', 'error')
            return redirect(url_for('signup'))

        # 1) create the user
        password = request.form['password']
        hash_pw = generate_password_hash(password)
        user_id = db.create_user(
            email=email,
            password_hash=hash_pw,
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            date_of_birth=request.form.get('date_of_birth'),
            sex=request.form.get('sex'),
            height_cm=request.form.get('height_cm'),
            weight_kg=request.form.get('weight_kg'),
            activity_level=request.form.get('activity_level'),
            dietary_pref=request.form.get('dietary_pref'),
            fitness_goals=request.form.get('fitness_goals')
        )

        session['user_id'] = user_id
        flash('Account created and logged in.', 'success')
        resp = redirect(url_for('dashboard'))
        return resp

    return render_template('signup.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.get_user(session['user_id'])
    chat_url = current_app.config['CHAT_SERVICE_URL']

    return render_template('dashboard.html',
                           user=user,
                           chat_url=chat_url)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)