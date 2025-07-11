# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os
from functools import wraps
from datetime import date
from markupsafe import escape
#app = Flask(__name__)
#app.config.from_pyfile('config.py')
from config import config
app = Flask(__name__)
app.config.from_object(config['development'])  # or 'production' as needed
config['development'].init_app(app)

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # intern, supervisor, manager, admin
    department = db.Column(db.String(50))
    supervisor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, inactive
    
    supervisor = db.relationship('User', remote_side=[id], backref='interns')
    
    def __repr__(self):
        return f'<User {self.email}>'

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    time_in = db.Column(db.Time, nullable=False)
    time_out = db.Column(db.Time)
    status = db.Column(db.String(20), default='present')  # present, late, absent
    notes = db.Column(db.Text)
    
    user = db.relationship('User', backref='attendance_records')

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    report_type = db.Column(db.String(20), nullable=False)  # weekly, monthly, final
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.Date)
    file_path = db.Column(db.String(200))
    content = db.Column(db.Text)
    status = db.Column(db.String(20), default='submitted')  # submitted, reviewed, approved
    feedback = db.Column(db.Text)
    
    user = db.relationship('User', foreign_keys=[user_id], backref='reports_submitted')
    supervisor = db.relationship('User', foreign_keys=[supervisor_id], backref='reports_to_review')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    is_urgent = db.Column(db.Boolean, default=False)
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='messages_sent')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='messages_received')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    intern_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    assigned_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed
    completion_notes = db.Column(db.Text)
    
    supervisor = db.relationship('User', foreign_keys=[supervisor_id], backref='tasks_assigned')
    intern = db.relationship('User', foreign_keys=[intern_id], backref='tasks_received')

# Helper Functions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'danger')
                return redirect(url_for('login'))
            
            user = User.query.get(session['user_id'])
            if user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = f"{user.first_name} {user.last_name}"
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'intern')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password,
            role=role,
            status='active'
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    
    if user.role == 'intern':
        # Get attendance stats
        total_days = Attendance.query.filter_by(user_id=user.id).count()
        present_days = Attendance.query.filter_by(user_id=user.id, status='present').count()
        attendance_percentage = round((present_days / total_days) * 100, 2) if total_days > 0 else 0
        
        # Get pending tasks
        pending_tasks = Task.query.filter_by(intern_id=user.id, status='pending').count()
        
        # Get recent reports
        recent_reports = Report.query.filter_by(user_id=user.id).order_by(Report.submission_date.desc()).limit(3).all()
        
        return render_template('dashboard/intern.html', 
                            attendance_percentage=attendance_percentage,
                            pending_tasks=pending_tasks,
                            recent_reports=recent_reports)
    
    elif user.role == 'supervisor':
        # Get intern count
        intern_count = User.query.filter_by(supervisor_id=user.id).count()
        
        # Get pending reports to review
        pending_reports = Report.query.filter_by(supervisor_id=user.id, status='submitted').count()
        
        # Get attendance issues
        attendance_issues = db.session.query(Attendance).join(User).filter(
            User.supervisor_id == user.id,
            Attendance.status != 'present'
        ).count()
        
        return render_template('dashboard/supervisor.html',
                            intern_count=intern_count,
                            pending_reports=pending_reports,
                            attendance_issues=attendance_issues)
    
    elif user.role == 'manager':
        # Get organization stats
        total_interns = User.query.filter_by(role='intern').count()
        active_interns = User.query.filter_by(role='intern', status='active').count()
        total_supervisors = User.query.filter_by(role='supervisor').count()
        
        # Get recent reports
        recent_reports = Report.query.order_by(Report.submission_date.desc()).limit(5).all()
        
        return render_template('dashboard/manager.html',
                            total_interns=total_interns,
                            active_interns=active_interns,
                            total_supervisors=total_supervisors,
                            recent_reports=recent_reports)
    
    elif user.role == 'admin':
        # Get all stats
        total_users = User.query.count()
        active_users = User.query.filter_by(status='active').count()
        total_reports = Report.query.count()
        pending_reports = Report.query.filter_by(status='submitted').count()
        
        return render_template('dashboard/admin.html',
                            total_users=total_users,
                            active_users=active_users,
                            total_reports=total_reports,
                            pending_reports=pending_reports)
    
    return redirect(url_for('login'))

