import os
import json
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave_secreta_super_segura_rinconada')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///rinconada.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

ANIMALITOS = {
    "0": "Delfín", "00": "Ballena", "1": "Carnero", "2": "Toro", "3": "Ciempiés",
    "4": "Alacrán", "5": "León", "6": "Rana", "7": "Perico", "8": "Ratón",
    "9": "Águila", "10": "Tigre", "11": "Gato", "12": "Caballo", "13": "Mono",
    "14": "Paloma", "15": "Zorro", "16": "Oso", "17": "Pavo", "18": "Burro",
    "19": "Chivo", "20": "Cochino", "21": "Gallo", "22": "Camello", "23": "Cebra",
    "24": "Iguana", "25": "Gallina", "26": "Vaca", "27": "Perro", "28": "Zamuro",
    "29": "Elefante", "30": "Caimán", "31": "Lapa", "32": "Ardilla", "33": "Pescado",
    "34": "Venado", "35": "Jirafa", "36": "Culebra"
}

PRECIO_POR_COMBINACION = 50.0 / 8.0

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='cliente')

class Boleto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(30), nullable=True)
    loteria = db.Column(db.String(50), nullable=False)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    cuadro_json = db.Column(db.Text, nullable=False)
    pote_3 = db.Column(db.String(5), nullable=False)
    pote_6 = db.Column(db.String(5), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.now)

class Acumulado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    acum_6 = db.Column(db.Float, default=0.0)
    acum_5 = db.Column(db.Float, default=0.0)
    acum_4 = db.Column(db.Float, default=0.0)
    acum_pote = db.Column(db.Float, default=0.0)

