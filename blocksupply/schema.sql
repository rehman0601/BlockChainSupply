-- BlockSupply Decentralized Supply Cloud
-- MariaDB schema (RDS)

CREATE DATABASE IF NOT EXISTS blocksupply
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE blocksupply;

CREATE TABLE users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(80) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          VARCHAR(20) NOT NULL DEFAULT 'staff',   -- admin | manager | staff
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE warehouses (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  name      VARCHAR(120) NOT NULL,
  location  VARCHAR(200)
) ENGINE=InnoDB;

CREATE TABLE products (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  name           VARCHAR(150) NOT NULL,
  sku            VARCHAR(60) NOT NULL UNIQUE,
  quantity       INT DEFAULT 0,
  reorder_level  INT DEFAULT 10,
  warehouse_id   INT NOT NULL,
  updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
) ENGINE=InnoDB;

CREATE TABLE shipments (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  product_id    INT NOT NULL,
  quantity      INT NOT NULL,
  source        VARCHAR(150) NOT NULL,
  destination   VARCHAR(150) NOT NULL,
  status        VARCHAR(30) DEFAULT 'Pending',   -- Pending | In Transit | Delivered | Cancelled
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB;

CREATE TABLE tasks (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  title         VARCHAR(200) NOT NULL,
  description   TEXT,
  assigned_to   INT,
  created_by    INT,
  status        VARCHAR(30) DEFAULT 'Open',  -- Open | In Progress | Pending Approval | Approved | Rejected | Done
  due_date      DATE,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (assigned_to) REFERENCES users(id),
  FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE approval_chains (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  task_id       INT NOT NULL,
  approver_id   INT NOT NULL,
  status        VARCHAR(20) DEFAULT 'Pending',  -- Pending | Approved | Rejected
  comment       VARCHAR(300),
  decided_at    DATETIME,
  FOREIGN KEY (task_id) REFERENCES tasks(id),
  FOREIGN KEY (approver_id) REFERENCES users(id)
) ENGINE=InnoDB;

-- Indexes for common queries
CREATE INDEX idx_products_warehouse ON products(warehouse_id);
CREATE INDEX idx_shipments_status ON shipments(status);
CREATE INDEX idx_shipments_product ON shipments(product_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assignee ON tasks(assigned_to);