# Attendance Routes
@app.route('/attendance', methods=['GET', 'POST'])
@login_required
@role_required(['intern'])
def attendance():
    user = User.query.get(session['user_id'])
    today = date.today()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'sign_in':
            # Check if already signed in today
            existing_record = Attendance.query.filter_by(
                user_id=user.id,
                date=today
            ).first()
            
            if existing_record:
                flash('You have already signed in today', 'warning')
            else:
                new_attendance = Attendance(
                    user_id=user.id,
                    date=today,
                    time_in=datetime.now().time(),
                    status='present'
                )
                db.session.add(new_attendance)
                db.session.commit()
                flash('Successfully signed in', 'success')
        
        elif action == 'sign_out':
            # Find today's record
            record = Attendance.query.filter_by(
                user_id=user.id,
                date=today
            ).first()
            
            if not record:
                flash('You need to sign in first', 'danger')
            elif record.time_out:
                flash('You have already signed out today', 'warning')
            else:
                record.time_out = datetime.now().time()
                db.session.commit()
                flash('Successfully signed out', 'success')
    
    # Get today's status
    today_record = Attendance.query.filter_by(
        user_id=user.id,
        date=today
    ).first()
    
    # Get attendance history
    attendance_history = Attendance.query.filter_by(
        user_id=user.id
    ).order_by(Attendance.date.desc()).limit(10).all()
    
    # Calculate attendance percentage
    total_days = Attendance.query.filter_by(user_id=user.id).count()
    present_days = Attendance.query.filter_by(user_id=user.id, status='present').count()
    attendance_percentage = round((present_days / total_days) * 100, 2) if total_days > 0 else 0
    
    return render_template('attendance/index.html',
                         today_record=today_record,
                         attendance_history=attendance_history,
                         attendance_percentage=attendance_percentage)

@app.route('/attendance/records')
@login_required
@role_required(['supervisor', 'manager', 'admin'])
def attendance_records():
    user = User.query.get(session['user_id'])
    
    if user.role == 'supervisor':
        # Get attendance records for interns supervised by this supervisor
        records = db.session.query(Attendance).join(User).filter(
            User.supervisor_id == user.id
        ).order_by(Attendance.date.desc()).all()
    else:
        # Admin or manager can see all records
        records = Attendance.query.order_by(Attendance.date.desc()).all()
    
    return render_template('attendance/records.html', records=records)

# Reports Routes
@app.route('/reports', methods=['GET', 'POST'])
@login_required
@role_required(['intern'])
def reports():
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        title = request.form.get('title')
        report_type = request.form.get('report_type')
        content = request.form.get('content')
        file = request.files.get('file')
        
        if not title or not report_type:
            flash('Title and report type are required', 'danger')
            return redirect(url_for('reports'))
        
        file_path = None
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{user.id}_{datetime.now().timestamp()}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
        
        new_report = Report(
            user_id=user.id,
            supervisor_id=user.supervisor_id,
            title=title,
            report_type=report_type,
            content=content,
            file_path=file_path,
            status='submitted',
            submission_date=datetime.now()
        )
        
        db.session.add(new_report)
        db.session.commit()
        
        flash('Report submitted successfully', 'success')
        return redirect(url_for('reports'))
    
    # Get user's reports
    user_reports = Report.query.filter_by(user_id=user.id).order_by(Report.submission_date.desc()).all()
    
    return render_template('reports/index.html', reports=user_reports)

@app.route('/reports/view/<int:report_id>')
@login_required
def view_report(report_id):
    report = Report.query.get_or_404(report_id)
    user = User.query.get(session['user_id'])
    
    # Check permissions
    if user.role == 'intern' and report.user_id != user.id:
        flash('You do not have permission to view this report', 'danger')
        return redirect(url_for('dashboard'))
    
    if user.role == 'supervisor' and report.supervisor_id != user.id:
        flash('You do not have permission to view this report', 'danger')
        return redirect(url_for('dashboard'))
    
    # For managers, they can view all reports
    return render_template('reports/view.html', report=report)
