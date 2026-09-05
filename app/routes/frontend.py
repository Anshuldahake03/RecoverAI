from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

frontend_bp = Blueprint('frontend', __name__)


@frontend_bp.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('frontend.dashboard'))
    return render_template('landing.html')


@frontend_bp.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('frontend.dashboard'))
    return render_template('login.html')


@frontend_bp.route('/register')
def register_page():
    if current_user.is_authenticated:
        return redirect(url_for('frontend.dashboard'))
    return render_template('register.html')


@frontend_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@frontend_bp.route('/transactions')
@login_required
def transactions_page():
    return render_template('transactions.html')


@frontend_bp.route('/transactions/<transaction_id>')
@login_required
def transaction_detail_page(transaction_id):
    return render_template('transaction_detail.html', transaction_id=transaction_id)


@frontend_bp.route('/recovery')
@login_required
def recovery_page():
    return render_template('recovery.html')


@frontend_bp.route('/analytics')
@login_required
def analytics_page():
    return render_template('analytics.html')


@frontend_bp.route('/audit-logs')
@login_required
def audit_logs_page():
    return render_template('audit_logs.html')


@frontend_bp.route('/notifications')
@login_required
def notifications_page():
    return render_template('notifications.html')
