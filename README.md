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

```text
├── .gitignore
├── architecture-diagram.png                 # Architecture diagram image
├── blockSupply_documetation.pdf             # Project documentation (PDF format)
├── bs.pem                                   # SSH private key for EC2 access (locally ignored)
├── requirements.txt                         # Top-level Python requirements
└── BlockChainSupply/                        # Flask application source directory
    ├── .env.example                         # Environment variables template
    ├── README.md                            # Project overview and setup instructions
    ├── app.py                               # Main Flask application (routes, models, APIs)
    ├── config.py                            # Database configuration and app settings
    ├── models.py                            # database models (SQLAlchemy)
    ├── requirements.txt                     # Source-level Python requirements
    ├── schema.sql                           # Raw database schema & setup tables
    ├── deploy/                              # AWS deployment configurations & docs
    │   ├── BlockSupply_Documentation.pdf    # Detailed system deployment documentation
    │   ├── DEPLOYMENT_GUIDE.md              # Step-by-step AWS infrastructure setup
    │   ├── PRICING_ANALYSIS.md              # Cost analysis for AWS Free Tier and paid tiers
    │   ├── architecture-diagram.png         # AWS architecture diagram (PNG)
    │   ├── architecture-diagram.svg         # AWS architecture diagram (SVG)
    │   └── blocksupply.service              # Systemd unit file for Gunicorn service
    ├── static/                              # Static UI assets
    │   └── style.css                        # Main custom CSS styling
    └── templates/                           # Jinja2 HTML templates for the frontend
        ├── base.html                        # Shared shell layout with navigation
        ├── dashboard.html                   # Overview dashboard page
        ├── inventory.html                   # Inventory management page
        ├── login.html                       # Login page
        ├── reports.html                     # Reports export page
        ├── shipments.html                   # Shipment tracking page
        └── workflow.html                    # Workflow task approvals page
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
