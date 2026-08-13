import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'rinconada_secret_key_2026'
DB_NAME = 'rinconada.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# Aseguramos que la BD tenga todo lo necesario
def init_db():
    conn = get_db()
    conn.execute('CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, animal TEXT, numero TEXT, monto REAL, comprador TEXT, vendedor TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS pozo (id INTEGER PRIMARY KEY AUTOINCREMENT, monto_acumulado REAL)')
    conn.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT)')
    if not conn.execute('SELECT * FROM usuarios WHERE username = ?', ('admin',)).fetchone():
        conn.execute('INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)', ('admin', '1234', 'admin'))
    if conn.execute('SELECT COUNT(*) FROM pozo').fetchone()[0] == 0:
        conn.execute('INSERT INTO pozo (monto_acumulado) VALUES (0.0)')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = get_db()
    pozo = conn.execute('SELECT SUM(monto_acumulado) FROM pozo').fetchone()[0] or 0.0
    # Aquí traemos todas las jugadas para que se vean como en el primer script
    tickets = conn.execute('SELECT * FROM tickets ORDER BY id DESC').fetchall()
    conn.close()
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>La Rinconada Oriental</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-dark bg-primary shadow-sm mb-4">
            <div class="container-fluid">
                <span class="navbar-brand">🐎 La Rinconada Oriental</span>
                <div>
                    {% if session.get('user') %}
                        <a href="/{{ 'admin' if session['role']=='admin' else 'vendedor' }}" class="btn btn-light btn-sm">Panel</a>
                        <a href="/logout" class="btn btn-danger btn-sm">Salir</a>
                    {% else %}
                        <a href="/login" class="btn btn-outline-light btn-sm">Ingresar</a>
                    {% endif %}
                </div>
            </div>
        </nav>
        <div class="container">
            <div class="card p-4 text-center mb-4 border-0 shadow-sm">
                <h4 class="text-success">Pozo Acumulado</h4>
                <h1 class="display-4 fw-bold">${{ "%.2f"|format(pozo) }}</h1>
            </div>
            <div class="card p-4 border-0 shadow-sm">
                <h3>Jugadas y Tickets</h3>
                <table class="table table-hover mt-3">
                    <thead class="table-dark">
                        <tr><th>ID</th><th>Comprador</th><th>Animalito</th><th>Nro</th><th>Monto</th><th>Vendedor</th></tr>
                    </thead>
                    <tbody>
                        {% for t in tickets %}
                        <tr>
                            <td>{{ t['id'] }}</td>
                            <td>{{ t['comprador'] }}</td>
                            <td>{{ t['animal'] }}</td>
                            <td>{{ t['numero'] }}</td>
                            <td>${{ "%.2f"|format(t['monto']) }}</td>
                            <td><span class="badge bg-secondary">{{ t['vendedor'] }}</span></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    ''', pozo=pozo, tickets=tickets)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db()
        user = conn.execute('SELECT * FROM usuarios WHERE username = ? AND password = ?', 
                           (request.form['usuario'], request.form['pass'])).fetchone()
        conn.close()
        if user:
            session['user'] = user['username']
            session['role'] = user['role']
            return redirect('/admin' if user['role'] == 'admin' else '/vendedor')
    return '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><body class="bg-primary d-flex vh-100 align-items-center justify-content-center"><form method="POST" class="card p-4" style="width:300px;"><h4 class="mb-3">Ingreso</h4><input name="usuario" class="form-control mb-2" placeholder="Usuario"><input name="pass" type="password" class="form-control mb-2" placeholder="Clave"><button class="btn btn-success w-100">Entrar</button><a href="/" class="btn btn-link mt-2">Volver</a></form></body>'

@app.route('/vendedor', methods=['GET', 'POST'])
def vendedor():
    if not session.get('user'): return redirect('/login')
    if request.method == 'POST':
        conn = get_db()
        conn.execute('INSERT INTO tickets (animal, numero, monto, comprador, vendedor) VALUES (?,?,?,?,?)', 
                     (request.form['animal'], request.form['num'], request.form['monto'], request.form['nombre'], session['user']))
        conn.execute('UPDATE pozo SET monto_acumulado = monto_acumulado + ?', (request.form['monto'],))
        conn.commit()
        conn.close()
    return render_template_string('''
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <div class="container mt-4" style="max-width:400px;">
        <h3>Venta - {{ session['user'] }}</h3>
        <form method="POST" class="card p-3">
            <input name="nombre" class="form-control mb-2" placeholder="Comprador" required>
            <input name="animal" class="form-control mb-2" placeholder="Animal" required>
            <input name="num" class="form-control mb-2" placeholder="Número" required>
            <input name="monto" type="number" class="form-control mb-2" placeholder="Monto" required>
            <button class="btn btn-success w-100">Registrar</button>
        </form>
        <a href="/" class="btn btn-secondary w-100 mt-2">Volver al Inicio</a>
    </div>
    ''')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('role') != 'admin': return redirect('/login')
    if request.method == 'POST':
        conn = get_db()
        conn.execute('INSERT INTO usuarios (username, password, role) VALUES (?,?,?)', 
                     (request.form['new_user'], request.form['new_pass'], request.form['new_role']))
        conn.commit()
        conn.close()
    return render_template_string('''
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <div class="container mt-4" style="max-width:500px;">
        <h3>Panel Admin</h3>
        <form method="POST" class="card p-3 mb-4">
            <input name="new_user" class="form-control mb-2" placeholder="Usuario nuevo" required>
            <input name="new_pass" type="password" class="form-control mb-2" placeholder="Clave" required>
            <select name="new_role" class="form-control mb-2"><option value="vendedor">Vendedor</option><option value="admin">Administrador</option></select>
            <button class="btn btn-primary w-100">Crear Usuario</button>
        </form>
        <a href="/" class="btn btn-secondary w-100">Ir al Inicio</a>
    </div>
    ''')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run()
