"""
AIoT Smart Waste Management System
====================================
Flask Backend Server
Handles:
  - Bin status updates from ESP32
  - Alerts (level/weight threshold exceeded)
  - Admin/Worker/User API endpoints
  - Mobile app REST API
"""

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# ─── Database Config ─────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'waste.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "aiot-waste-secret-key"

db = SQLAlchemy(app)

# ─── Models ──────────────────────────────────────────────────────────────────
class Bin(db.Model):
    __tablename__ = "bin_tbl"
    bin_id   = db.Column(db.String(50), primary_key=True)
    status   = db.Column(db.String(50), default="Empty")

class Account(db.Model):
    __tablename__ = "account_tbl"
    id        = db.Column(db.String(50), primary_key=True)
    bin_id    = db.Column(db.String(50), db.ForeignKey("bin_tbl.bin_id"))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level     = db.Column(db.Integer)
    weight    = db.Column(db.Float)

class User(db.Model):
    __tablename__ = "user_tbl"
    user_id      = db.Column(db.String(50), primary_key=True)
    bin_id       = db.Column(db.String(50), db.ForeignKey("bin_tbl.bin_id"))
    user_name    = db.Column(db.String(50))
    password     = db.Column(db.String(50))
    name         = db.Column(db.String(50))
    address      = db.Column(db.String(50))
    phone_number = db.Column(db.String(10))
    panchayath   = db.Column(db.String(50))
    ward_no      = db.Column(db.Integer)

class Worker(db.Model):
    __tablename__ = "worker_tbl"
    id           = db.Column(db.String(50), primary_key=True)
    name         = db.Column(db.String(50))
    phone_number = db.Column(db.String(10))
    email        = db.Column(db.String(50))
    charge       = db.Column(db.String(50))
    password     = db.Column(db.String(50))
    panchayath   = db.Column(db.String(50))
    ward_no      = db.Column(db.Integer)

class Payment(db.Model):
    __tablename__ = "payment_tbl"
    id      = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey("user_tbl.user_id"))
    bin_id  = db.Column(db.String(50), db.ForeignKey("bin_tbl.bin_id"))
    date    = db.Column(db.String(50))
    amount  = db.Column(db.Float)
    status  = db.Column(db.String(50), default="Pending")

class Feedback(db.Model):
    __tablename__ = "feedback_tbl"
    id       = db.Column(db.String(50), primary_key=True)
    user_id  = db.Column(db.String(50), db.ForeignKey("user_tbl.user_id"))
    feedback = db.Column(db.String(50))

class History(db.Model):
    __tablename__ = "history_tbl"
    id      = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey("user_tbl.user_id"))
    amount  = db.Column(db.Float)
    date    = db.Column(db.String(40))
    weight  = db.Column(db.Float)
    payment = db.Column(db.String(50))

class Information(db.Model):
    __tablename__ = "information_tbl"
    id         = db.Column(db.String(50), primary_key=True)
    waste_type = db.Column(db.String(50))
    month      = db.Column(db.String(50))

# ─── Routes: ESP32 ───────────────────────────────────────────────────────────
@app.route("/api/bin/status", methods=["POST"])
def update_bin_status():
    """Called by ESP32 every 5 seconds with sensor readings."""
    data = request.get_json()
    level_recyclable    = data.get("level_recyclable", 0)
    level_nonrecyclable = data.get("level_nonrecyclable", 0)
    weight              = data.get("weight", 0)

    # Determine bin status
    min_level = min(level_recyclable, level_nonrecyclable)
    if min_level < 5:
        status = "Full"
    elif min_level < 15:
        status = "Half Full"
    else:
        status = "Empty"

    # Update or create bin record (using default bin ID "BIN001")
    bin_record = Bin.query.get("BIN001")
    if not bin_record:
        bin_record = Bin(bin_id="BIN001", status=status)
        db.session.add(bin_record)
    else:
        bin_record.status = status

    # Log to account table
    log = Account(
        id=str(datetime.utcnow().timestamp()),
        bin_id="BIN001",
        timestamp=datetime.utcnow(),
        level=int(min_level),
        weight=weight,
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({"status": "ok", "bin_status": status})


@app.route("/api/alert", methods=["POST"])
def receive_alert():
    """Called by ESP32 when bin exceeds threshold."""
    data  = request.get_json()
    atype = data.get("type")
    value = data.get("value")
    unit  = data.get("unit")

    print(f"⚠️  ALERT: {atype} = {value}{unit}")
    # TODO: Push notification to admin mobile app / FCM
    return jsonify({"status": "alert_received", "type": atype})


# ─── Routes: Auth ────────────────────────────────────────────────────────────
@app.route("/api/user/login", methods=["POST"])
def user_login():
    data = request.get_json()
    user = User.query.filter_by(
        user_name=data.get("username"),
        password=data.get("password")
    ).first()
    if user:
        return jsonify({"status": "success", "user_id": user.user_id,
                        "name": user.name, "bin_id": user.bin_id})
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401


@app.route("/api/user/register", methods=["POST"])
def user_register():
    data = request.get_json()
    import uuid
    user = User(
        user_id      = str(uuid.uuid4())[:8],
        bin_id       = data.get("bin_id"),
        user_name    = data.get("username"),
        password     = data.get("password"),
        name         = data.get("name"),
        address      = data.get("address"),
        phone_number = data.get("phone"),
        panchayath   = data.get("panchayath"),
        ward_no      = data.get("ward_no"),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"status": "success", "user_id": user.user_id})