@app.route('/reports/review', methods=['GET', 'POST'])
@login_required
@role_required(['supervisor', 'manager'])
def review_reports():
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        report_id = request.form.get('report_id')
        feedback = request.form.get('feedback')
        status = request.form.get('status')
        
        report = Report.query.get(report_id)
        
        # Check permissions
        if user.role == 'supervisor' and report.supervisor_id != user.id:
            flash('You do not have permission to review this report', 'danger')
            return redirect(url_for('review_reports'))
        
        if report:
            report.feedback = feedback
            report.status = status
            db.session.commit()
            flash('Report reviewed successfully', 'success')
        else:
            flash('Invalid report', 'danger')
        
        return redirect(url_for('review_reports'))
    
    # Get reports based on role
    if user.role == 'supervisor':
        pending_reports = Report.query.filter_by(
            supervisor_id=user.id,
            status='submitted'
        ).order_by(Report.submission_date.desc()).all()
        
        reviewed_reports = Report.query.filter(
            Report.supervisor_id == user.id,
            Report.status.in_(['approved', 'declined'])
        ).order_by(Report.submission_date.desc()).limit(10).all()
    else:  # manager
        pending_reports = Report.query.filter_by(
            status='submitted'
        ).order_by(Report.submission_date.desc()).all()
        
        reviewed_reports = Report.query.filter(
            Report.status.in_(['approved', 'declined'])
        ).order_by(Report.submission_date.desc()).limit(10).all()
    
    return render_template('reports/review.html',
                         pending_reports=pending_reports,
                         reviewed_reports=reviewed_reports)
# Communication Routes
@app.route('/communication')
@login_required
def communication():
    user = User.query.get(session['user_id'])
    
    # Get unread message count
    unread_count = Message.query.filter_by(
        recipient_id=user.id,
        read_at=None
    ).count()
    
    # Get recent messages
    received_messages = Message.query.filter_by(
        recipient_id=user.id
    ).order_by(Message.sent_at.desc()).limit(5).all()
    
    sent_messages = Message.query.filter_by(
        sender_id=user.id
    ).order_by(Message.sent_at.desc()).limit(5).all()
    
    # Get users for dropdown based on role
    if user.role == 'intern':
        recipients = User.query.filter_by(supervisor_id=user.supervisor_id).all()
    elif user.role == 'supervisor':
        recipients = User.query.filter(
            (User.supervisor_id == user.id) | (User.role == 'manager') | (User.role == 'admin')
        ).all()
    elif user.role == 'manager':
        recipients = User.query.filter(
            (User.role == 'supervisor') | (User.role == 'admin')
        ).all()
    else:  # admin
        recipients = User.query.all()
    
    return render_template('communication/index.html',
                         unread_count=unread_count,
                         received_messages=received_messages,
                         sent_messages=sent_messages,
                         recipients=recipients)

@app.route('/communication/messages')
@login_required
def messages():
    user = User.query.get(session['user_id'])
    message_type = request.args.get('type', 'inbox')
    
    if message_type == 'inbox':
        messages = Message.query.filter_by(recipient_id=user.id).order_by(Message.sent_at.desc()).all()
    else:
        messages = Message.query.filter_by(sender_id=user.id).order_by(Message.sent_at.desc()).all()
    
    return render_template('communication/messages.html',
                         messages=messages,
                         message_type=message_type)

@app.route('/communication/compose', methods=['GET', 'POST'])
@login_required
def compose_message():
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id')
        subject = request.form.get('subject')
        body = request.form.get('body')
        is_urgent = request.form.get('is_urgent') == 'on'
        
        if not recipient_id or not subject or not body:
            flash('All fields are required', 'danger')
            return redirect(url_for('compose_message'))
        
        recipient = User.query.get(recipient_id)
        if not recipient:
            flash('Invalid recipient', 'danger')
            return redirect(url_for('compose_message'))
        
        new_message = Message(
            sender_id=session['user_id'],
            recipient_id=recipient_id,
            subject=subject,
            body=body,
            is_urgent=is_urgent,
            sent_at=datetime.now()
        )
        
        db.session.add(new_message)
        db.session.commit()
        
        flash('Message sent successfully', 'success')
        return redirect(url_for('messages', type='sent'))
    
    # Get recipients based on user role
    user = User.query.get(session['user_id'])
    
    if user.role == 'intern':
        recipients = User.query.filter_by(supervisor_id=user.supervisor_id).all()
    elif user.role == 'supervisor':
        recipients = User.query.filter(
            (User.supervisor_id == user.id) | (User.role == 'manager') | (User.role == 'admin')
        ).all()
    elif user.role == 'manager':
        recipients = User.query.filter(
            (User.role == 'supervisor') | (User.role == 'admin')
        ).all()
    else:  # admin
        recipients = User.query.all()
    
    return render_template('communication/compose.html', recipients=recipients)

@app.route('/communication/messages/<int:message_id>')
@login_required
def view_message(message_id):
    message = Message.query.get_or_404(message_id)
    user = User.query.get(session['user_id'])
    
    # Check if user is recipient or sender
    if message.recipient_id != user.id and message.sender_id != user.id:
        flash('You do not have permission to view this message', 'danger')
        return redirect(url_for('messages'))
    
    # Mark as read if recipient
    if message.recipient_id == user.id and not message.read_at:
        message.read_at = datetime.now()
        db.session.commit()
    
    return render_template('communication/view_message.html', message=message)

