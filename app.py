import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'rinconada_secret_key_2026'

DB_NAME = 'rinconada.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal TEXT NOT NULL,
            numero TEXT NOT NULL,
            monto REAL NOT NULL,
            comprador TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pozo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monto_acumulado REAL NOT NULL
        )
    ''')
    cursor.execute('SELECT COUNT(*) FROM pozo')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO pozo (monto_acumulado) VALUES (0.0)')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(monto_acumulado) FROM pozo')
    pozo = cursor.fetchone()[0] or 0.0
    cursor.execute('SELECT * FROM tickets')
    tickets = cursor.fetchall()
    conn.close()

    html = '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>La Rinconada Oriental de la Suerte</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-dark bg-primary shadow-sm">
            <div class="container-fluid">
                <span class="navbar-brand mb-0 h1">🐎 La Rinconada Oriental</span>
                <div>
                    {% if session.get('logged_in') %}
                        <a href="{{ url_for('admin') }}" class="btn btn-light btn-sm me-2">Panel Admin</a>
                        <a href="{{ url_for('logout') }}" class="btn btn-danger btn-sm">Salir</a>
                    {% else %}
                        <a href="{{ url_for('login') }}" class="btn btn-outline-light btn-sm">Ingresar al Sistema</a>
                    {% endif %}
                </div>
            </div>
        </nav>
        <div class="container mt-4">
            <div class="card shadow-sm p-4 text-center mb-4 bg-white">
                <h2 class="text-success">Pozo Acumulado Actual</h2>
                <h1 class="display-4 fw-bold text-dark">${{ "%.2f"|format(pozo) }}</h1>
            </div>
            <div class="card shadow-sm p-4 bg-white">
                <h3>Jugadas y Tickets Registrados</h3>
                <table class="table table-striped mt-3">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Comprador</th>
                            <th>Animalito</th>
                            <th>Número</th>
                            <th>Monto</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for t in tickets %}
                        <tr>
                            <td>{{ t[0] }}</td>
                            <td>{{ t[4] }}</td>
                            <td>{{ t[1] }}</td>
                            <td>{{ t[2] }}</td>
                            <td>${{ "%.2f"|format(t[3]) }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, pozo=pozo, tickets=tickets)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('usuario')
        pwd = request.form.get('contraseña')
        if user == 'admin' and pwd == '1234':
            session['logged_in'] = True
            return redirect(url_for('admin'))
    
    login_html = '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ingreso - La Rinconada</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-primary d-flex align-items-center justify-content-center vh-100">
        <div class="card p-4 shadow" style="width: 350px;">
            <h4 class="text-center mb-3">🐎 Ingreso al Sistema</h4>
            <form method="POST">
                <div class="mb-3">
                    <input type="text" name="usuario" class="form-control" placeholder="Usuario" required>
                </div>
                <div class="mb-3">
                    <input type="password" name="contraseña" class="form-control" placeholder="Contraseña" required>
                </div>
                <button type="submit" class="btn btn-success w-100">Entrar al Sistema</button>
            </form>
        </div>
    </body>
    </html>
    '''
    return render_template_string(login_html)

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return '''
        <h1>Panel de Administración</h1>
        <p>Bienvenido al panel de control exclusivo.</p>
        <a href="/">Volver al inicio</a> | <a href="/logout">Cerrar sesión</a>
    '''

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
