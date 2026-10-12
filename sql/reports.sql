-- =========================================================
-- (a) ORDER TOTALS
-- Expected: 180 orders, revenue 99860.20, AOV 554.78
-- =========================================================

SELECT
    COUNT(*) AS total_orders,
    ROUND(
        SUM(
            o.quantity * p.price *
            (1 - COALESCE(o.discount_pct, 0) / 100.0)
        ),
        2
    ) AS total_revenue,
    ROUND(
        AVG(
            o.quantity * p.price *
            (1 - COALESCE(o.discount_pct, 0) / 100.0)
        ),
        2
    ) AS avg_order_value
FROM orders AS o
JOIN products AS p
    ON o.product_id = p.product_id;


-- =========================================================
-- (b) COUNT(*) VS COUNT(rating)
-- Expected: 180, 165, 15
-- =========================================================

SELECT
    COUNT(*) AS total_orders,
    COUNT(rating) AS rated_orders,
    COUNT(*) - COUNT(rating) AS missing_ratings
FROM orders;


-- =========================================================
-- (c1) ZERO-ORDER CUSTOMERS USING LEFT JOIN
-- Expected: C045, Vihaan
-- =========================================================

SELECT
    c.customer_id,
    c.name
FROM customers AS c
LEFT JOIN orders AS o
    ON c.customer_id = o.customer_id
GROUP BY
    c.customer_id,
    c.name
HAVING COUNT(o.order_id) = 0;


-- =========================================================
-- (c2) ZERO-ORDER CUSTOMERS USING NOT IN
-- Expected: C045, Vihaan
-- =========================================================

SELECT
    customer_id,
    name
FROM customers
WHERE customer_id NOT IN (
    SELECT DISTINCT customer_id
    FROM orders
)
ORDER BY customer_id;


-- =========================================================
-- (d) CITY-WISE RETURN RATE
-- Expected:
-- Jaipur    | 19 | 8  | 42.1
-- Lucknow   | 49 | 15 | 30.6
-- Bangalore | 33 | 8  | 24.2
-- =========================================================

SELECT
    c.city,
    COUNT(*) AS total_orders,
    SUM(o.returned) AS returned_orders,
    ROUND(
        100.0 * SUM(o.returned) / COUNT(*),
        1
    ) AS return_rate_pct
FROM orders AS o
JOIN customers AS c
    ON o.customer_id = c.customer_id
GROUP BY c.city
HAVING ROUND(
    100.0 * SUM(o.returned) / COUNT(*),
    1
) > 20
ORDER BY return_rate_pct DESC;


-- =========================================================
-- (e1) TOP FIVE CUSTOMERS BY SPEND
-- Expected:
-- C043 | Reyansh | 12920.00
-- C026 | Isha    | 8371.60
-- C008 | Meera   | 4564.60
-- C011 | Arjun   | 4111.00
-- C042 | Sanya   | 3785.00
--
-- customer_id ASC breaks spending ties deterministically.
-- =========================================================

SELECT
    c.customer_id,
    c.name,
    ROUND(
        SUM(
            o.quantity * p.price *
            (1 - COALESCE(o.discount_pct, 0) / 100.0)
        ),
        2
    ) AS total_spend
FROM orders AS o
JOIN products AS p
    ON o.product_id = p.product_id
JOIN customers AS c
    ON o.customer_id = c.customer_id
GROUP BY
    c.customer_id,
    c.name
ORDER BY
    total_spend DESC,
    c.customer_id ASC
LIMIT 5;


-- =========================================================
-- (e2) RANKS 3-5 USING LIMIT AND OFFSET
-- Expected:
-- C008 | Meera | 4564.60
-- C011 | Arjun | 4111.00
-- C042 | Sanya | 3785.00
-- =========================================================

SELECT
    c.customer_id,
    c.name,
    ROUND(
        SUM(
            o.quantity * p.price *
            (1 - COALESCE(o.discount_pct, 0) / 100.0)
        ),
        2
    ) AS total_spend
FROM orders AS o
JOIN products AS p
    ON o.product_id = p.product_id
JOIN customers AS c
    ON o.customer_id = c.customer_id
GROUP BY
    c.customer_id,
    c.name
ORDER BY
    total_spend DESC,
    c.customer_id ASC
LIMIT 3 OFFSET 2;


-- =========================================================
-- (f) CATEGORY-WISE ORDER COUNT AND REVENUE
-- Expected:
-- Haircare     | 54 | 44956.10
-- Skincare     | 60 | 27346.00
-- Babycare     | 30 | 16805.00
-- PersonalCare | 36 | 10753.10
-- =========================================================

SELECT
    p.category,
    COUNT(o.order_id) AS order_count,
    ROUND(
        SUM(
            o.quantity * p.price *
            (1 - COALESCE(o.discount_pct, 0) / 100.0)
        ),
        2
    ) AS category_revenue
FROM orders AS o
JOIN products AS p
    ON o.product_id = p.product_id
JOIN customers AS c
    ON o.customer_id = c.customer_id
GROUP BY p.category
ORDER BY category_revenue DESC;


-- =========================================================
-- (g) CUSTOMERS WHOSE NAMES START WITH A
-- Expected: 10 rows
-- =========================================================

SELECT
    customer_id,
    name
FROM customers
WHERE name LIKE 'A%'
ORDER BY name, customer_id;


-- =========================================================
-- (h) DISTINCT ACQUISITION SOURCES
-- Expected: Ad, Organic, Referral, Social
-- =========================================================

SELECT DISTINCT acquisition_source
FROM customers
ORDER BY acquisition_source;


-- =========================================================
-- (i) ADD AND POPULATE LOYALTY TIER
-- Expected:
-- Gold   | 28
-- Silver | 17
-- Run this section once on a database without loyalty_tier.
-- =========================================================
ALTER TABLE customers
ADD COLUMN loyalty_tier VARCHAR(10);

UPDATE customers
SET loyalty_tier = CASE
    WHEN city_tier = 1 THEN 'Gold'
    ELSE 'Silver'
END;

SELECT
    loyalty_tier,
    COUNT(*) AS customer_count
FROM customers
GROUP BY loyalty_tier
ORDER BY loyalty_tier;
