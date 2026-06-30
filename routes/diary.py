import logging
import calendar
from datetime import date, timedelta
from collections import defaultdict

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user

from models.database import db, DiaryEntry

logger = logging.getLogger(__name__)

diary_bp = Blueprint("diary", __name__)


def _decrypt_title(entry):
    try:
        return current_app.encryption.decrypt(entry.title_encrypted)
    except Exception:
        return "***"


@diary_bp.route("/")
@login_required
def index():
    view_mode = request.args.get("view", "calendar")

    if view_mode == "list":
        page = request.args.get("page", 1, type=int)
        per_page = 15
        query = DiaryEntry.query.filter_by(user_id=current_user.id)
        pagination = query.order_by(DiaryEntry.diary_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        entries = []
        for entry in pagination.items:
            entries.append({
                "id": entry.id,
                "title": _decrypt_title(entry),
                "diary_date": entry.diary_date.isoformat() if entry.diary_date else entry.created_at.date().isoformat(),
                "word_count": entry.word_count,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
            })
        return render_template("index.html", view_mode="list", entries=entries, pagination=pagination)

    # Calendar view
    today = date.today()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1

    selected_date = None
    selected_date_str = request.args.get("date", "").strip()
    if selected_date_str:
        try:
            selected_date = date.fromisoformat(selected_date_str)
        except ValueError:
            pass

    cal = calendar.Calendar(firstweekday=6)  # 周日开始
    month_days = cal.monthdatescalendar(year, month)

    # Fetch all entries for this month
    first_day = month_days[0][0]
    last_day = month_days[-1][-1]
    month_entries = DiaryEntry.query.filter(
        DiaryEntry.user_id == current_user.id,
        DiaryEntry.diary_date >= first_day,
        DiaryEntry.diary_date <= last_day,
    ).order_by(DiaryEntry.diary_date.asc()).all()

    # Group by date -> list of (id, title)
    date_entries = defaultdict(list)
    for entry in month_entries:
        date_entries[entry.diary_date].append((entry.id, _decrypt_title(entry), entry.word_count))

    # Entries for selected date
    day_entries = []
    if selected_date and selected_date in date_entries:
        day_entries = date_entries[selected_date]

    # Prev / next month links
    prev_date = date(year, month, 1) - timedelta(days=1)
    next_date = date(year, month, 1) + timedelta(days=32)
    next_date = next_date.replace(day=1)

    calendar_data = {
        "year": year,
        "month": month,
        "month_name": f"{year}年{month}月",
        "weeks": month_days,
        "prev_year": prev_date.year,
        "prev_month": prev_date.month,
        "next_year": next_date.year,
        "next_month": next_date.month,
        "date_entries": {d.isoformat(): len(v) for d, v in date_entries.items()},
        "today": today,
    }

    return render_template(
        "index.html",
        view_mode="calendar",
        calendar_data=calendar_data,
        selected_date=selected_date,
        day_entries=day_entries,
    )


@diary_bp.route("/write", methods=["GET", "POST"])
@login_required
def write():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        diary_date_str = request.form.get("diary_date", "").strip()

        if not title:
            flash("请输入日记标题。", "error")
            return render_template("write.html", content=content, diary_date=diary_date_str), 400
        if not content:
            flash("请输入日记内容。", "error")
            return render_template("write.html", title=title, diary_date=diary_date_str), 400
        if len(title) > 200:
            flash("标题不能超过200个字符。", "error")
            return render_template("write.html", content=content, diary_date=diary_date_str), 400

        diary_date = date.today()
        if diary_date_str:
            try:
                diary_date = date.fromisoformat(diary_date_str)
            except ValueError:
                flash("日期格式不正确。", "error")
                return render_template("write.html", title=title, content=content, diary_date=diary_date_str), 400

        enc = current_app.encryption
        entry = DiaryEntry(
            user_id=current_user.id,
            title_encrypted=enc.encrypt(title),
            content_encrypted=enc.encrypt(content),
            diary_date=diary_date,
            word_count=len(content),
        )
        db.session.add(entry)
        db.session.commit()
        logger.info("User '%s' created diary entry #%d", current_user.username, entry.id)
        flash("日记保存成功！", "success")
        return redirect(url_for("diary.view", entry_id=entry.id))

    diary_date_str = request.args.get("date", date.today().isoformat())
    try:
        date.fromisoformat(diary_date_str)
    except ValueError:
        diary_date_str = date.today().isoformat()
    return render_template("write.html", diary_date=diary_date_str)


@diary_bp.route("/auto-save", methods=["POST"])
@login_required
def auto_save():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "")
    diary_date_str = request.form.get("diary_date", "").strip()
    entry_id = request.form.get("entry_id", type=int)

    if not title and not content:
        return jsonify({"ok": False, "msg": "empty"})

    diary_date = date.today()
    if diary_date_str:
        try:
            diary_date = date.fromisoformat(diary_date_str)
        except ValueError:
            pass

    enc = current_app.encryption

    if entry_id:
        entry = DiaryEntry.query.filter_by(id=entry_id, user_id=current_user.id).first()
        if not entry:
            return jsonify({"ok": False, "msg": "not found"})
        if title:
            entry.title_encrypted = enc.encrypt(title)
        entry.content_encrypted = enc.encrypt(content)
        entry.diary_date = diary_date
        entry.word_count = len(content)
        db.session.commit()
        return jsonify({"ok": True, "entry_id": entry.id, "updated_at": entry.updated_at.isoformat()})
    else:
        if not title:
            title = "无标题"
        entry = DiaryEntry(
            user_id=current_user.id,
            title_encrypted=enc.encrypt(title),
            content_encrypted=enc.encrypt(content),
            diary_date=diary_date,
            word_count=len(content),
        )
        db.session.add(entry)
        db.session.commit()
        logger.info("User '%s' auto-saved new diary entry #%d", current_user.username, entry.id)
        return jsonify({"ok": True, "entry_id": entry.id, "updated_at": entry.updated_at.isoformat()})


