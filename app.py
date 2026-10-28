from flask import Flask, render_template, jsonify
from sqlalchemy import inspect, text
from flask_login import LoginManager
from config import Config
from database import db
from models import User
from utils.blockchain import ensure_genesis_block

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({'error': 'Unauthorized. Please log in.'}), 401

    # Register Blueprints
    from routes import (
        auth_bp, public_bp, donors_bp, donations_bp,
        inventory_bp, beneficiaries_bp, distributions_bp,
        ledger_bp, reports_bp, audit_bp, blockchain_bp, volunteers_bp
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(donors_bp)
    app.register_blueprint(donations_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(beneficiaries_bp)
    app.register_blueprint(distributions_bp)
    app.register_blueprint(ledger_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(blockchain_bp)
    app.register_blueprint(volunteers_bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/gpay')
    def gpay_page():
        return render_template('gpay.html')

    # Global Error Handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Resource or endpoint not found'}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    # Ensure DB tables & genesis block exist
    with app.app_context():
        db.create_all()
        donation_columns = {column['name'] for column in inspect(db.engine).get_columns('donations')}
        with db.engine.begin() as connection:
            if 'product_photo' not in donation_columns:
                connection.execute(text('ALTER TABLE donations ADD COLUMN product_photo VARCHAR(255)'))
            if 'payment_screenshot' not in donation_columns:
                connection.execute(text('ALTER TABLE donations ADD COLUMN payment_screenshot VARCHAR(255)'))
            if 'evidence_status' not in donation_columns:
                connection.execute(text("ALTER TABLE donations ADD COLUMN evidence_status VARCHAR(30) NOT NULL DEFAULT 'Pending Review'"))
            if 'evidence_reviewed_by' not in donation_columns:
                connection.execute(text('ALTER TABLE donations ADD COLUMN evidence_reviewed_by VARCHAR(120)'))
            if 'item_name' not in donation_columns:
                connection.execute(text('ALTER TABLE donations ADD COLUMN item_name VARCHAR(120)'))
        # Ensure distributions.amount column exists
        try:
            distribution_columns = {column['name'] for column in inspect(db.engine).get_columns('distributions')}
        except Exception:
            distribution_columns = set()
        with db.engine.begin() as connection:
            if 'amount' not in distribution_columns:
                connection.execute(text('ALTER TABLE distributions ADD COLUMN amount FLOAT DEFAULT 0.0'))
        ensure_genesis_block()
        seed_users = [
            {'name': 'Joshna', 'email': 'admin@ngo.org', 'role': 'admin', 'phone': '+91 98765 43210'},
            {'name': 'Harish Kumar', 'email': 'staff@ngo.org', 'role': 'staff', 'phone': '+91 98765 43211'},
            {'name': 'Dia Ravi', 'email': 'donor@example.com', 'role': 'donor', 'phone': '+91 98765 43212'},
            {'name': 'Meena Devi', 'email': 'beneficiary@example.com', 'role': 'beneficiary', 'phone': '+91 98765 43213'},
            {'name': 'Kavya Raj', 'email': 'auditor@ngo.org', 'role': 'auditor', 'phone': '+91 98765 43214'},
        ]
        from models import Donor
        for udata in seed_users:
            u = User.query.filter_by(email=udata['email']).first()
            if not u:
                u = User(name=udata['name'], email=udata['email'], role=udata['role'], phone=udata['phone'])
                u.set_password('password123')
                db.session.add(u)
                db.session.commit()
            if u.role == 'donor':
                d = Donor.query.filter_by(email=u.email).first()
                if not d:
                    d = Donor(user_id=u.id, name=u.name, email=u.email, phone=u.phone, address='Anna Nagar, Chennai, Tamil Nadu', preferred_causes='Emergency Relief & Education')
                    db.session.add(d)
                    db.session.commit()
                elif not d.address:
                    d.address = 'Anna Nagar, Chennai, Tamil Nadu'
                    db.session.commit()


    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
