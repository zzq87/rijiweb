import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from models.database import db, User

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("diary.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("请输入用户名和密码。", "error")
            return render_template("login.html"), 400

        user = User.query.filter_by(username=username).first()

        if user and user.is_locked():
            remaining = (user.locked_until - datetime.now(timezone.utc)).seconds // 60 + 1
            flash(f"账户已锁定，请在 {remaining} 分钟后重试。", "error")
            return render_template("login.html"), 429

        if user and user.check_password(password):
            user.login_attempts = 0
            user.locked_until = None
            db.session.commit()
            login_user(user, remember=request.form.get("remember") == "on")
            logger.info("User '%s' logged in successfully", username)
            flash("登录成功！", "success")
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("diary.index"))

        if user:
            user.login_attempts += 1
            if user.login_attempts >= current_app.config["LOGIN_ATTEMPT_LIMIT"]:
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    seconds=current_app.config["LOGIN_ATTEMPT_WINDOW"]
                )
                logger.warning("User '%s' locked due to too many login attempts", username)
                flash("登录失败次数过多，账户已锁定10分钟。", "error")
            else:
                flash("用户名或密码错误。", "error")
            db.session.commit()
        else:
            flash("用户名或密码错误。", "error")

        return render_template("login.html"), 401

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("diary.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        errors = []
        if len(username) < 2 or len(username) > 50:
            errors.append("用户名长度需在2-50个字符之间。")
        if not username.replace("_", "").replace("-", "").isalnum():
            errors.append("用户名只能包含字母、数字、下划线和连字符。")
        if len(password) < 6:
            errors.append("密码长度不能少于6个字符。")
        if password != confirm:
            errors.append("两次输入的密码不一致。")
        if User.query.filter_by(username=username).first():
            errors.append("该用户名已被注册。")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", username=username), 400

        user = User(username=username)
        user.set_password(password)

        if not User.query.filter_by(is_admin=True).first():
            user.is_admin = True

        db.session.add(user)
        db.session.commit()
        logger.info("New user registered: '%s'", username)
        flash("注册成功，请登录。", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logger.info("User '%s' logged out", current_user.username)
    logout_user()
    flash("已安全退出。", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password", "")
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm", "")

        if not current_user.check_password(old_password):
            flash("当前密码不正确。", "error")
            return render_template("change_password.html"), 400
        if len(new_password) < 6:
            flash("新密码长度不能少于6个字符。", "error")
            return render_template("change_password.html"), 400
        if new_password != confirm:
            flash("两次输入的新密码不一致。", "error")
            return render_template("change_password.html"), 400

        current_user.set_password(new_password)
        db.session.commit()
        logger.info("User '%s' changed password", current_user.username)
        flash("密码修改成功。", "success")
        return redirect(url_for("diary.index"))

    return render_template("change_password.html")
