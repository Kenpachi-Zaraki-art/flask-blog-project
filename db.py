import psycopg2
import psycopg2.extras
from flask import current_app, g


def get_db():
    """ Підключення до PostgreSQL """
    if 'db' not in g:
        g.db = psycopg2.connect(
            host=current_app.config['DB_HOST'],
            database=current_app.config['DB_NAME'],
            user=current_app.config['DB_USER'],
            password=current_app.config['DB_PASSWORD']
        )
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with db.cursor() as cur:
        with current_app.open_resource('schema.sql') as f:
            cur.execute(f.read().decode('utf8'))
    db.commit()


# --- ТРАНЗАКЦІЇ (PostgreSQL) ---

def create_post_transactional(title, content):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'INSERT INTO posts (title, content) VALUES (%s, %s)',
                (title, content)
            )
        db.commit()
        return True
    except psycopg2.Error as e:
        db.rollback()
        print(f"Create Transaction failed: {e}")
        return False


def delete_post_transactional(post_id):
    db = get_db()
    try:
        # Використовуємо RealDictCursor для доступу по іменах колонок
        with db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM posts WHERE id = %s', (post_id,))
            post = cur.fetchone()

            if post is None:
                return False

            # Копіюємо в архів
            cur.execute(
                'INSERT INTO deleted_posts (original_id, title, content, final_donations) VALUES (%s, %s, %s, %s)',
                (post['id'], post['title'], post['content'], post['donations'])
            )
            # Видаляємо з основної таблиці
            cur.execute('DELETE FROM posts WHERE id = %s', (post_id,))

        db.commit()
        return True
    except psycopg2.Error as e:
        db.rollback()
        print(f"Delete Transaction failed: {e}")
        return False


def restore_post_transactional(archive_id):
    db = get_db()
    try:
        with db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 1. Знаходимо пост в архіві
            cur.execute('SELECT * FROM deleted_posts WHERE id = %s', (archive_id,))
            post = cur.fetchone()

            if post is None:
                return False

            # 2. Вставляємо назад у posts (разом з донатами!)
            cur.execute(
                'INSERT INTO posts (title, content, donations) VALUES (%s, %s, %s)',
                (post['title'], post['content'], post['final_donations'])
            )

            # 3. Видаляємо з архіву
            cur.execute('DELETE FROM deleted_posts WHERE id = %s', (archive_id,))

            # 4. Логуємо
            cur.execute("INSERT INTO audit_log (message) VALUES (%s)",
                        (f"Restored post '{post['title']}' from archive",))

        db.commit()
        return True
    except psycopg2.Error as e:
        db.rollback()
        print(f"Restore Transaction failed: {e}")
        return False


def donate_transactional(post_id, amount):
    db = get_db()
    try:
        with db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 1. Перевірка гаманця
            cur.execute('SELECT balance FROM wallet WHERE id = 1')
            wallet = cur.fetchone()

            if wallet is None:
                return "Database Error"

            if wallet['balance'] < amount:
                return "Not enough funds"

            # 2. Списання
            cur.execute('UPDATE wallet SET balance = balance - %s WHERE id = 1', (amount,))

            # 3. Нарахування
            cur.execute('UPDATE posts SET donations = donations + %s WHERE id = %s', (amount, post_id))

            # 4. Логування
            cur.execute("INSERT INTO audit_log (message) VALUES (%s)",
                        (f'Donated ${amount} to post #{post_id}',))

        db.commit()
        return "Success"

    except psycopg2.Error as e:
        db.rollback()
        print(f"Donation Transaction failed: {e}")
        return "Database Error"


def reset_wallet():
    db = get_db()
    with db.cursor() as cur:
        cur.execute('UPDATE wallet SET balance = 1000 WHERE id = 1')
    db.commit()


def populate_db():
    create_post_transactional("Перший пост", "Це вміст першого тестового поста (PostgreSQL).")
    create_post_transactional("Про автора", "Цей flask додаток був написаний Денисом Руденком")


def init_app(app):
    app.teardown_appcontext(close_db)