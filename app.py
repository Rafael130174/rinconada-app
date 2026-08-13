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

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal TEXT NOT NULL,
            numero TEXT NOT NULL,
            monto REAL NOT NULL,
            comprador TEXT NOT NULL,
            vendedor TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS pozo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monto_acumulado REAL NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    # Crear usuario administrador por defecto si no existe
    admin_user = conn.execute('SELECT * FROM usuarios WHERE username = ?', ('admin',)).fetchone()
    if not admin_user:
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
    tickets = conn.execute('SELECT * FROM tickets').fetchall()
    conn.close()
    return render_template_string('''
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <nav class="navbar navbar-dark bg-primary"><div class="container">
        <span class="navbar-brand">🐎 La Rinconada Oriental</span>
        <div>
            {% if session.get('user') %}
                <span class="text-white me-2">Hola, {{ session['user'] }} ({{ session['role'] }})</span>
                {% if session['role'] == 'admin' %}
                    <a href="/admin" class="btn btn-light btn-sm">Panel Admin</a>
                {% elif session['role'] == 'vendedor' %}
                    <a href="/vendedor" class="btn btn-light btn-sm">Panel Vendedor</a>
                {% endif %}
                <a href="/logout" class="btn btn-danger btn-sm">Salir</a>
            {% else %}
                <a href="/login" class="btn btn-outline-light btn-sm">Entrar</a>
            {% endif %}
        </div>
    </div></nav>
    <div class="container mt-4">
        <h3>Pozo Actual: ${{ "%.2f"|format(pozo) }}</h3>
        <table class="table mt-3">
            <thead><tr><th>Comprador</th><th>Animalito</th><th>Número</th><th>Monto</th><th>Vendedor</th></tr></thead>
            <tbody>{% for t in tickets %}<tr><td>{{t['comprador']}}</td><td>{{t['animal']}}</td><td>{{t['numero']}}</td><td>${{t['monto']}}</td><td>{{t['vendedor']}}</td></tr>{% endfor %}</tbody>
        </table>
    </div>
    ''', pozo=pozo, tickets=tickets)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        u = request.form.get('usuario')
        p = request.form.get('pass')
        conn = get_db()
        user = conn.execute('SELECT * FROM usuarios WHERE username = ? AND password = ?', (u, p)).fetchone()
        conn.close()
        if user:
            session['user'] = user['username']
            session['role'] = user['role']
            if user['role'] == 'admin':
                return redirect('/admin')
            else:
                return redirect('/vendedor')
        else:
            error = "Usuario o clave incorrectos"
            
    return render_template_string('''
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <div class="container mt-5" style="max-width:350px;">
        <h3 class="text-center mb-3">Iniciar Sesión</h3>
        {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
        <form method="POST" class="card p-3 shadow-sm">
            <input name="usuario" class="form-control mb-2" placeholder="Usuario" required>
            <input name="pass" type="password" class="form-control mb-2" placeholder="Clave" required>
            <button class="btn btn-primary w-100">Entrar</button>
        </form>
        <div class="text-center mt-3"><a href="/">Volver al inicio</a></div>
    </div>
    ''', error=error)

@app.route('/vendedor', methods=['GET', 'POST'])
def vendedor():
    if session.get('role') not in ['vendedor', 'admin']: return redirect('/login')
    msg = ""
    if request.method == 'POST':
        conn = get_db()
        conn.execute('INSERT INTO tickets (animal, numero, monto, comprador, vendedor) VALUES (?,?,?,?,?)', 
                     (request.form['animal'], request.form['num'], request.form['monto'], request.form['nombre'], session['user']))
        conn.execute('UPDATE pozo SET monto_acumulado = monto_acumulado + ?', (request.form['monto'],))
        conn.commit()
        conn.close()
        msg = "¡Ticket registrado con éxito!"

    return render_template_string('''
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <div class="container mt-4" style="max-width:500px;">
        <h2>Panel de Vendedor</h2>
        <p class="text-muted">Registrando jugadas como: <b>{{ session['user'] }}</b></p>
        {% if msg %}<div class="alert alert-success">{{ msg }}</div>{% endif %}
        <form method="POST" class="card p-3 shadow-sm mb-3">
            <input name="nombre" class="form-control mb-2" placeholder="Nombre del Comprador" required>
            <input name="animal" class="form-control mb-2" placeholder="Animalito" required>
            <input name="num" class="form-control mb-2" placeholder="Número" required>
            <input name="monto" type="number" step="0.01" class="form-control mb-2" placeholder="Monto" required>
            <button class="btn btn-success w-100">Registrar Ticket</button>
        </form>
        <a href="/" class="btn btn-secondary w-100">Ver Inicio / Pozo</a>
    </div>
    ''', msg=msg)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('role') != 'admin': return redirect('/login')
    msg = ""
    if request.method == 'POST':
        u = request.form.get('new_user')
        p = request.form.get('new_pass')
        r = request.form.get('new_role')
        if u and p:
            try:
                conn = get_db()
                conn.execute('INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)', (u, p, r))
                conn.commit()
                conn.close()
                msg = f"¡Usuario '{u}' creado como {r}!"
            except:
                msg = "El usuario ya existe."

    conn = get_db()
    usuarios = conn.execute('SELECT * FROM usuarios').fetchall()
    conn.close()

    return render_template_string('''
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <div class="container mt-4">
        <h2>Panel de Administración</h2>
        <p>Control total del sistema y creación de cuentas.</p>
        {% if msg %}<div class="alert alert-info">{{ msg }}</div>{% endif %}
        
        <div class="card p-3 mb-4 shadow-sm">
            <h4>Crear Nuevo Usuario / Vendedor</h4>
            <form method="POST">
                <input name="new_user" class="form-control mb-2" placeholder="Nombre de usuario" required>
                <input name="new_pass" type="password" class="form-control mb-2" placeholder="Contraseña" required>
                <select name="new_role" class="form-control mb-2">
                    <option value="vendedor">Vendedor</option>
                    <option value="admin">Administrador</option>
                </select>
                <button class="btn btn-primary">Crear Cuenta</button>
            </form>
        </div>

        <h4>Usuarios Registrados</h4>
        <ul class="list-group mb-3">
            {% for u in usuarios %}
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    {{ u['username'] }} <span class="badge bg-secondary">{{ u['role'] }}</span>
                </li>
            {% endfor %}
        </ul>
        <a href="/" class="btn btn-secondary">Volver al inicio</a>
    </div>
    ''', usuarios=usuarios, msg=msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()
