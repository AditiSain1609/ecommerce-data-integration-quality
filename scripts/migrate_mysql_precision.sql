-- One-time upgrade for MySQL databases created before DECIMAL(12,2) was used.
-- Run with a database administrator account against ecommerce_quality.
ALTER TABLE products MODIFY price DECIMAL(12,2) NOT NULL;
ALTER TABLE orders MODIFY total_amount DECIMAL(12,2) NOT NULL;
ALTER TABLE order_items MODIFY unit_price DECIMAL(12,2) NOT NULL;
ALTER TABLE order_items MODIFY line_total DECIMAL(12,2) NOT NULL;
ALTER TABLE payments MODIFY payment_amount DECIMAL(12,2) NOT NULL;
ALTER TABLE pipeline_runs MODIFY error_message LONGTEXT NULL;