class Historial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.String(30), nullable=False)
    ventas = db.Column(db.Float, nullable=False)
    ganancia = db.Column(db.Float, nullable=False)
    premios = db.Column(db.Float, nullable=False)
    ganadores_txt = db.Column(db.String(100), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- HTML TEMPLATES ---
LOGIN_HTML = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Acceso</title><style>body{font-family:sans-serif; background:#1a73e8; display:flex; justify-content:center; align-items:center; height:100vh; margin:0;}
.card{background:white; padding:25px; border-radius:12px; width:90%; max-width:360px; text-align:center;}
input{width:100%; padding:12px; margin:8px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;}
button{background:#28a745; color:white; border:none; padding:12px; width:100%; border-radius:6px; cursor:pointer; font-weight:bold;}</style></head>
<body><div class="card"><h2>ACCESO</h2><form method="POST"><input type="text" name="username" placeholder="Usuario" required><input type="password" name="password" placeholder="Contraseña" required><button type="submit">Iniciar Sesión</button></form><a href="/registro">¿No tienes cuenta? Regístrate</a></div></body></html>
"""

REGISTRO_HTML = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Registro</title><style>body{font-family:sans-serif; background:#1a73e8; display:flex; justify-content:center; align-items:center; height:100vh; margin:0;}
.card{background:white; padding:25px; border-radius:12px; width:90%; max-width:360px; text-align:center;}
input{width:100%; padding:12px; margin:8px 0; border:1px solid #ccc; border-radius:6px; box-sizing:border-box;}
button{background:#1a73e8; color:white; border:none; padding:12px; width:100%; border-radius:6px; cursor:pointer; font-weight:bold;}</style></head>
<body><div class="card"><h2>REGISTRO</h2><form method="POST"><input type="text" name="username" placeholder="Usuario" required><input type="password" name="password" placeholder="Contraseña" required><button type="submit">Registrarse</button></form></div></body></html>
"""

MAIN_HTML = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>La Rinconada</title><style>body{font-family:sans-serif; background:#f0f2f5; padding:10px;}
.card{background:white; padding:15px; border-radius:12px; max-width:500px; margin:10px auto; box-shadow:0 2px 5px rgba(0,0,0,0.1);}
.grid{display:grid; grid-template-columns:repeat(2, 1fr); gap:5px; max-height:100px; overflow-y:auto; border:1px solid #eee; padding:5px;}
.btn{background:#28a745; color:white; border:none; padding:12px; width:100%; border-radius:8px; font-weight:bold; cursor:pointer; margin-top:10px;}
.ticket-box{background:#fff8e1; border:2px dashed #ffe082; padding:10px; margin-top:15px; font-family:monospace; white-space:pre-wrap;}
</style></head>
<body>
<div class="card" style="background:#1a73e8; color:white; text-align:center;"><h1>LA RINCONADA</h1>
{% if current_user.is_authenticated %} <b>{{ current_user.username }}</b> | <a href="/logout" style="color:white;">Salir</a> {% else %} <a href="/login" style="color:white;">Entrar</a> {% endif %}
</div>
<div class="card">
<form method="POST" action="/vender">
<label>Lotería:</label><select name="loteria" style="width:100%; padding:8px;"><option>Loto Activo</option><option>La Granjita</option></select>
<label>Nombre:</label><input type="text" name="cliente" value="{% if current_user.is_authenticated %}{{ current_user.username }}{% endif %}" required style="width:100%; padding:8px; box-sizing:border-box;">
{% for i, hora in validas %}
<p><b>Válida {{ i }} ({{ hora }})</b></p>
<div class="grid">
{% for k, v in animalitos.items() %}<label style="font-size:12px;"><input type="checkbox" name="val_{{ i }}" value="{{ k }}"> {{ k }} {{ v }}</label>{% endfor %}
</div>
{% if i in [3, 6] %} <select name="pote_fijo_{{ i }}" style="width:100%; margin-top:5px;"><option value="">Fijo Pote {{ i }}</option>{% for k, v in animalitos.items() %}<option value="{{ k }}">{{ k }} {{ v }}</option>{% endfor %}</select> {% endif %}
{% endfor %}
<button type="submit" class="btn">Generar Ticket</button>
</form>
{% if ticket %}<div class="ticket-box">{{ ticket }}</div>{% endif %}
</div>
</body></html>
"""

# --- RUTAS ---
@app.route('/')
def home():
    validas = [(1, "1 PM"), (2, "2 PM"), (3, "3 PM"), (4, "4 PM"), (5, "5 PM"), (6, "6 PM")]
    acum = Acumulado.query.first() or Acumulado(acum_6=0, acum_5=0, acum_4=0, acum_pote=0)
    return render_template_string(MAIN_HTML, animalitos=ANIMALITOS, validas=validas, acum=acum, ticket=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password_hash, request.form['password']):
            login_user(u)
            return redirect(url_for('home'))
    return render_template_string(LOGIN_HTML)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        u = User(username=request.form['username'], password_hash=generate_password_hash(request.form['password']), role='cliente')
        db.session.add(u)
        db.session.commit()
        login_user(u)
        return redirect(url_for('home'))
    return render_template_string(REGISTRO_HTML)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/vender', methods=['POST'])
@login_required
def vender():
    validas_list = [(1, "1 PM"), (2, "2 PM"), (3, "3 PM"), (4, "4 PM"), (5, "5 PM"), (6, "6 PM")]
    cuadro_res = {str(i): request.form.getlist(f'val_{i}') for i in range(1, 7)}
    pote_3, pote_6 = request.form.get('pote_fijo_3'), request.form.get('pote_fijo_6')
    
    if not all(cuadro_res.values()) or not pote_3 or not pote_6:
        return "Error: Faltan datos"

    combinaciones = 1
    detalle_validas = ""
    for i in range(1, 7):
        sel = cuadro_res[str(i)]
        combinaciones *= len(sel)
        detalle_validas += f"  Válida {i}: {', '.join([ANIMALITOS[k] for k in sel])}\n"
    
    monto = combinaciones * PRECIO_POR_COMBINACION
    
    ticket_res = f"""🧾 TICKET RINCONADA
👤 Cliente: {request.form['cliente']}
----------------------------
📋 JUGADA:
{detalle_validas}----------------------------
🔥 POTE FIJO:
  • Válida 3: {ANIMALITOS[pote_3]}
  • Válida 6: {ANIMALITOS[pote_6]}
----------------------------
💵 TOTAL: {monto:.2f} Bs."""
    
    return render_template_string(MAIN_HTML, animalitos=ANIMALITOS, validas=validas_list, ticket=ticket_res, acum=Acumulado.query.first())

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password_hash=generate_password_hash('admin'), role='admin'))
        db.session.commit()

if __name__ == '__main__':
    app.run()