@app.route("/api/worker/login", methods=["POST"])
def worker_login():
    data   = request.get_json()
    worker = Worker.query.filter_by(
        email=data.get("email"),
        password=data.get("password")
    ).first()
    if worker:
        return jsonify({"status": "success", "worker_id": worker.id,
                        "name": worker.name})
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401


# ─── Routes: Bin ─────────────────────────────────────────────────────────────
@app.route("/api/bin/<bin_id>", methods=["GET"])
def get_bin_status(bin_id):
    bin_record = Bin.query.get(bin_id)
    if not bin_record:
        return jsonify({"status": "error", "message": "Bin not found"}), 404
    latest = Account.query.filter_by(bin_id=bin_id)\
                          .order_by(Account.timestamp.desc()).first()
    return jsonify({
        "bin_id": bin_id,
        "status": bin_record.status,
        "weight": latest.weight if latest else 0,
        "level":  latest.level  if latest else 0,
    })


# ─── Routes: Payment ─────────────────────────────────────────────────────────
@app.route("/api/payment", methods=["POST"])
def make_payment():
    data = request.get_json()
    import uuid
    payment = Payment(
        id      = str(uuid.uuid4())[:8],
        user_id = data.get("user_id"),
        bin_id  = data.get("bin_id"),
        date    = datetime.utcnow().strftime("%Y-%m-%d"),
        amount  = data.get("amount"),
        status  = "Paid",
    )
    db.session.add(payment)
    db.session.commit()
    return jsonify({"status": "success", "payment_id": payment.id})


@app.route("/api/payment/history/<user_id>", methods=["GET"])
def payment_history(user_id):
    payments = Payment.query.filter_by(user_id=user_id).all()
    return jsonify([{
        "id": p.id, "date": p.date,
        "amount": p.amount, "status": p.status
    } for p in payments])


# ─── Routes: Feedback ─────────────────────────────────────────────────────────
@app.route("/api/feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json()
    import uuid
    fb = Feedback(
        id       = str(uuid.uuid4())[:8],
        user_id  = data.get("user_id"),
        feedback = data.get("feedback"),
    )
    db.session.add(fb)
    db.session.commit()
    return jsonify({"status": "success"})


@app.route("/api/feedback/all", methods=["GET"])
def all_feedbacks():
    feedbacks = Feedback.query.all()
    return jsonify([{"id": f.id, "user_id": f.user_id,
                     "feedback": f.feedback} for f in feedbacks])


# ─── Routes: Admin ────────────────────────────────────────────────────────────
@app.route("/api/admin/bins", methods=["GET"])
def all_bins():
    bins = Bin.query.all()
    return jsonify([{"bin_id": b.bin_id, "status": b.status} for b in bins])


@app.route("/api/admin/collections", methods=["GET"])
def all_collections():
    logs = Account.query.order_by(Account.timestamp.desc()).limit(50).all()
    return jsonify([{
        "bin_id":    l.bin_id,
        "timestamp": l.timestamp.isoformat(),
        "level":     l.level,
        "weight":    l.weight,
    } for l in logs])


# ─── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Database tables created.")
    app.run(host="0.0.0.0", port=5000, debug=True)
