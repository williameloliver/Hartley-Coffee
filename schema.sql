CREATE TABLE products (
  id VARCHAR(80) PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  price INTEGER NOT NULL,
  type VARCHAR(20) NOT NULL,
  recipe_grams REAL NOT NULL DEFAULT 0
);
CREATE TABLE combo_components (
  id INTEGER PRIMARY KEY,
  combo_id VARCHAR(80) NOT NULL REFERENCES products(id),
  component_product_id VARCHAR(80) NOT NULL REFERENCES products(id),
  quantity INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE sales (
  id VARCHAR(80) PRIMARY KEY,
  product_id VARCHAR(80) NOT NULL REFERENCES products(id),
  product_name VARCHAR(120) NOT NULL,
  unit_price INTEGER NOT NULL,
  quantity INTEGER NOT NULL,
  mode VARCHAR(20) NOT NULL,
  created_at_ms BIGINT NOT NULL
);
CREATE TABLE expenses (
  id VARCHAR(80) PRIMARY KEY,
  amount INTEGER NOT NULL,
  description VARCHAR(200) NOT NULL,
  category VARCHAR(80) NOT NULL,
  created_at_ms BIGINT NOT NULL
);
CREATE TABLE inventory (
  id INTEGER PRIMARY KEY,
  day_date VARCHAR(10) NOT NULL,
  start_cups VARCHAR(40) NOT NULL DEFAULT '',
  end_cups VARCHAR(40) NOT NULL DEFAULT '',
  start_grams VARCHAR(40) NOT NULL DEFAULT '',
  end_grams VARCHAR(40) NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE extra_stock (
  id INTEGER PRIMARY KEY,
  product_id VARCHAR(80) NOT NULL REFERENCES products(id),
  start_units VARCHAR(40) NOT NULL DEFAULT '',
  end_units VARCHAR(40) NOT NULL DEFAULT ''
);
