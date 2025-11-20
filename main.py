import os
import sys
import random
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, flash
import db

app = Flask(__name__)

# --- КОНФІГУРАЦІЯ ---
app.config.from_mapping(
    SECRET_KEY='your-secret-key-change-this',

    # Параметри підключення до PostgreSQL
    DB_HOST='localhost',
    DB_NAME='flask_blog',
    DB_USER='postgres',
    DB_PASSWORD='postgres'
)

# Пароль для адміністративних дій (видалення/відновлення)
ADMIN_PASSWORD = "admin"

db.init_app(app)


@app.route('/')
def index():
    database = db.get_db()

    with database.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # Пости
        cur.execute('SELECT * FROM posts ORDER BY created DESC')
        posts = cur.fetchall()

        # Логи
        cur.execute('SELECT message, action_time FROM audit_log ORDER BY action_time DESC LIMIT 10')
        logs = cur.fetchall()

        # Архів (тепер беремо ID, щоб можна було відновити)
        cur.execute(
            'SELECT id, title, deleted_at, final_donations FROM deleted_posts ORDER BY deleted_at DESC LIMIT 10')
        deleted = cur.fetchall()

        # Гаманець
        cur.execute('SELECT balance FROM wallet WHERE id = 1')
        wallet = cur.fetchone()

    balance = wallet['balance'] if wallet else 0

    return render_template('index.html', posts=posts, logs=logs, deleted=deleted, wallet_balance=balance)


@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        if not title:
            flash('Title is required.')
        else:
            if db.create_post_transactional(title, content):
                return redirect(url_for('index'))
            else:
                flash("Error saving post.")
    return render_template('create.html')


@app.route('/delete/<int:id>', methods=('POST',))
def delete(id):
    entered_password = request.form.get('password')

    if entered_password == ADMIN_PASSWORD:
        if db.delete_post_transactional(id):
            flash('Успіх: Пост переміщено в архів.', 'success')
        else:
            flash('Помилка бази даних.')
    else:
        flash('Помилка: Невірний пароль адміністратора!')

    return redirect(url_for('index'))


@app.route('/restore/<int:id>', methods=('POST',))
def restore(id):
    entered_password = request.form.get('password')

    if entered_password == ADMIN_PASSWORD:
        if db.restore_post_transactional(id):
            flash('Успіх: Пост відновлено з архіву!', 'success')
        else:
            flash('Помилка при відновленні.')
    else:
        flash('Помилка: Невірний пароль адміністратора!')

    return redirect(url_for('index'))


@app.route('/donate/<int:id>', methods=('POST',))
def donate(id):
    result = db.donate_transactional(id, 100)
    if result == "Success":
        flash(f'Successfully donated 100 coins to post #{id}!')
    elif result == "Not enough funds":
        flash('Error: Not enough money in wallet!')
    elif result == "Database Error":
        flash('Error processing donation.')
    else:
        flash(f'Error: {result}')
    return redirect(url_for('index'))


@app.route('/reset_wallet', methods=('POST',))
def reset_wallet():
    db.reset_wallet()
    flash('Баланс гаманця відновлено до $1000!')
    return redirect(url_for('index'))


@app.route('/test')
def test_yourself():
    my_info = ["Denis", "Rudenok", "KND11"]
    return random.choice(my_info)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'initdb':
        print("Initializing PostgreSQL database...")
        with app.app_context():
            db.init_db()
            db.populate_db()
            print("Done.")
    else:
        print("Starting Flask server...")
        app.run(debug=True)