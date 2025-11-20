-- Очищення старих таблиць
DROP TABLE IF EXISTS posts CASCADE;
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS deleted_posts CASCADE;
DROP TABLE IF EXISTS wallet CASCADE;

-- 1. Гаманець
CREATE TABLE wallet (
  id SERIAL PRIMARY KEY,
  balance INTEGER NOT NULL DEFAULT 1000
);

INSERT INTO wallet (balance) VALUES (1000);

-- 2. Пости
CREATE TABLE posts (
  id SERIAL PRIMARY KEY,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  donations INTEGER NOT NULL DEFAULT 0
);

-- 3. Логи аудиту
CREATE TABLE audit_log (
  id SERIAL PRIMARY KEY,
  action_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  message TEXT NOT NULL
);

-- 4. Архів
CREATE TABLE deleted_posts (
  id SERIAL PRIMARY KEY,
  original_id INTEGER,
  deleted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  final_donations INTEGER
);

-- 5. ТРИГЕР (Для PostgreSQL це робиться у 2 етапи)

-- Етап А: Створюємо функцію
CREATE OR REPLACE FUNCTION log_new_post_func()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (message)
    VALUES ('Created new post: ' || NEW.title);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Етап Б: Прив'язуємо функцію до таблиці
CREATE TRIGGER log_new_post
AFTER INSERT ON posts
FOR EACH ROW
EXECUTE FUNCTION log_new_post_func();