-- Standalone analysis queries (MySQL 8.0+). Run them in MySQL Workbench / CLI
-- after you have some price_history rows (python seed_demo.py gives you demo data).

-- 1) Change versus the previous check, per product (LAG + named window)
SELECT p.title, h.checked_at, h.price,
       LAG(h.price) OVER w AS prev_price,
       ROUND(100 * (h.price - LAG(h.price) OVER w) / LAG(h.price) OVER w, 2) AS change_pct
FROM price_history h
JOIN products p ON p.id = h.product_id
WINDOW w AS (PARTITION BY h.product_id ORDER BY h.checked_at)
ORDER BY p.title, h.checked_at;

-- 2) Running minimum and 3-check moving average
SELECT product_id, checked_at, price,
       MIN(price) OVER (PARTITION BY product_id ORDER BY checked_at) AS running_min,
       ROUND(AVG(price) OVER (PARTITION BY product_id ORDER BY checked_at
                              ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS moving_avg_3
FROM price_history
ORDER BY product_id, checked_at;

-- 3) How far is each product's current price below its all-time high? (CTE + RANK)
WITH ranked AS (
  SELECT product_id, price,
         ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY checked_at DESC) AS rn,
         MAX(price)   OVER (PARTITION BY product_id) AS max_price,
         MIN(price)   OVER (PARTITION BY product_id) AS min_price
  FROM price_history
)
SELECT p.title, r.price AS current_price, r.max_price, r.min_price,
       ROUND(100 * (r.max_price - r.price) / r.max_price, 2) AS pct_below_high,
       RANK() OVER (ORDER BY (r.max_price - r.price) / r.max_price DESC) AS deal_rank
FROM ranked r
JOIN products p ON p.id = r.product_id
WHERE r.rn = 1;

-- 4) Biggest single-check price drops
WITH changes AS (
  SELECT product_id, checked_at, price,
         LAG(price) OVER (PARTITION BY product_id ORDER BY checked_at) AS prev_price
  FROM price_history
)
SELECT p.title, c.checked_at, c.prev_price, c.price,
       ROUND(100 * (c.price - c.prev_price) / c.prev_price, 2) AS change_pct
FROM changes c
JOIN products p ON p.id = c.product_id
WHERE c.prev_price IS NOT NULL AND c.price < c.prev_price
ORDER BY change_pct ASC
LIMIT 10;

-- 5) Checks where the price was at or below the user's target
SELECT p.title, p.target_price, h.price, h.checked_at
FROM price_history h
JOIN products p ON p.id = h.product_id
WHERE p.target_price IS NOT NULL AND h.price <= p.target_price
ORDER BY h.checked_at DESC;
