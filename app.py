import os
import logging
from datetime import datetime, timezone

from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import Config, DevelopmentConfig, ProductionConfig
from models.database import db, init_db, User
from utils.encryption import DiaryEncryption
from utils.backup import backup_database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_class=None):
    app = Flask(__name__)

    env = os.environ.get("DIARY_ENV", "development")
    if config_class is None:
        config_class = ProductionConfig if env == "production" else DevelopmentConfig
    app.config.from_object(config_class)

    init_db(app)
    app.encryption = DiaryEncryption(app.config["ENCRYPTION_KEY"])

    csrf = CSRFProtect(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "请先登录后再访问此页面。"
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from routes.auth import auth_bp
    from routes.diary import diary_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(diary_bp)

    @app.errorhandler(400)
    def csrf_error(e):
        from flask import flash
        flash("请求无效，请刷新页面后重试。", "error")
        return redirect(request.referrer or url_for("auth.login"))

    @app.before_request
    def check_blocked():
        if request.endpoint in ("auth.login", "auth.logout", "static"):
            return
        if not current_user.is_authenticated:
            return
        if current_user.locked_until and current_user.locked_until > datetime.now(timezone.utc):
            from flask_login import logout_user
            logout_user()
            from flask import flash
            flash("账户已被临时锁定，请稍后再试。", "error")
            return redirect(url_for("auth.login"))

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error("Internal server error: %s", e, exc_info=True)
        db.session.rollback()
        return render_template("500.html"), 500

    @app.context_processor
    def inject_now():
        return {"now": datetime.now(timezone.utc)}

    db_path = app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        db_path = os.path.join(app.config["BASE_DIR"], db_path)

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: backup_database(
            db_path,
            app.config["BACKUP_DIR"],
            app.config["BACKUP_KEEP_COUNT"],
        ),
        trigger=IntervalTrigger(hours=app.config["BACKUP_INTERVAL_HOURS"]),
        id="db_backup",
        name="Database backup",
        replace_existing=True,
    )
    scheduler.start()

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

    import atexit
    @atexit.register
    def shutdown_scheduler():
        if scheduler.running:
            scheduler.shutdown(wait=False)

    return app


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=app.config.get("DEBUG", False))
