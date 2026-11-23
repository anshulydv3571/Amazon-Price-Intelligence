-- Run once:  mysql -u root -p < sql/schema.sql
-- Requires MySQL 8.0+ (the analysis queries use window functions and CTEs).

CREATE DATABASE IF NOT EXISTS price_tracker
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE price_tracker;

CREATE TABLE IF NOT EXISTS products (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  url              VARCHAR(500)  NOT NULL,
  title            VARCHAR(500)  NOT NULL,
  target_price     DECIMAL(10,2) NULL,
  email            VARCHAR(255)  NULL,
  is_active        TINYINT(1)    NOT NULL DEFAULT 1,
  last_alert_price DECIMAL(10,2) NULL,
  created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_products_url (url)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS price_history (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  product_id  INT           NOT NULL,
  price       DECIMAL(10,2) NOT NULL,
  checked_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_history_product FOREIGN KEY (product_id)
    REFERENCES products (id) ON DELETE CASCADE,
  INDEX idx_history_product_time (product_id, checked_at)
) ENGINE=InnoDB;
