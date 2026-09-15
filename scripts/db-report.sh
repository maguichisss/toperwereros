#!/bin/sh
# Business snapshot report for reconciliation / pre-meeting sanity checks.
# Runs read-only SQL against the compose database.
set -e

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

docker compose -f "$COMPOSE_FILE" exec -T db psql -U postgres -d store_catalog -P pager=off -v ON_ERROR_STOP=1 <<'SQL'
\echo '=== Products ==='
SELECT
  COUNT(*)                                      AS products,
  COUNT(*) FILTER (WHERE stock > 0)             AS in_stock,
  COUNT(*) FILTER (WHERE stock = 0)             AS out_of_stock,
  COALESCE(SUM(stock * price), 0)               AS inventory_value
FROM products;

\echo '=== Sales (count / total) ==='
SELECT
  COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE)          AS today,
  COUNT(*) FILTER (WHERE created_at >= date_trunc('week', now()))  AS this_week,
  COUNT(*) FILTER (WHERE created_at >= date_trunc('month', now())) AS this_month,
  COALESCE(SUM(total) FILTER (WHERE created_at::date = CURRENT_DATE), 0)          AS total_today,
  COALESCE(SUM(total) FILTER (WHERE created_at >= date_trunc('week', now())), 0)  AS total_week,
  COALESCE(SUM(total) FILTER (WHERE created_at >= date_trunc('month', now())), 0) AS total_month
FROM sales;

\echo '=== Apartados ==='
SELECT
  COUNT(*) FILTER (WHERE status = 'active')                                   AS active,
  COALESCE(SUM(balance) FILTER (WHERE status = 'active'), 0)                  AS active_balance,
  COUNT(*) FILTER (WHERE status = 'completed')                                AS completed,
  COUNT(*) FILTER (WHERE status = 'cancelled')                                AS cancelled
FROM layaways;

\echo '=== Clientes ==='
SELECT COUNT(*) AS customers, COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE) AS created_today
FROM customers;

\echo '=== Usuarios / roles ==='
SELECT r.name AS role, COUNT(u.id) AS users
FROM roles r LEFT JOIN users u ON u.role_id = r.id
GROUP BY r.name ORDER BY r.name;
SQL