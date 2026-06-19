# BlockSupply — Decentralized Supply Cloud

A Supply Chain Management Dashboard built with Flask, demonstrating core AWS
cloud concepts: **EC2, RDS (MariaDB), S3, CloudWatch, IAM, and VPC**.

## Features

- **Role-based access** — Admin, Manager, Operational Staff
- **Inventory Management** — add products, update quantity, warehouse tracking
- **Shipment Tracking** — status updates, source/destination
- **Workflow Management** — task assignment, manager → admin approval chains
- **Reporting Dashboard** — inventory metrics, shipment analytics, CSV export to S3

## Tech Stack

- **Backend**: Flask, Flask-SQLAlchemy, Flask-Login
- **Database**: MariaDB (Amazon RDS)
- **Storage**: Amazon S3 (via boto3, IAM role — no static credentials)
- **Monitoring**: Amazon CloudWatch (infra metrics + custom app metrics)
- **Deployment**: Amazon EC2 (Amazon Linux 2023, gunicorn + systemd)

## Project Structure

```
blocksupply/
├── app.py                     # Flask application & routes
├── models.py                  # SQLAlchemy models
├── config.py                  # Environment-based configuration
├── schema.sql                 # MariaDB DDL
├── requirements.txt
├── .env.example
├── templates/                 # Jinja2 templates
├── static/style.css
└── deploy/
    ├── DEPLOYMENT_GUIDE.md    # Step-by-step AWS setup
    ├── PRICING_ANALYSIS.md
    ├── architecture-diagram.svg / .png
    └── blocksupply.service    # systemd unit for gunicorn
```

## Local Setup (development)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DB_HOST etc. — or point at a local MariaDB/MySQL
export FLASK_APP=app.py
flask seed-db           # creates tables + demo users
python app.py           # http://localhost:5000
```

Demo accounts: `admin/admin123` · `manager/manager123` · `staff/staff123`

## AWS Deployment

See [`deploy/DEPLOYMENT_GUIDE.md`](deploy/DEPLOYMENT_GUIDE.md) for full
step-by-step instructions covering VPC, RDS, S3, IAM, EC2, and CloudWatch.

## Architecture

See [`deploy/architecture-diagram.png`](deploy/architecture-diagram.png).

EC2 (public subnet) runs the Flask app behind a security group; it connects
to RDS MariaDB (private subnet, only reachable from the app's security
group) for relational data, and to S3 (via an IAM instance role — no
hardcoded keys) for report storage. CloudWatch monitors both EC2/RDS
infrastructure metrics and custom application metrics.

## Database Design

See [`schema.sql`](schema.sql). Core tables: `users`, `warehouses`,
`products`, `shipments`, `tasks`, `approval_chains`.

## Pricing

See [`deploy/PRICING_ANALYSIS.md`](deploy/PRICING_ANALYSIS.md) — this
architecture runs at $0/month on AWS Free Tier; ~$33–36/month on standard
on-demand pricing.
