import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production")

    # --- RDS (MariaDB) connection ---
    DB_USER = os.environ.get("DB_USER", "admin")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "blocksupply")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- S3 ---
    S3_BUCKET = os.environ.get("S3_BUCKET", "blocksupply-reports")
    AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")

    # --- CloudWatch ---
    CLOUDWATCH_NAMESPACE = os.environ.get("CLOUDWATCH_NAMESPACE", "BlockSupply/App")
