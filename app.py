from datetime import datetime, timedelta
import json
import os
import random
import string
from flask import Flask, redirect, render_template_string, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', 'clave_secreta_super_segura_rinconada'
)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///rinconada.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

ANIMALITOS = {
    '0': 'Delfín',
    '00': 'Ballena',
    '1': 'Carnero',
    '2': 'Toro',
    '3': 'Ciempiés',
    '4': 'Alacrán',
    '5': 'León',
    '6': 'Rana',
    '7': 'Perico',
    '8': 'Ratón',
    '9': 'Águila',
    '10': 'Tigre',
    '11': 'Gato',
    '12': 'Caballo',
    '13': 'Mono',
    '14': 'Paloma',
    '15': 'Zorro',
    '16': 'Oso',
    '17': 'Pavo',
    '18': 'Burro',
    '19': 'Chivo',
    '20': 'Cochino',
    '21': 'Gallo',
    '22': 'Camello',
    '23': 'Cebra',
    '24': 'Iguana',
    '25': 'Gallina',
    '26': 'Vaca',
    '27': 'Perro',
    '28': 'Zamuro',
    '29': 'Elefante',
    '30': 'Caimán',
    '31': 'Lapa',
    '32': 'Ardilla',
    '33': 'Pescado',
    '34': 'Venado',
    '35': 'Jirafa',
    '36': 'Culebra',
}

PRECIO_POR_COMBINACION = 50.0 / 8.0


def generar_codigo_ticket():
  letras = ''.join(random.choices(string.ascii_uppercase, k=4))
  numeros = ''.join(random.choices(string.digits, k=4))
  return f'RINC-{letras}-{numeros}'


class User(UserMixin, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(50), unique=True, nullable=False)
  password_hash = db.Column(db.String(256), nullable=False)
  role = db.Column(db.String(20), default='cliente')
  balance = db.Column(db.Float, default=0.0)
  commission_earned = db.Column(db.Float, default=0.0)