@diary_bp.route("/entry/<int:entry_id>")
@login_required
def view(entry_id):
    entry = DiaryEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    enc = current_app.encryption
    return render_template(
        "view.html",
        entry={
            "id": entry.id,
            "title": enc.decrypt(entry.title_encrypted),
            "content": enc.decrypt(entry.content_encrypted),
            "diary_date": entry.diary_date.isoformat() if entry.diary_date else entry.created_at.date().isoformat(),
            "word_count": entry.word_count,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
        },
    )


@diary_bp.route("/entry/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit(entry_id):
    entry = DiaryEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    enc = current_app.encryption

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        diary_date_str = request.form.get("diary_date", "").strip()

        if not title:
            flash("请输入日记标题。", "error")
            return render_template("edit.html", entry={"id": entry_id, "title": title, "content": content, "diary_date": diary_date_str}), 400
        if not content:
            flash("请输入日记内容。", "error")
            return render_template("edit.html", entry={"id": entry_id, "title": title, "content": content, "diary_date": diary_date_str}), 400
        if len(title) > 200:
            flash("标题不能超过200个字符。", "error")
            return render_template("edit.html", entry={"id": entry_id, "title": title, "content": content, "diary_date": diary_date_str}), 400

        diary_date = date.today()
        if diary_date_str:
            try:
                diary_date = date.fromisoformat(diary_date_str)
            except ValueError:
                flash("日期格式不正确。", "error")
                return render_template("edit.html", entry={"id": entry_id, "title": title, "content": content, "diary_date": diary_date_str}), 400

        entry.title_encrypted = enc.encrypt(title)
        entry.content_encrypted = enc.encrypt(content)
        entry.diary_date = diary_date
        entry.word_count = len(content)
        db.session.commit()
        logger.info("User '%s' updated diary entry #%d", current_user.username, entry.id)
        flash("日记更新成功！", "success")
        return redirect(url_for("diary.view", entry_id=entry.id))

    return render_template(
        "edit.html",
        entry={
            "id": entry.id,
            "title": enc.decrypt(entry.title_encrypted),
            "content": enc.decrypt(entry.content_encrypted),
            "diary_date": entry.diary_date.isoformat() if entry.diary_date else date.today().isoformat(),
        },
    )


@diary_bp.route("/entry/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete(entry_id):
    entry = DiaryEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    logger.info("User '%s' deleting diary entry #%d", current_user.username, entry.id)
    db.session.delete(entry)
    db.session.commit()
    flash("日记已删除。", "success")
    return redirect(url_for("diary.index"))


@diary_bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        flash("请输入至少2个字符的搜索词。", "error")
        return redirect(url_for("diary.index"))

    enc = current_app.encryption
    all_entries = DiaryEntry.query.filter_by(user_id=current_user.id).order_by(
        DiaryEntry.created_at.desc()
    ).all()

    results = []
    for entry in all_entries:
        try:
            title = enc.decrypt(entry.title_encrypted)
            content = enc.decrypt(entry.content_encrypted)
        except Exception:
            continue
        if q.lower() in title.lower() or q.lower() in content.lower():
            results.append({
                "id": entry.id,
                "title": title,
                "diary_date": entry.diary_date.isoformat() if entry.diary_date else entry.created_at.date().isoformat(),
                "snippet": content[:120] + ("..." if len(content) > 120 else ""),
                "created_at": entry.created_at,
            })

    return render_template("search.html", keyword=q, results=results)