# Tasks Routes
from datetime import datetime, date  # This import is already at the top of your file

@app.route('/tasks')
@login_required
def tasks():
    user = User.query.get(session['user_id'])
    
    if user.role == 'intern':
        tasks = Task.query.filter_by(intern_id=user.id).order_by(Task.due_date.asc()).all()
        return render_template('tasks/intern.html', tasks=tasks, date=date)  # Add date here
    elif user.role == 'supervisor':
        tasks = Task.query.filter_by(supervisor_id=user.id).order_by(Task.due_date.asc()).all()
        interns = User.query.filter_by(supervisor_id=user.id).all()
        return render_template('tasks/supervisor.html', tasks=tasks, interns=interns)
    else:
        flash('You do not have access to tasks', 'warning')
        return redirect(url_for('dashboard'))

@app.route('/tasks/update/<int:task_id>', methods=['POST'])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    user = User.query.get(session['user_id'])
    
    if user.role == 'intern' and task.intern_id != user.id:
        flash('You do not have permission to update this task', 'danger')
        return redirect(url_for('tasks'))
    
    if user.role == 'supervisor' and task.supervisor_id != user.id:
        flash('You do not have permission to update this task', 'danger')
        return redirect(url_for('tasks'))
    
    status = request.form.get('status')
    completion_notes = request.form.get('completion_notes')
    
    if status:
        task.status = status
    
    if completion_notes is not None:
        task.completion_notes = completion_notes
    
    db.session.commit()
    
    flash('Task updated successfully', 'success')
    return redirect(url_for('tasks'))

# Admin Routes
@app.route('/admin/users')
@login_required
@role_required(['admin'])
def admin_users():
    users = User.query.order_by(User.role, User.last_name).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.first_name = request.form.get('first_name', user.first_name)
        user.last_name = request.form.get('last_name', user.last_name)
        user.email = request.form.get('email', user.email)
        user.role = request.form.get('role', user.role)
        user.department = request.form.get('department', user.department)
        user.status = request.form.get('status', user.status)
        
        supervisor_id = request.form.get('supervisor_id')
        if supervisor_id and supervisor_id != 'None':
            user.supervisor_id = int(supervisor_id)
        else:
            user.supervisor_id = None
        
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('admin_users'))
    
    supervisors = User.query.filter_by(role='supervisor').all()
    return render_template('admin/edit_user.html', user=user, supervisors=supervisors)

@app.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def create_user():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        department = request.form.get('department')
        supervisor_id = request.form.get('supervisor_id')
        
        if not first_name or not last_name or not email or not role:
            flash('All required fields must be filled', 'danger')
            return redirect(url_for('create_user'))
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already in use', 'danger')
            return redirect(url_for('create_user'))
        
        hashed_password = generate_password_hash(password or 'password123', method='pbkdf2:sha256')
        
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password,
            role=role,
            department=department,
            supervisor_id=int(supervisor_id) if supervisor_id and supervisor_id != 'None' else None,
            status='active'
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('User created successfully', 'success')
        return redirect(url_for('admin_users'))
    
    supervisors = User.query.filter_by(role='supervisor').all()
    return render_template('admin/create_user.html', supervisors=supervisors)

# API Routes for AJAX
@app.route('/api/attendance/stats')
@login_required
def attendance_stats():
    user = User.query.get(session['user_id'])
    
    if user.role == 'intern':
        total_days = Attendance.query.filter_by(user_id=user.id).count()
        present_days = Attendance.query.filter_by(user_id=user.id, status='present').count()
        late_days = Attendance.query.filter_by(user_id=user.id, status='late').count()
        absent_days = Attendance.query.filter_by(user_id=user.id, status='absent').count()
        
        return jsonify({
            'total_days': total_days,
            'present_days': present_days,
            'late_days': late_days,
            'absent_days': absent_days,
            'attendance_percentage': round((present_days / total_days) * 100, 2) if total_days > 0 else 0
        })
    
    elif user.role == 'supervisor':
        interns = User.query.filter_by(supervisor_id=user.id).all()
        data = []
        
        for intern in interns:
            total_days = Attendance.query.filter_by(user_id=intern.id).count()
            present_days = Attendance.query.filter_by(user_id=intern.id, status='present').count()
            
            data.append({
                'intern_name': f"{intern.first_name} {intern.last_name}",
                'attendance_percentage': round((present_days / total_days) * 100, 2) if total_days > 0 else 0
            })
        
        return jsonify(data)
    
    return jsonify({'error': 'Invalid request'}), 400

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