class RechargeRequest(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
  amount = db.Column(db.Float, nullable=False)
  reference = db.Column(db.String(100), nullable=False)
  bank = db.Column(db.String(100), nullable=False)
  status = db.Column(db.String(20), default='Pendiente')
  date = db.Column(db.DateTime, default=datetime.now)
  user = db.relationship('User', backref=db.backref('recharges', lazy=True))


# <-- NUEVO: Tabla para gestionar solicitudes de pago móvil (retiros)
class WithdrawalRequest(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
  amount = db.Column(db.Float, nullable=False)
  phone = db.Column(db.String(30), nullable=False)
  bank = db.Column(db.String(100), nullable=False)
  ci = db.Column(db.String(30), nullable=False)
  status = db.Column(db.String(20), default='Pendiente')
  date = db.Column(db.DateTime, default=datetime.now)
  user = db.relationship('User', backref=db.backref('withdrawals', lazy=True))


class Boleto(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  codigo_ticket = db.Column(db.String(30), unique=True, nullable=False)
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


LOGIN_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acceso - La Rinconada Oriental</title>
    <style>
        body { font-family: sans-serif; background: #1a73e8; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); width: 90%; max-width: 360px; text-align: center; }
        h2 { color: #1a73e8; margin-bottom: 15px; font-size: 20px; }
        input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 15px; }
        button { background: #28a745; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .error { color: red; font-size: 13px; margin-bottom: 10px; }
        .back-link { display: block; margin-top: 12px; color: #1a73e8; text-decoration: none; font-size: 13px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>🏇 ACCESO AL SISTEMA</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Usuario" required>
            <input type="password" name="password" placeholder="Contraseña" required>
            <button type="submit">Iniciar Sesión</button>
        </form>
        <a href="/registro" class="back-link">¿No tienes cuenta? Regístrate aquí</a>
        <a href="/" class="back-link">← Volver al Portal Principal</a>
    </div>
</body>
</html>
"""

REGISTRO_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registro - La Rinconada Oriental</title>
    <style>
        body { font-family: sans-serif; background: #1a73e8; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); width: 90%; max-width: 360px; text-align: center; }
        h2 { color: #1a73e8; margin-bottom: 15px; font-size: 20px; }
        input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 15px; }
        button { background: #1a73e8; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .error { color: red; font-size: 13px; margin-bottom: 10px; }
        .back-link { display: block; margin-top: 12px; color: #1a73e8; text-decoration: none; font-size: 13px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>📝 REGISTRO DE CLIENTE</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Elige un Nombre de Usuario" required>
            <input type="password" name="password" placeholder="Crea una Contraseña" required>
            <button type="submit">Registrarse</button>
        </form>
        <a href="/login" class="back-link">¿Ya tienes cuenta? Inicia sesión</a>
        <a href="/" class="back-link">← Volver al Portal Principal</a>
    </div>
</body>
</html>
"""

MAIN_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>La Rinconada Oriental de la Suerte</title>
    <style>
        body { font-family: sans-serif; background: #f0f2f5; padding: 10px; margin: 0; }
        .header-app { text-align: center; margin-bottom: 15px; background: #1a73e8; color: white; padding: 15px; border-radius: 12px; max-width: 500px; margin: auto; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
        .header-app h1 { margin: 0; font-size: 18px; text-transform: uppercase; }
        .user-bar { background: #ffffff; max-width: 500px; margin: 10px auto; padding: 8px 15px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; font-size: 13px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
        .card { background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); max-width: 500px; margin: auto; margin-bottom: 20px; }
        h2, h3, h4 { color: #1a73e8; text-align: center; margin-top: 5px; }
        label { font-weight: bold; display: block; margin-top: 10px; font-size: 14px; }
        input[type="text"], input[type="password"], input[type="number"], select { width: 100%; padding: 10px; margin-top: 4px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 15px; }
        .valida-box { background: #f8f9fa; border: 1px solid #ddd; padding: 10px; border-radius: 8px; margin-top: 12px; }
        .valida-title { font-weight: bold; color: #333; margin-bottom: 8px; font-size: 15px; }
        .pote-header { color: #d93025; background: #feefef; padding: 4px 8px; border-radius: 4px; }
        .grid-animals { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; max-height: 140px; overflow-y: auto; background: white; padding: 8px; border: 1px solid #eee; border-radius: 6px; }
        .chk-item { font-size: 13px; display: flex; align-items: center; gap: 4px; cursor: pointer; }
        .chk-item input { transform: scale(1.2); }
        .pote-select { background: #fff8e1; border: 1px solid #ffe082; padding: 8px; border-radius: 6px; margin-top: 8px; }
        .btn { background: #28a745; color: white; border: none; padding: 14px; width: 100%; border-radius: 8px; font-size: 18px; margin-top: 20px; font-weight: bold; cursor: pointer; }
        .btn-resultados { background: #d93025; margin-top: 15px; }
        .btn-reset { background: #6c757d; font-size: 12px; padding: 6px; margin-top: 10px; border: none; border-radius: 4px; color: white; cursor: pointer; width: 100%; }
        .ticket-box { background: #fff8e1; border: 2px dashed #ffe082; padding: 12px; border-radius: 8px; margin-top: 15px; }
        .ticket { font-family: monospace; white-space: pre-wrap; font-size: 13px; color: #333; margin: 0; }
        .btn-share { background: #007bff; color: white; border: none; padding: 10px; width: 100%; border-radius: 6px; font-weight: bold; margin-top: 10px; cursor: pointer; font-size: 14px; }
        .reporte-box { background: #e8f0fe; border: 1px solid #aecbfa; padding: 12px; border-radius: 8px; margin-top: 15px; font-size: 14px; color: #174ea6; }
        .acumulado-box { background: #fff3cd; border: 1px solid #ffeeba; padding: 12px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; color: #856404; }
        .winner { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 10px; border-radius: 6px; margin-top: 8px; font-size: 13px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #1a73e8; color: white; }
    </style>
</head>
<body>
    <div class="header-app">
        <h1>🏇 LA RINCONADA ORIENTAL DE LA SUERTE 🎰</h1>
        <p>Portal Oficial de Resultados y Apuestas</p>
    </div>

    <div class="user-bar">
        {% if current_user.is_authenticated %}
            <span>👤 <b>{{ current_user.username }}</b> ({{ current_user.role.upper() }}) | Saldo: <b style="color: #28a745;">{{ "%.2f"|format(current_user.balance) }} Bs.</b></span>
            <a href="/logout" style="color: #d93025; font-weight: bold; text-decoration: none;">Cerrar Sesión</a>
        {% else %}
            <span>🌐 Visitante</span>
            <div>
                <a href="/login" style="color: #1a73e8; font-weight: bold; text-decoration: none; margin-right: 10px;">Entrar</a>
                <a href="/registro" style="color: #28a745; font-weight: bold; text-decoration: none;">Registrarse</a>
            </div>
        {% endif %}
    </div>

    <div class="card">
        <div class="acumulado-box">
            <h3 style="color: #856404; margin: 0 0 10px 0;">🔥 POZO ACUMULADO ACTUAL</h3>
            • <b>6 Aciertos:</b> {{ "%.2f"|format(acum.acum_6) }} Bs.<br>
            • <b>5 Aciertos:</b> {{ "%.2f"|format(acum.acum_5) }} Bs.<br>
            • <b>4 Aciertos:</b> {{ "%.2f"|format(acum.acum_4) }} Bs.<br>
            • <b>Pote Fijo (3 y 6):</b> {{ "%.2f"|format(acum.acum_pote) }} Bs.<br>
            <hr style="border:0; border-top: 1px solid #ffeeba; margin: 6px 0;">
            <b>💰 Gran Pozo Acumulado: {{ "%.2f"|format(acum.acum_6 + acum.acum_5 + acum.acum_4 + acum.acum_pote) }} Bs.</b>
            
            {% if current_user.is_authenticated and current_user.role == 'admin' %}
            <form method="POST" action="/reset" style="margin:0;" onsubmit="return confirm('¿Reiniciar sistema general a 0 Bs.?');">
                <button type="submit" class="btn-reset">🔄 Reiniciar Sistema General a 0 Bs.</button>
            </form>
            {% endif %}
        </div>

        {% if current_user.is_authenticated %}
        
        <div style="background: #e8f0fe; border: 1px solid #aecbfa; padding: 12px; border-radius: 8px; margin-bottom: 15px;">
            <h3 style="color: #174ea6; margin-top:0;">💳 Recargar Billetera (Máximo 1000 Bs.)</h3>
            <form method="POST" action="/solicitar_recarga">
                <label>Monto a Recargar (Bs.):</label>
                <input type="number" step="0.01" name="amount" placeholder="Máximo 1000 Bs" required>
                <label>Banco Emisor:</label>
                <input type="text" name="bank" placeholder="Ej: Banco de Venezuela" required>
                <label>Número de Referencia:</label>
                <input type="text" name="reference" placeholder="Referencia bancaria" required>
                <button type="submit" class="btn" style="background: #174ea6; margin-top: 10px; font-size: 15px; padding: 10px;">📤 Enviar Solicitud de Recarga</button>
            </form>
        </div>

        <!-- NUEVO: Sección para solicitar Retiro a Pago Móvil -->
        <div style="background: #fdf2e9; border: 1px solid #f5cba7; padding: 12px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="color: #d35400; margin-top:0;">💸 Solicitar Retiro a Pago Móvil</h3>
            <form method="POST" action="/solicitar_retiro">
                <label>Monto a Retirar (Bs.):</label>
                <input type="number" step="0.01" name="amount" placeholder="Monto a retirar" required>
                <label>Banco Destino:</label>
                <input type="text" name="bank" placeholder="Ej: Banesco / Banco de Venezuela" required>
                <label>Teléfono (Pago Móvil):</label>
                <input type="text" name="phone" placeholder="Ej: 04121234567" required>
                <label>Cédula de Identidad:</label>
                <input type="text" name="ci" placeholder="Ej: 12345678" required>
                <button type="submit" class="btn" style="background: #d35400; margin-top: 10px; font-size: 15px; padding: 10px;">📥 Solicitar Pago Móvil</button>
            </form>
        </div>

        <h2>🎟️ Registrador de Tickets</h2>
        <form method="POST" action="/vender">
            <label>Lotería:</label>
            <select name="loteria">
                <option value="Loto Activo">Loto Activo</option>
                <option value="La Granjita">La Granjita</option>
                <option value="Lotto Rey">Lotto Rey</option>
            </select>

            <label>Nombre del Cliente o Apostador:</label>
            <input type="text" name="cliente" required value="{% if current_user.role == 'cliente' %}{{ current_user.username }}{% endif %}" placeholder="Ej: Juan Pérez">

            <label>Teléfono / WhatsApp:</label>
            <input type="text" name="telefono" placeholder="Ej: 04121234567">

            <hr style="margin-top: 15px; border: 0; border-top: 1px solid #eee;">
            <p style="text-align: center; font-weight: bold; color: #444; margin: 5px 0;">📋 Selección de Válidas</p>

            {% for i, hora in validas %}
            <div class="valida-box">
                <div class="valida-title {% if i in [3, 6] %}pote-header{% endif %}">
                    Válida {{ i }} ({{ hora }}) {% if i in [3, 6] %}🔥 [POTE]{% endif %}
                </div>
                
                <div class="grid-animals">
                    {% for k, v in animalitos.items() %}
                    <label class="chk-item">
                        <input type="checkbox" name="val_{{ i }}" value="{{ k }}"> {{ k }} - {{ v }}
                    </label>
                    {% endfor %}
                </div>

                {% if i in [3, 6] %}
                <div class="pote-select">
                    <label style="margin:0; color: #b78103;">🎯 FIJO Pote Válida {{ i }}:</label>
                    <select name="pote_fijo_{{ i }}">
                        <option value="">-- Selecciona animalito --</option>
                        {% for k, v in animalitos.items() %}
                        <option value="{{ k }}">{{ k }} - {{ v }}</option>
                        {% endfor %}
                    </select>
                </div>
                {% endif %}
            </div>
            {% endfor %}

            <button type="submit" class="btn">🎟️ Generar Ticket (Descuenta de Saldo)</button>
        </form>

        {% if ticket %}
        <div class="ticket-box">
            <pre class="ticket" id="ticketText">{{ ticket }}</pre>
            <button class="btn-share" onclick="compartirTicket()">📲 Copiar / Compartir Ticket</button>
        </div>
        <script>
        function compartirTicket() {
            var text = document.getElementById("ticketText").innerText;
            if (navigator.share) {
                navigator.share({ text: text });
            } else {
                navigator.clipboard.writeText(text);
                alert("¡Ticket copiado al portapapeles!");
            }
        }
        </script>
        {% endif %}

        {% else %}
        <div style="text-align: center; padding: 15px 0;">
            <h3 style="color: #1a73e8;">📢 ¡Bienvenido a La Rinconada Oriental!</h3>
            <p style="font-size: 14px; color: #555;">Consulta los pozos acumulados, <a href="/registro" style="color: #1a73e8; font-weight: bold;">regístrate para jugar tú mismo</a> o <a href="/login" style="color: #1a73e8; font-weight: bold;">inicia sesión</a>.</p>
        </div>
        {% endif %}
    </div>

    {% if current_user.is_authenticated and current_user.role == 'admin' %}
    <div class="card" style="border: 2px solid #174ea6;">
        <h3 style="color: #174ea6;">📥 Solicitudes de Recarga Pendientes</h3>
        {% if recargas_pendientes %}
        <table>
            <thead>
                <tr>
                    <th>Usuario</th>
                    <th>Monto</th>
                    <th>Banco / Ref</th>
                    <th>Acción</th>
                </tr>
            </thead>
            <tbody>
                {% for r in recargas_pendientes %}
                <tr>
                    <td><b>{{ r.user.username }}</b></td>
                    <td style="color: #28a745; font-weight: bold;">{{ "%.2f"|format(r.amount) }} Bs.</td>
                    <td>{{ r.bank }}<br><small>{{ r.reference }}</small></td>
                    <td>
                        <form method="POST" action="/aprobar_recarga/{{ r.id }}" style="margin:0;">
                            <button type="submit" style="background:#28a745; color:white; border:none; padding:6px 10px; border-radius:4px; cursor:pointer; font-weight:bold;">Aprobar</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p style="text-align: center; color: #777; font-size: 13px;">No hay recargas pendientes.</p>
        {% endif %}
    </div>

    <!-- NUEVO: Panel de aprobaciones de Retiro (Pago Móvil) para el Admin -->
    <div class="card" style="border: 2px solid #d35400;">
        <h3 style="color: #d35400;">📤 Solicitudes de Retiro (Pago Móvil) Pendientes</h3>
        {% if retiros_pendientes %}
        <table>
            <thead>
                <tr>
                    <th>Usuario</th>
                    <th>Monto</th>
                    <th>Datos Pago Móvil</th>
                    <th>Acción</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                {% for w in retiros_pendientes %}
                    <td><b>{{ w.user.username }}</b></td>
                    <td style="color: #d35400; font-weight: bold;">{{ "%.2f"|format(w.amount) }} Bs.</td>
                    <td>{{ w.bank }}<br>{{ w.phone }}<br>CI: {{ w.ci }}</td>
                    <td>
                        <form method="POST" action="/aprobar_retiro/{{ w.id }}" style="margin:0;">
                            <button type="submit" style="background:#d35400; color:white; border:none; padding:6px 10px; border-radius:4px; cursor:pointer; font-weight:bold;">Pagar</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p style="text-align: center; color: #777; font-size: 13px;">No hay solicitudes de retiro pendientes.</p>
        {% endif %}
    </div>

    <div class="card" style="border: 2px solid #1a73e8;">
        <h3 style="color: #1a73e8;">👥 Gestión de Usuarios y Vendedores</h3>
        <form method="POST" action="/crear_usuario">
            <label>Nuevo Usuario Vendedor:</label>
            <input type="text" name="nuevo_user" required placeholder="Ej: vendedor01">
            <label>Contraseña:</label>
            <input type="password" name="nuevo_pass" required placeholder="Clave segura">
            <input type="hidden" name="nuevo_role" value="vendedor">
            <button type="submit" class="btn" style="background: #1a73e8; margin-top: 15px;">➕ Registrar Vendedor Autorizado</button>
        </form>

        <h4 style="margin-top: 20px;">📋 Lista de Usuarios y Comisiones (10%)</h4>
        <table>
            <thead>
                <tr>
                    <th>Usuario</th>
                    <th>Rol</th>
                    <th>Comisión (10%)</th>
                    <th>Acción</th>
                </tr>
            </thead>
            <tbody>
                {% for u in usuarios_lista %}
                <tr>
                    <td><b>{{ u.username }}</b></td>
                    <td>{{ u.role.upper() }}</td>
                    <td style="color: #28a745; font-weight: bold;">{{ "%.2f"|format(u.commission_earned) }} Bs.</td>
                    <td>
                        {% if u.username != 'admin' %}
                        <form method="POST" action="/eliminar_usuario/{{ u.id }}" style="margin:0;" onsubmit="return confirm('¿Eliminar usuario?');">
                            <button type="submit" style="background:#d93025; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;">X</button>
                        </form>
                        {% else %}
                        -
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    {% if ganadores is not none %}
    <div class="card" style="border: 2px solid #28a745;">
        <h3 style="color: #28a745;">🎉 Resultados de la Jornada y Premios Abonados</h3>
        
        {% if current_user.is_authenticated and current_user.role == 'admin' and financiero %}
        <div class="reporte-box">
            <h4 style="margin: 0 0 10px 0; text-align:center;">📊 Balance General</h4>
            <b>💵 Ventas Totales:</b> {{ "%.2f"|format(financiero.total_ventas) }} Bs.<br>
            <b style="color: #28a745;">🏦 Ganancia Banca (30%):</b> {{ "%.2f"|format(financiero.ganancia_banca) }} Bs.<br>
            <b>🎯 Fondo Premios (70%):</b> {{ "%.2f"|format(financiero.pozo_hoy) }} Bs.
        </div>
        {% endif %}

        <h4 style="margin-top: 15px; margin-bottom: 5px;">📋 Tickets Ganadores (Saldo acreditado al usuario si está registrado)</h4>
        {% if ganadores %}
            {% for g in ganadores %}
            <div class="winner">
                <b>Código: {{ g.codigo }}</b><br>
                <b>{{ g.cliente }}</b> ({{ g.telefono }}) - {{ g.loteria }}<br>
                • Premio: <b>{{ g.tipo }}</b> | Monto asignado: <b style="color:#155724;">{{ "%.2f"|format(g.monto_premio) }} Bs.</b>
            </div>
            {% endfor %}
        {% else %}
            <p style="text-align: center; color: #d93025; font-weight: bold; font-size: 14px;">❌ No hubo tickets ganadores en esta jugada.</p>
        {% endif %}
    </div>
    {% endif %}

    {% if current_user.is_authenticated and current_user.role == 'admin' %}
    <div class="card" style="border: 2px solid #d93025;">
        <h3 style="color: #d93025;">🏆 Escrutinio y Finanzas</h3>
        <form method="POST" action="/escrutar">
            <p style="font-size: 13px; color: #666; text-align: center;">Ingresa los 6 animalitos premiados del día:</p>
            {% for i, hora in validas %}
            <label>Válida {{ i }} ({{ hora }})</label>
            <select name="res_val_{{ i }}" required>
                <option value="">-- Selecciona ganador --</option>
                {% for k, v in animalitos.items() %}
                <option value="{{ k }}">{{ k }} - {{ v }}</option>
                {% endfor %}
            </select>
            {% endfor %}
            <button type="submit" class="btn btn-resultados">🔍 Cargar Resultados y Procesar Premios</button>
        </form>
    </div>
    <div class="card" style="border: 1px solid #1a73e8;">
        <h3>📅 Historial de Ventas Diarias</h3>
        {% if historial %}
        <table>
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Venta</th>
                    <th>Ganancia</th>
                    <th>Resultado</th>
                </tr>
            </thead>
            <tbody>
                {% for item in historial %}
                <tr>
                    <td><b>{{ item.fecha }}</b></td>
                    <td>{{ "%.2f"|format(item.ventas) }} Bs.</td>
                    <td style="color: #28a745; font-weight: bold;">{{ "%.2f"|format(item.ganancia) }} Bs.</td>
                    <td>{{ item.ganadores_txt }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p style="text-align: center; color: #777; font-size: 13px;">Sin historial registrado.</p>
        {% endif %}
    </div>
    {% endif %}
</body>
</html>
"""


@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
      login_user(user)
      return redirect(url_for('home'))
    return render_template_string(
        LOGIN_HTML, error='Usuario o contraseña incorrectos'
    )
  return render_template_string(LOGIN_HTML)


@app.route('/registro', methods=['GET', 'POST'])
def registro():
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')
    if User.query.filter_by(username=username).first():
      return render_template_string(
          REGISTRO_HTML, error='El usuario ya existe. Elige otro.'
      )
    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role='cliente',
    )
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return redirect(url_for('home'))
  return render_template_string(REGISTRO_HTML)


@app.route('/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('home'))


@app.route('/')
def home():
  validas_list = [
      (1, '1:00 PM'),
      (2, '2:00 PM'),
      (3, '3:00 PM'),
      (4, '4:00 PM'),
      (5, '5:00 PM'),
      (6, '6:00 PM'),
  ]
  acum = Acumulado.query.first()
  if not acum:
    acum = Acumulado(acum_6=0, acum_5=0, acum_4=0, acum_pote=0)
    db.session.add(acum)
    db.session.commit()
  historial = Historial.query.order_by(Historial.id.desc()).all()
  usuarios_lista = User.query.all()
  recargas_pendientes = RechargeRequest.query.filter_by(
      status='Pendiente'
  ).all()
  retiros_pendientes = WithdrawalRequest.query.filter_by(
      status='Pendiente'
  ).all()
  return render_template_string(
      MAIN_HTML,
      animalitos=ANIMALITOS,
      validas=validas_list,
      acum=acum,
      historial=historial,
      usuarios_lista=usuarios_lista,
      recargas_pendientes=recargas_pendientes,
      retiros_pendientes=retiros_pendientes,
      ganadores=None,
      financiero=None,
  )


@app.route('/solicitar_recarga', methods=['POST'])
@login_required
def solicitar_recarga():
  try:
    amount = float(request.form.get('amount'))
  except ValueError:
    return redirect(url_for('home'))
  bank = request.form.get('bank')
  reference = request.form.get('reference')
  if amount > 1000:
    return redirect(url_for('home'))
  nueva_recarga = RechargeRequest(
      user_id=current_user.id, amount=amount, bank=bank, reference=reference
  )
  db.session.add(nueva_recarga)
  db.session.commit()
  return redirect(url_for('home'))


@app.route('/aprobar_recarga/<int:id>', methods=['POST'])
@login_required
def aprobar_recarga(id):
  if current_user.role != 'admin':
    return redirect(url_for('home'))
  recarga = RechargeRequest.query.get(id)
  if recarga and recarga.status == 'Pendiente':
    recarga.status = 'Aprobado'
    cliente = User.query.get(recarga.user_id)
    if cliente:
      cliente.balance += recarga.amount
    db.session.commit()
  return redirect(url_for('home'))


# <-- NUEVO: Ruta para procesar la solicitud de retiro del usuario
@app.route('/solicitar_retiro', methods=['POST'])
@login_required
def solicitar_retiro():
  try:
    amount = float(request.form.get('amount'))
  except ValueError:
    return redirect(url_for('home'))

  bank = request.form.get('bank')
  phone = request.form.get('phone')
  ci = request.form.get('ci')

  if amount <= 0 or current_user.balance < amount:
    return redirect(url_for('home'))

  # Descuenta inmediatamente del saldo para evitar doble gasto
  current_user.balance -= amount

  nuevo_retiro = WithdrawalRequest(
      user_id=current_user.id,
      amount=amount,
      bank=bank,
      phone=phone,
      ci=ci,
      status='Pendiente',
  )
  db.session.add(nuevo_retiro)
  db.session.commit()
  return redirect(url_for('home'))


# <-- NUEVO: Ruta para que el admin apruebe el Pago Móvil físico
@app.route('/aprobar_retiro/<int:id>', methods=['POST'])
@login_required
def aprobar_retiro(id):
  if current_user.role != 'admin':
    return redirect(url_for('home'))
  retiro = WithdrawalRequest.query.get(id)
  if retiro and retiro.status == 'Pendiente':
    retiro.status = 'Pagado'
    db.session.commit()
  return redirect(url_for('home'))


@app.route('/crear_usuario', methods=['POST'])
@login_required
def crear_usuario():
  if current_user.role != 'admin':
    return redirect(url_for('home'))
  nuevo_user = request.form.get('nuevo_user')
  nuevo_pass = request.form.get('nuevo_pass')
  if User.query.filter_by(username=nuevo_user).first():
    return redirect(url_for('home'))
  user = User(
      username=nuevo_user,
      password_hash=generate_password_hash(nuevo_pass),
      role='vendedor',
  )
  db.session.add(user)
  db.session.commit()
  return redirect(url_for('home'))


@app.route('/eliminar_usuario/<int:id>', methods=['POST'])
@login_required
def eliminar_usuario(id):
  if current_user.role != 'admin':
    return redirect(url_for('home'))
  user = User.query.get(id)
  if user and user.username != 'admin':
    db.session.delete(user)
    db.session.commit()
  return redirect(url_for('home'))


@app.route('/vender', methods=['POST'])
@login_required
def vender():
  if current_user.role not in ['admin', 'vendedor', 'cliente']:
    return redirect(url_for('home'))

  validas_list = [
      (1, '1:00 PM'),
      (2, '2:00 PM'),
      (3, '3:00 PM'),
      (4, '4:00 PM'),
      (5, '5:00 PM'),
      (6, '6:00 PM'),
  ]
  acum = Acumulado.query.first()
  historial = Historial.query.order_by(Historial.id.desc()).all()
  usuarios_lista = User.query.all()
  recargas_pendientes = RechargeRequest.query.filter_by(
      status='Pendiente'
  ).all()
  retiros_pendientes = WithdrawalRequest.query.filter_by(
      status='Pendiente'
  ).all()

  loteria = request.form.get('loteria')
  cliente = request.form.get('cliente')
  telefono = request.form.get('telefono')

  fecha_emision = (datetime.now() - timedelta(hours=4)).strftime(
      '%d/%m/%Y %I:%M %p'
  )

  while True:
    codigo_ticket = generar_codigo_ticket()
    if not Boleto.query.filter_by(codigo_ticket=codigo_ticket).first():
      break

  combinaciones = 1
  cuadro_res = {}
  error = False

  for i in range(1, 7):
    sel = request.form.getlist(f'val_{i}')
    if not sel:
      error = True
      break
    cuadro_res[str(i)] = sel
    combinaciones *= len(sel)

  pote_3 = request.form.get('pote_fijo_3')
  pote_6 = request.form.get('pote_fijo_6')

  detalle_validas = ''
  if not error:
    for i in range(1, 7):
      sel = cuadro_res[str(i)]
      nombres_animales = [f'{k} - {ANIMALITOS.get(k)}' for k in sel]
      detalle_validas += (
          f"  • Válida {i} ({validas_list[i-1][1]}):"
          f" {', '.join(nombres_animales)}\n"
      )

  monto_total = combinaciones * PRECIO_POR_COMBINACION

  if error or not pote_3 or not pote_6:
    ticket_res = '⚠️ Error: Faltan marcar válidas o potes fijos.'
  elif current_user.balance < monto_total:
    ticket_res = '⚠️ Error: Saldo insuficiente en tu billetera.'
  else:
    current_user.balance -= monto_total
    comision_vendedor = monto_total * 0.10
    vendedor_a_acreditar = current_user.id

    if current_user.role == 'vendedor':
      current_user.commission_earned += comision_vendedor

    nuevo_boleto = Boleto(
        codigo_ticket=codigo_ticket,
        cliente=cliente,
        telefono=telefono if telefono else 'N/A',
        loteria=loteria,
        vendedor_id=vendedor_a_acreditar,
        cuadro_json=json.dumps(cuadro_res),
        pote_3=pote_3,
        pote_6=pote_6,
        monto=monto_total,
    )
    db.session.add(nuevo_boleto)
    db.session.commit()

    ticket_res = f"""🧾 LA RINCONADA ORIENTAL DE LA SUERTE
🔑 CÓDIGO: {codigo_ticket}
📅 Fecha: {fecha_emision}
🎰 Lotería: {loteria.upper()}
👤 Cliente: {cliente}
📱 Teléfono: {telefono if telefono else 'N/A'}
🏷️ Registrado por: {current_user.username}
----------------------------------------
📋 JUGADA DE VÁLIDAS:
{detalle_validas}----------------------------------------
🔥 POTE FIJO:
  • Válida 3: {pote_3} - {ANIMALITOS.get(pote_3)}
  • Válida 6: {pote_6} - {ANIMALITOS.get(pote_6)}
----------------------------------------
📊 Combinaciones: {combinaciones}
💵 TOTAL PAGADO: {monto_total:.2f} Bs.
----------------------------------------
✅ Válido únicamente para el sorteo del día."""

  return render_template_string(
      MAIN_HTML,
      animalitos=ANIMALITOS,
      validas=validas_list,
      ticket=ticket_res,
      acum=acum,
      historial=historial,
      usuarios_lista=usuarios_lista,
      recargas_pendientes=recargas_pendientes,
      retiros_pendientes=retiros_pendientes,
      ganadores=None,
      financiero=None,
  )


@app.route('/escrutar', methods=['POST'])
@login_required
def escrutar():
  if current_user.role != 'admin':
    return redirect(url_for('home'))

  validas_list = [
      (1, '1:00 PM'),
      (2, '2:00 PM'),
      (3, '3:00 PM'),
      (4, '4:00 PM'),
      (5, '5:00 PM'),
      (6, '6:00 PM'),
  ]
  resultados = {str(i): request.form.get(f'res_val_{i}') for i in range(1, 7)}

  boletos = Boleto.query.all()
  acum_anterior = Acumulado.query.first()

  total_ventas = sum(b.monto for b in boletos)
  ganancia_banca = total_ventas * 0.30
  pozo_hoy = total_ventas * 0.70

  pago_6_hoy = pozo_hoy * 0.50
  pago_5_hoy = pozo_hoy * 0.20
  pago_4_hoy = pozo_hoy * 0.10
  pago_pote_hoy = pozo_hoy * 0.20

  pozo_6_total = acum_anterior.acum_6 + pago_6_hoy
  pozo_5_total = acum_anterior.acum_5 + pago_5_hoy
  pozo_4_total = acum_anterior.acum_4 + pago_4_hoy
  pozo_pote_total = acum_anterior.acum_pote + pago_pote_hoy

  # Contar ganadores por categoría para repartir el pozo proporcionalmente si hay varios
  ganadores_6 = [
      b
      for b in boletos
      if sum(
          1
          for i in range(1, 7)
          if resultados[str(i)] == json.loads(b.cuadro_json)[str(i)]
      )
      == 6
  ]
  ganadores_5 = [
      b
      for b in boletos
      if sum(
          1
          for i in range(1, 7)
          if resultados[str(i)] == json.loads(b.cuadro_json)[str(i)]
      )
      == 5
  ]
  ganadores_4 = [
      b
      for b in boletos
      if sum(
          1
          for i in range(1, 7)
          if resultados[str(i)] == json.loads(b.cuadro_json)[str(i)]
      )
      == 4
  ]
  ganadores_pote = [
      b for b in boletos if b.pote_3 == resultados['3'] and b.pote_6 == resultados['6']
  ]

  premio_por_6 = pozo_6_total / len(ganadores_6) if ganadores_6 else 0
  premio_por_5 = pozo_5_total / len(ganadores_5) if ganadores_5 else 0
  premio_por_4 = pozo_4_total / len(ganadores_4) if ganadores_4 else 0
  premio_por_pote = pozo_pote_total / len(ganadores_pote) if ganadores_pote else 0

  ganadores_resumen = []

  # Procesar ganadores y abonar al balance del usuario si coincide el nombre con un usuario registrado
  def procesar_premio_lista(lista_boletos, monto_premio_unitario, tipo_texto):
    for b in lista_boletos:
      vendedor = User.query.get(b.vendedor_id)
      vendedor_nombre = vendedor.username if vendedor else 'Desconocido'

      # Buscar si el cliente tiene cuenta de usuario para abonarle el saldo automáticamente
      user_cliente = User.query.filter_by(username=b.cliente).first()
      if user_cliente:
        user_cliente.balance += monto_premio_unitario

      ganadores_resumen.append({
          'codigo': b.codigo_ticket,
          'cliente': b.cliente,
          'telefono': b.telefono,
          'loteria': b.loteria,
          'vendedor': vendedor_nombre,
          'tipo': tipo_texto,
          'monto_premio': monto_premio_unitario,
      })

  procesar_premio_lista(
      ganadores_6,
      pozo_6_total if ganadores_6 else 0,
      '🥇 Primer Premio (6 Aciertos)',
  )
  procesar_premio_lista(
      ganadores_5,
      pozo_5_total / len(ganadores_5) if ganadores_5 else 0,
      '🥈 Segundo Premio (5 Aciertos)',
  )
  procesar_premio_lista(
      ganadores_4,
      pozo_4_total / len(ganadores_4) if ganadores_4 else 0,
      '🥉 Tercer Premio (4 Aciertos)',
  )
  procesar_premio_lista(
      ganadores_pote,
      pozo_pote_total / len(ganadores_pote) if ganadores_pote else 0,
      '🔥 Pote Fijo',
  )

  acum_anterior.acum_6 = 0.0 if ganadores_6 else pozo_6_total
  acum_anterior.acum_5 = 0.0 if ganadores_5 else pozo_5_total
  acum_anterior.acum_4 = 0.0 if ganadores_4 else pozo_4_total
  acum_anterior.acum_pote = 0.0 if ganadores_pote else pozo_pote_total

  total_ganadores_hoy = (
      len(ganadores_6)
      + len(ganadores_5)
      + len(ganadores_4)
      + len(ganadores_pote)
  )
  ganadores_str = (
      f'🎉 {total_ganadores_hoy} ganador(es)'
      if total_ganadores_hoy > 0
      else '❌ Pasa a Acumulado'
  )

  fecha_historial = (datetime.now() - timedelta(hours=4)).strftime(
      '%d/%m/%Y %I:%M %p'
  )

  registro_dia = Historial(
      fecha=fecha_historial,
      ventas=total_ventas,
      ganancia=ganancia_banca,
      premios=pozo_hoy,
      ganadores_txt=ganadores_str,
  )
  db.session.add(registro_dia)

  Boleto.query.delete()
  db.session.commit()

  financiero = {
      'total_ventas': total_ventas,
      'ganancia_banca': ganancia_banca,
      'pozo_hoy': pozo_hoy,
  }

  historial = Historial.query.order_by(Historial.id.desc()).all()
  usuarios_lista = User.query.all()
  recargas_pendientes = RechargeRequest.query.filter_by(
      status='Pendiente'
  ).all()
  retiros_pendientes = WithdrawalRequest.query.filter_by(
      status='Pendiente'
  ).all()

  return render_template_string(
      MAIN_HTML,
      animalitos=ANIMALITOS,
      validas=validas_list,
      financiero=financiero,
      ganadores=ganadores_resumen,
      acum=acum_anterior,
      historial=historial,
      usuarios_lista=usuarios_lista,
      recargas_pendientes=recargas_pendientes,
      retiros_pendientes=retiros_pendientes,
  )


@app.route('/reset', methods=['POST'])
@login_required
def reset():
  if current_user.role == 'admin':
    Boleto.query.delete()
    Historial.query.delete()
    RechargeRequest.query.delete()
    WithdrawalRequest.query.delete()
    acum = Acumulado.query.first()
    if acum:
      acum.acum_6 = 0
      acum.acum_5 = 0
      acum.acum_4 = 0
      acum.acum_pote = 0
    db.session.commit()
  return redirect(url_for('home'))


with app.app_context():
  db.create_all()
  if not User.query.filter_by(username='admin').first():
    admin_user = User(
        username='admin',
        password_hash=generate_password_hash('rinconada2026'),
        role='admin',
    )
    db.session.add(admin_user)
    db.session.commit()

if __name__ == '__main__':
  app.run(host='127.0.0.1', port=5000)
