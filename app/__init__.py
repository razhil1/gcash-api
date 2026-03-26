import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from app.extensions import db, jwt, limiter

def create_app(config_name=None):
    """Application factory."""
    # Use /tmp for instance path on Vercel to avoid Read-only filesystem errors
    instance_path = '/tmp' if os.environ.get('VERCEL') == '1' else None
    
    app = Flask(__name__, static_folder=None, instance_path=instance_path)

    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    from app.config import config
    app_config = config.get(config_name, config['default'])
    app.config.from_object(app_config)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    CORS(app, origins='*')

    # JWT config
    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return str(user)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        from app.models.user import User
        identity = jwt_data["sub"]
        return User.query.get(int(identity))

    # JWT Error Handlers for debugging 422s
    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        app.logger.error(f"Invalid Token: {error_string}")
        return jsonify({
            'error': 'Invalid token',
            'msg': error_string
        }), 401

    @jwt.unauthorized_loader
    def unauthorized_token_callback(error_string):
        app.logger.error(f"Unauthorized: {error_string}")
        return jsonify({
            'error': 'Unauthorized',
            'msg': error_string
        }), 401

    # Ensure storage folders exist (Safe for Vercel if pointed to /tmp)
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'qr_codes'), exist_ok=True)
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'proofs'), exist_ok=True)
    except OSError as e:
        if os.environ.get('VERCEL') == '1':
            print(f"⚠️ Warning: Could not create directories in production: {e}")
        else:
            raise

    # Register API blueprints
    from app.routes.auth import auth_bp
    from app.routes.payments import payments_bp
    from app.routes.uploads import uploads_bp
    from app.routes.qr_wallets import qr_wallets_bp
    from app.routes.transactions import transactions_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    app.register_blueprint(uploads_bp, url_prefix='/api/uploads')
    app.register_blueprint(qr_wallets_bp, url_prefix='/api/qr-wallets')
    app.register_blueprint(transactions_bp, url_prefix='/api/transactions')

    # Serve uploaded files
    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Serve frontend files
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')

    @app.route('/')
    def serve_index():
        return send_from_directory(frontend_dir, 'index.html')

    @app.route('/dashboard')
    @app.route('/dashboard/')
    def serve_dashboard():
        return send_from_directory(frontend_dir, 'dashboard.html')

    @app.route('/pay/<slug>')
    def serve_payment(slug):
        return send_from_directory(frontend_dir, 'payment.html')

    @app.route('/login')
    def serve_login():
        return send_from_directory(frontend_dir, 'login.html')

    @app.route('/assets/<path:filename>')
    def serve_assets(filename):
        return send_from_directory(os.path.join(frontend_dir, 'assets'), filename)

    # Create database tables
    with app.app_context():
        from app import models  # noqa
        db.create_all()

        # Create default admin user if none exists
        from app.models.user import User
        if not User.query.filter_by(role='admin').first():
            admin = User(
                email='admin@gcashpay.com',
                name='Admin',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('✅ Default admin created: admin@gcashpay.com / admin123')

    return app
