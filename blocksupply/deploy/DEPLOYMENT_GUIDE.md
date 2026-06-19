# BlockSupply — AWS Deployment Guide

This guide walks through deploying the BlockSupply Flask app on AWS using the
account you already have. Follow it top to bottom — each section builds on
the last. Budget roughly 60–90 minutes including RDS provisioning time.

---

## 0. Prerequisites

- AWS account with console access
- A key pair for SSH (create one in EC2 → Key Pairs if you don't have one, download the `.pem`)
- This project's code (zipped or on GitHub)

---

## 1. VPC Setup

You can use the **default VPC** to save time, or create a custom one for a
cleaner architecture diagram match:

1. Go to **VPC Console → Create VPC** → "VPC and more"
2. Name: `blocksupply-vpc`, IPv4 CIDR: `10.0.0.0/16`
3. Number of Availability Zones: 1 (fine for a demo)
4. Public subnets: 1 (`10.0.1.0/24`) — Private subnets: 1 (`10.0.2.0/24`)
5. NAT gateway: **None** (saves cost — skip unless private subnet needs internet)
6. Create VPC

This auto-creates an Internet Gateway, route tables, and subnet associations.

### Security Groups
Create two security groups in this VPC:

**`web-sg`** (for EC2)
- Inbound: SSH (22) from My IP, HTTP (80) from 0.0.0.0/0, Custom TCP (5000) from 0.0.0.0/0 (for testing before you put a proxy in front)
- Outbound: All traffic

**`db-sg`** (for RDS)
- Inbound: MySQL/Aurora (3306) from **`web-sg`** (select the security group, not an IP range)
- Outbound: All traffic

---

## 2. RDS (MariaDB)

1. **RDS Console → Create database**
2. Engine: **MariaDB**
3. Template: **Free tier**
4. DB instance identifier: `blocksupply-db`
5. Master username: `admin`, set a strong master password (save it)
6. Instance class: `db.t3.micro` (free tier eligible)
7. Storage: 20 GB gp2 (default is fine)
8. Connectivity → VPC: `blocksupply-vpc`
9. Subnet group: create new, using the **private subnet**
10. Public access: **No**
11. VPC security group: select **`db-sg`** (remove default)
12. Initial database name: `blocksupply`
13. Create database (takes 5–10 minutes — start this early)

Once available, copy the **Endpoint** (looks like
`blocksupply-db.xxxxxxx.ap-south-1.rds.amazonaws.com`) — you'll need it for `.env`.

---

## 3. S3 Bucket

1. **S3 Console → Create bucket**
2. Name: `blocksupply-reports-<your-unique-suffix>` (bucket names are global, add initials/roll number)
3. Region: same as EC2/RDS (e.g. `ap-south-1`)
4. Block all public access: **Keep enabled** (the app uses IAM role access, not public URLs)
5. Create bucket
6. Inside the bucket, you can optionally pre-create folders `reports/` and `documents/`

---

## 4. IAM Role (for EC2 → S3 + CloudWatch access)

This is what lets the app upload to S3 and push CloudWatch metrics **without
hardcoding AWS keys** — the right way to do it.

1. **IAM Console → Roles → Create role**
2. Trusted entity: **AWS service → EC2**
3. Attach policies:
   - `AmazonS3FullAccess` (or scope to your bucket for extra credit — see note below)
   - `CloudWatchAgentServerPolicy`
4. Name: `blocksupply-ec2-role`
5. Create role

> **Scoped policy (optional, better practice):** instead of `AmazonS3FullAccess`,
> create a custom policy restricting `s3:PutObject`/`s3:GetObject` to
> `arn:aws:s3:::blocksupply-reports-<suffix>/*`. Mention this tradeoff in your
> documentation — it shows you understand least-privilege IAM.

---

## 5. EC2 Instance

1. **EC2 Console → Launch instance**
2. Name: `blocksupply-app`
3. AMI: **Amazon Linux 2023**
4. Instance type: `t2.micro` (free tier)
5. Key pair: select yours
6. Network: `blocksupply-vpc`, **public subnet**, auto-assign public IP: **Enable**
7. Security group: select **`web-sg`**
8. Advanced details → **IAM instance profile**: select `blocksupply-ec2-role`
9. Launch instance

### Connect and deploy

SSH in:
```bash
ssh -i your-key.pem ec2-user@<EC2_PUBLIC_IP>
```

Install dependencies:
```bash
sudo yum update -y
sudo yum install -y python3.11 python3.11-pip git mariadb105
git clone <your-github-repo-url> blocksupply
cd blocksupply
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Configure environment:
```bash
cp .env.example .env
nano .env   # fill in DB_HOST (RDS endpoint), DB_PASSWORD, S3_BUCKET, AWS_REGION
```

Initialize the database (creates tables + demo users):
```bash
export FLASK_APP=app.py
flask seed-db
```

Quick test run:
```bash
python app.py
# visit http://<EC2_PUBLIC_IP>:5000
```

Run as a managed service (recommended for screenshots/demo stability):
```bash
sudo cp deploy/blocksupply.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable blocksupply
sudo systemctl start blocksupply
sudo systemctl status blocksupply
```

The app will now run on port 5000 and restart automatically if it crashes.

---

## 6. CloudWatch

### Infrastructure metrics (automatic)
EC2 and RDS already report basic metrics (CPU, network) to CloudWatch with
**no setup required**. Go to **CloudWatch → Metrics → EC2 / RDS** to view them.

### Application logs
The Flask app logs to stdout. For real log shipping, install the CloudWatch
agent:
```bash
sudo yum install -y amazon-cloudwatch-agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
```
Point it at your systemd journal or redirect gunicorn logs to a file and
configure the agent to tail that file. For a class project, screenshotting
the built-in EC2 CPU/Network graphs plus the journal logs
(`sudo journalctl -u blocksupply -n 50`) is usually sufficient.

### Custom metrics
The app also pushes custom metrics (`UserLogin`, `ReportExported`) via boto3
to the `BlockSupply/App` namespace — visible under **CloudWatch → Metrics →
Custom Namespaces** after you've logged in / exported a report at least once.

---

## 7. Screenshots checklist (for your deliverable)

- [ ] EC2 instance running (console)
- [ ] RDS instance available, showing endpoint
- [ ] S3 bucket with an uploaded report
- [ ] CloudWatch EC2 CPU/Network graph
- [ ] CloudWatch custom metric (UserLogin or ReportExported)
- [ ] App running in browser — dashboard, inventory, shipments, workflow, reports
- [ ] Security group inbound rules (web-sg and db-sg)

---

## 8. Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| Can't connect to RDS from EC2 | `db-sg` not allowing `web-sg` | Re-check inbound rule references the SG, not an IP |
| S3 upload fails with AccessDenied | IAM role not attached, or attached after launch | Stop/start instance after attaching role, or attach via Actions → Security → Modify IAM role |
| EC2 unreachable on port 5000 | Security group missing inbound rule | Add Custom TCP 5000 (or just use 80 + reverse proxy) |
| RDS stuck in "creating" | Normal — takes 5–10 min | Start this step first, work on Flask app while waiting |
| `flask seed-db` fails to connect | Wrong DB_HOST or app launched in different subnet/SG | Verify `.env` matches RDS endpoint exactly, security group order |
