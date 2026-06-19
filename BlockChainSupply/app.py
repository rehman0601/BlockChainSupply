import csv
import io
import logging
import os
from datetime import datetime

import boto3
from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from functools import wraps

from config import Config
from models import db, User, Warehouse, Product, Shipment, Task, ApprovalChain

# --- Logging setup (stdout -> picked up by CloudWatch agent on EC2) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("blocksupply")

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Role-based access decorator ---
def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("login"))
            if current_user.role not in roles:
                flash("You do not have permission to access that page.", "error")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


# --- CloudWatch custom metric helper ---
def put_metric(metric_name, value=1, unit="Count"):
    """Push a custom metric to CloudWatch. Fails silently if not on AWS / no IAM role."""
    try:
        cw = boto3.client("cloudwatch", region_name=app.config["AWS_REGION"])
        cw.put_metric_data(
            Namespace=app.config["CLOUDWATCH_NAMESPACE"],
            MetricData=[{"MetricName": metric_name, "Value": value, "Unit": unit}],
        )
    except Exception as e:
        logger.warning(f"CloudWatch metric push skipped: {e}")


# ---------------- Auth ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            logger.info(f"User '{username}' logged in (role={user.role})")
            put_metric("UserLogin")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
        logger.warning(f"Failed login attempt for username '{username}'")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------- Dashboard ----------------

@app.route("/")
@login_required
def dashboard():
    total_products = Product.query.count()
    low_stock = Product.query.filter(Product.quantity <= Product.reorder_level).count()
    total_shipments = Shipment.query.count()
    pending_shipments = Shipment.query.filter_by(status="Pending").count()
    open_tasks = Task.query.filter(Task.status.in_(["Open", "In Progress"])).count()

    return render_template(
        "dashboard.html",
        total_products=total_products,
        low_stock=low_stock,
        total_shipments=total_shipments,
        pending_shipments=pending_shipments,
        open_tasks=open_tasks,
    )


# ---------------- Inventory Management ----------------

@app.route("/inventory")
@login_required
def inventory():
    products = Product.query.all()
    warehouses = Warehouse.query.all()
    return render_template("inventory.html", products=products, warehouses=warehouses)


@app.route("/inventory/add", methods=["POST"])
@roles_required("admin", "manager")
def add_product():
    name = request.form.get("name")
    sku = request.form.get("sku")
    quantity = int(request.form.get("quantity", 0))
    reorder_level = int(request.form.get("reorder_level", 10))
    warehouse_id = request.form.get("warehouse_id")

    product = Product(
        name=name, sku=sku, quantity=quantity,
        reorder_level=reorder_level, warehouse_id=warehouse_id,
    )
    db.session.add(product)
    db.session.commit()
    logger.info(f"Product added: {sku} by {current_user.username}")
    flash("Product added.", "success")
    return redirect(url_for("inventory"))


@app.route("/inventory/<int:product_id>/update", methods=["POST"])
@roles_required("admin", "manager", "staff")
def update_quantity(product_id):
    product = Product.query.get_or_404(product_id)
    new_quantity = int(request.form.get("quantity"))
    product.quantity = new_quantity
    db.session.commit()
    logger.info(f"Quantity updated for {product.sku} -> {new_quantity} by {current_user.username}")
    flash("Quantity updated.", "success")
    return redirect(url_for("inventory"))


@app.route("/warehouses/add", methods=["POST"])
@roles_required("admin", "manager")
def add_warehouse():
    name = request.form.get("name")
    location = request.form.get("location")
    db.session.add(Warehouse(name=name, location=location))
    db.session.commit()
    flash("Warehouse added.", "success")
    return redirect(url_for("inventory"))


# ---------------- Shipment Tracking ----------------

@app.route("/shipments")
@login_required
def shipments():
    all_shipments = Shipment.query.order_by(Shipment.created_at.desc()).all()
    products = Product.query.all()
    return render_template("shipments.html", shipments=all_shipments, products=products)


@app.route("/shipments/add", methods=["POST"])
@roles_required("admin", "manager")
def add_shipment():
    shipment = Shipment(
        product_id=request.form.get("product_id"),
        quantity=int(request.form.get("quantity")),
        source=request.form.get("source"),
        destination=request.form.get("destination"),
        status="Pending",
    )
    db.session.add(shipment)
    db.session.commit()
    logger.info(f"Shipment created #{shipment.id} by {current_user.username}")
    flash("Shipment created.", "success")
    return redirect(url_for("shipments"))


@app.route("/shipments/<int:shipment_id>/status", methods=["POST"])
@login_required
def update_shipment_status(shipment_id):
    shipment = Shipment.query.get_or_404(shipment_id)
    shipment.status = request.form.get("status")
    shipment.updated_at = datetime.utcnow()
    db.session.commit()
    logger.info(f"Shipment #{shipment_id} status -> {shipment.status} by {current_user.username}")
    flash("Shipment status updated.", "success")
    return redirect(url_for("shipments"))


# ---------------- Workflow Management ----------------

@app.route("/workflow")
@login_required
def workflow():
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    users = User.query.all()
    return render_template("workflow.html", tasks=tasks, users=users)


