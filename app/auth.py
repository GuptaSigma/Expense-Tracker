from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from app import db, limiter
from app.models import User
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from config import Config
from app.utils import generate_otp, send_otp_email, get_otp_expiry_time
from datetime import datetime
import re

oauth = OAuth()

auth = Blueprint('auth', __name__)
EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def is_uptimerobot():
    """
    Exempt UptimeRobot checks from rate-limits.
    UptimeRobot user agent commonly contains 'UptimeRobot'.
    """
    ua = request.headers.get("User-Agent", "")
    return "UptimeRobot" in ua


def generate_unique_username(name):
    """Generate a unique username from a name using the pattern: NAME_123
    Example: SAGAR GUPTA -> SAGAR_GUPTA or SAGAR_GUPTA_123 if duplicate exists
    """
    # Convert name to uppercase and replace spaces with underscores
    base_username = name.strip().upper().replace(' ', '_')
    # Remove any special characters, keep only alphanumeric and underscores
    base_username = re.sub(r'[^A-Z0-9_]', '', base_username)

    # Check if base username is available
    if not User.query.filter_by(username=base_username).first():
        return base_username

    # If not available, append numbers: SAGAR_GUPTA_1, SAGAR_GUPTA_2, etc.
    counter = 1
    while True:
        new_username = f"{base_username}_{counter}"
        if not User.query.filter_by(username=new_username).first():
            return new_username
        counter += 1


@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute', exempt_when=is_uptimerobot)
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            if not user.is_email_verified:
                session['pending_verification_email'] = user.email
                flash('Login blocked: Verify OTP from email before login.', 'warning')
                return redirect(url_for('auth.verify_otp'))
            login_user(user)
            return redirect(url_for('main.dashboard'))

        flash('Invalid username or password', 'warning')

    return render_template('login.html')


@auth.route('/register', methods=['GET', 'POST'])
@limiter.limit('5 per minute', exempt_when=is_uptimerobot)
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not username:
            flash('Username is required', 'warning')
            return render_template('register.html')

        if not email or not EMAIL_PATTERN.match(email):
            flash('Please enter a valid email address', 'warning')
            return render_template('register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'warning')
            return render_template('register.html')

        user_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()

        if user_exists:
            flash('Username already exists', 'warning')
        elif email_exists:
            flash('Email already registered', 'warning')
        else:
            # Generate OTP
            otp = generate_otp()

            new_user = User(
                username=username,
                email=email,
                password=generate_password_hash(password),
                otp=otp,
                otp_expiry=get_otp_expiry_time()
            )
            db.session.add(new_user)
            db.session.commit()

            # Save email in session
            session['pending_verification_email'] = email

            # Send OTP email
            email_sent = send_otp_email(email, otp, username)

            if email_sent:
                flash('Registration successful! OTP sent to your email.', 'success')
            else:
                # Email failed but user is created - let them retry
                flash('Account created! Email not sent (check configuration). Use "Resend OTP" on next page.', 'warning')

            return redirect(url_for('auth.verify_otp'))

    return render_template('register.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth.route('/verify-otp', methods=['GET', 'POST'])
@limiter.limit('10 per minute', exempt_when=is_uptimerobot)
def verify_otp():
    """Verify OTP for email verification"""
    pending_email = session.get('pending_verification_email', '')

    if request.method == 'POST':
        email = pending_email
        otp = request.form.get('otp', '').strip()

        if not email:
            flash('Session expired. Please register again.', 'warning')
            return redirect(url_for('auth.register'))

        user = User.query.filter_by(email=email).first()

        if not user:
            flash('User not found', 'warning')
            return render_template('verify_otp.html', pending_email=pending_email)

        if not user.otp or not user.otp_expiry:
            flash('No OTP found. Please register again.', 'warning')
            return redirect(url_for('auth.register'))

        # Check if OTP expired
        if datetime.utcnow() > user.otp_expiry:
            flash('OTP has expired. Please request a new one.', 'warning')
            return render_template('verify_otp.html', pending_email=pending_email)

        # Verify OTP
        if user.otp == otp:
            user.is_email_verified = True
            user.otp = None
            user.otp_expiry = None
            db.session.commit()

            # Clear session
            session.pop('pending_verification_email', None)

            flash('Email verified successfully! Please login.', 'success')
            return redirect(url_for('auth.login'))
        else:
            # Debug info for development
            print(f"❌ OTP Mismatch - Expected: {user.otp}, Got: {otp}")
            flash('Invalid OTP. Please try again.', 'warning')
            return render_template('verify_otp.html', pending_email=pending_email)

    return render_template('verify_otp.html', pending_email=pending_email)


@auth.route('/resend-otp', methods=['POST'])
@limiter.limit('3 per minute', exempt_when=is_uptimerobot)
def resend_otp():
    """Resend OTP to email"""
    email = session.get('pending_verification_email')

    if not email:
        flash('Session expired. Please register again.', 'warning')
        return redirect(url_for('auth.register'))

    user = User.query.filter_by(email=email).first()

    if not user:
        flash('User not found', 'warning')
        return render_template('verify_otp.html', pending_email=email)

    # Generate new OTP
    otp = generate_otp()
    user.otp = otp
    user.otp_expiry = get_otp_expiry_time()
    db.session.commit()

    # Send new OTP
    if send_otp_email(email, otp, user.username):
        flash('OTP sent to your email!', 'success')
    else:
        flash('Failed to send OTP. Please try again.', 'danger')

    return render_template('verify_otp.html', pending_email=email)


# Google OAuth Routes
def init_google_oauth(app):
    """Initialize Google OAuth with Flask app"""
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=Config.GOOGLE_CLIENT_ID,
        client_secret=Config.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )


@auth.route('/auth/google')
def google_login():
    """Redirect user to Google for login"""
    if not Config.GOOGLE_CLIENT_ID or not Config.GOOGLE_CLIENT_SECRET:
        flash('Google authentication is not configured', 'warning')
        return redirect(url_for('auth.login'))

    google = oauth.google
    redirect_uri = url_for('auth.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@auth.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    if not Config.GOOGLE_CLIENT_ID or not Config.GOOGLE_CLIENT_SECRET:
        flash('Google authentication is not configured', 'warning')
        return redirect(url_for('auth.login'))

    google = oauth.google
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            flash('Failed to get user information from Google', 'warning')
            return redirect(url_for('auth.login'))

        google_id = user_info.get('sub')
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])

        # Check if user with this google_id already exists
        user = User.query.filter_by(google_id=google_id).first()

        if user:
            # User has already linked Google account, just login
            login_user(user)
            flash(f'Welcome back {user.username.upper()}!', 'success')
            return redirect(url_for('main.dashboard'))

        # Check if email already exists (user registered manually before)
        user = User.query.filter_by(email=email).first()

        if user:
            # Link Google account to existing user
            user.google_id = google_id
            if not user.is_email_verified:
                user.is_email_verified = True
            db.session.commit()
        else:
            # Create new user with unique username
            unique_username = generate_unique_username(name)
            user = User(
                username=unique_username,
                email=email,
                google_id=google_id,
                is_email_verified=True,
                password=generate_password_hash('google-oauth')  # Placeholder password
            )
            db.session.add(user)
            db.session.commit()

        login_user(user)
        flash(f'Welcome {user.username.upper()}!', 'success')
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        flash(f'Error during Google authentication: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))