# Report Editing and Downloading
@app.route('/reports/edit/<int:report_id>', methods=['GET', 'POST'])
@login_required
@role_required(['intern'])
def edit_report(report_id):
    report = Report.query.get_or_404(report_id)
    user = User.query.get(session['user_id'])
    
    if report.user_id != user.id or report.status != 'submitted':
        flash('You cannot edit this report', 'danger')
        return redirect(url_for('reports'))
    
    if request.method == 'POST':
        report.title = request.form.get('title', report.title)
        report.report_type = request.form.get('report_type', report.report_type)
        report.content = request.form.get('content', report.content)
        
        # Handle file attachment
        if request.form.get('remove_file') == '1' and report.file_path:
            if os.path.exists(report.file_path):
                os.remove(report.file_path)
            report.file_path = None
        
        file = request.files.get('file')
        if file and allowed_file(file.filename):
            # Delete old file if exists
            if report.file_path and os.path.exists(report.file_path):
                os.remove(report.file_path)
            
            filename = secure_filename(f"{user.id}_{datetime.now().timestamp()}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            report.file_path = file_path
        
        db.session.commit()
        flash('Report updated successfully', 'success')
        return redirect(url_for('view_report', report_id=report.id))
    
    return render_template('reports/edit.html', report=report)

@app.route('/reports/download/<int:report_id>')
@login_required
def download_report(report_id):
    report = Report.query.get_or_404(report_id)
    user = User.query.get(session['user_id'])
    
    # Check permissions
    if report.user_id != user.id and report.supervisor_id != user.id and user.role not in ['manager', 'admin']:
        flash('You do not have permission to download this report', 'danger')
        return redirect(url_for('dashboard'))
    
    if not report.file_path or not os.path.exists(report.file_path):
        flash('File not found', 'danger')
        return redirect(url_for('view_report', report_id=report.id))
    
    return send_file(report.file_path, as_attachment=True)

# Task Creation
@app.route('/tasks/create', methods=['POST'])
@login_required
@role_required(['supervisor'])
def create_task():
    title = request.form.get('title')
    description = request.form.get('description')
    intern_id = request.form.get('intern_id')
    due_date = request.form.get('due_date')
    
    if not title or not intern_id:
        flash('Title and intern are required', 'danger')
        return redirect(url_for('tasks'))
    
    try:
        due_date = datetime.strptime(due_date, '%Y-%m-%d') if due_date else None
    except ValueError:
        due_date = None
    
    new_task = Task(
        supervisor_id=session['user_id'],
        intern_id=intern_id,
        title=title,
        description=description,
        due_date=due_date,
        assigned_date=datetime.now(),
        status='pending'
    )
    
    db.session.add(new_task)
    db.session.commit()
    
    flash('Task assigned successfully', 'success')
    return redirect(url_for('tasks'))

# System Settings
@app.route('/admin/system-settings', methods=['POST'])
@login_required
@role_required(['admin'])
def update_system_settings():
    org_name = request.form.get('org_name')
    default_role = request.form.get('default_role')
    registration_open = request.form.get('registration_open') == 'on'
    
    # Update config - in a real app you would save these to database
    app.config['ORGANIZATION_NAME'] = org_name
    app.config['DEFAULT_ROLE'] = default_role
    app.config['REGISTRATION_OPEN'] = registration_open
    
    flash('System settings updated successfully', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
@app.route('/admin/users/<int:user_id>/change-password', methods=['POST'])
@login_required
@role_required(['admin'])
def change_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not new_password or not confirm_password:
        flash('Please fill in all password fields.', 'danger')
        return redirect(url_for('edit_user', user_id=user_id))
    
    if new_password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('edit_user', user_id=user_id))
    
    hashed_password = generate_password_hash(new_password, method='sha256')
    user.password = hashed_password
    db.session.commit()
    
    flash(f'Password for {user.first_name} {user.last_name} has been updated.', 'success')
    return redirect(url_for('edit_user', user_id=user_id))
@app.route('/attendance/update/<int:record_id>', methods=['POST'])
@login_required
@role_required(['supervisor', 'admin'])
def update_attendance(record_id):
    record = Attendance.query.get_or_404(record_id)
    record.status = request.form.get('status', record.status)
    record.notes = request.form.get('notes', record.notes)
    db.session.commit()
    
    flash('Attendance record updated successfully', 'success')
    return redirect(url_for('attendance_records'))