@app.route("/workflow/add", methods=["POST"])
@roles_required("admin", "manager")
def add_task():
    task = Task(
        title=request.form.get("title"),
        description=request.form.get("description"),
        assigned_to=request.form.get("assigned_to"),
        created_by=current_user.id,
        due_date=request.form.get("due_date") or None,
        status="Open",
    )
    db.session.add(task)
    db.session.commit()

    # Manager-created tasks above a certain scope require admin approval
    if current_user.role == "manager":
        task.status = "Pending Approval"
        admin = User.query.filter_by(role="admin").first()
        if admin:
            db.session.add(ApprovalChain(task_id=task.id, approver_id=admin.id))
        db.session.commit()

    flash("Task created.", "success")
    return redirect(url_for("workflow"))


@app.route("/workflow/<int:task_id>/status", methods=["POST"])
@login_required
def update_task_status(task_id):
    task = Task.query.get_or_404(task_id)
    task.status = request.form.get("status")
    db.session.commit()
    flash("Task status updated.", "success")
    return redirect(url_for("workflow"))


@app.route("/workflow/approval/<int:approval_id>/decide", methods=["POST"])
@roles_required("admin")
def decide_approval(approval_id):
    approval = ApprovalChain.query.get_or_404(approval_id)
    decision = request.form.get("decision")  # Approved / Rejected
    approval.status = decision
    approval.comment = request.form.get("comment", "")
    approval.decided_at = datetime.utcnow()
    approval.task.status = decision
    db.session.commit()
    logger.info(f"Approval #{approval_id} -> {decision} by {current_user.username}")
    flash(f"Task {decision.lower()}.", "success")
    return redirect(url_for("workflow"))


# ---------------- Reporting Dashboard ----------------

@app.route("/reports")
@login_required
def reports():
    products = Product.query.all()
    shipments_list = Shipment.query.all()

    inventory_by_warehouse = {}
    for p in products:
        wh = p.warehouse.name if p.warehouse else "Unassigned"
        inventory_by_warehouse[wh] = inventory_by_warehouse.get(wh, 0) + p.quantity

    shipment_status_counts = {}
    for s in shipments_list:
        shipment_status_counts[s.status] = shipment_status_counts.get(s.status, 0) + 1

    return render_template(
        "reports.html",
        inventory_by_warehouse=inventory_by_warehouse,
        shipment_status_counts=shipment_status_counts,
        low_stock_products=[p for p in products if p.low_stock],
    )


@app.route("/reports/export")
@roles_required("admin", "manager")
def export_report():
    """Generate a CSV inventory report and upload it to S3."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["SKU", "Name", "Warehouse", "Quantity", "Reorder Level", "Low Stock"])
    for p in Product.query.all():
        writer.writerow([
            p.sku, p.name, p.warehouse.name if p.warehouse else "",
            p.quantity, p.reorder_level, p.low_stock,
        ])

    filename = f"inventory_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    try:
        s3 = boto3.client("s3", region_name=app.config["AWS_REGION"])
        s3.put_object(
            Bucket=app.config["S3_BUCKET"],
            Key=f"reports/{filename}",
            Body=output.getvalue().encode("utf-8"),
            ContentType="text/csv",
        )
        logger.info(f"Report uploaded to S3: reports/{filename}")
        flash(f"Report uploaded to S3 as reports/{filename}", "success")
        put_metric("ReportExported")
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        flash(f"S3 upload failed (check IAM role / bucket): {e}", "error")

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


# ---------------- Health check (for ALB / monitoring) ----------------

@app.route("/health")
def health():
    return {"status": "ok"}, 200


# ---------------- CLI: seed database ----------------

@app.cli.command("seed-db")
def seed_db():
    """Create tables and seed demo users/data. Usage: flask --app app seed-db"""
    db.create_all()

    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", role="admin")
        admin.set_password("admin123")
        manager = User(username="manager", role="manager")
        manager.set_password("manager123")
        staff = User(username="staff", role="staff")
        staff.set_password("staff123")
        db.session.add_all([admin, manager, staff])

        wh1 = Warehouse(name="Thane Central Warehouse", location="Thane, MH")
        wh2 = Warehouse(name="Mumbra Distribution Hub", location="Mumbra, MH")
        db.session.add_all([wh1, wh2])
        db.session.commit()

        p1 = Product(name="Steel Bolts (M8)", sku="SKU-1001", quantity=500, reorder_level=100, warehouse_id=wh1.id)
        p2 = Product(name="Industrial Sensors", sku="SKU-1002", quantity=15, reorder_level=20, warehouse_id=wh1.id)
        p3 = Product(name="Packaging Boxes (L)", sku="SKU-1003", quantity=1200, reorder_level=300, warehouse_id=wh2.id)
        db.session.add_all([p1, p2, p3])
        db.session.commit()

        s1 = Shipment(product_id=p1.id, quantity=200, source="Thane Central Warehouse",
                       destination="Pune Hub", status="In Transit")
        s2 = Shipment(product_id=p3.id, quantity=400, source="Mumbra Distribution Hub",
                       destination="Navi Mumbai Retail", status="Delivered")
        db.session.add_all([s1, s2])
        db.session.commit()

        print("Seeded database with demo users: admin/admin123, manager/manager123, staff/staff123")
    else:
        print("Database already seeded.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
