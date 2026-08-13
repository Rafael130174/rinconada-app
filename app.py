import os
import json
import webbrowser
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash
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

# --- MODELOS DE BASE DE DATOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='vendedor')  # 'admin' o 'vendedor'

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

# --- PLANTILLAS HTML ---
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acceso - La Rinconada Oriental de la Suerte</title>
    <style>
        body { font-family: sans-serif; background: #1a73e8; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); width: 90%; max-width: 360px; text-align: center; }
        h2 { color: #1a73e8; margin-bottom: 20px; font-size: 20px; }
        input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 15px; }
        button { background: #28a745; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .error { color: red; font-size: 13px; margin-bottom: 10px; }
        .back-link { display: block; margin-top: 15px; color: #1a73e8; text-decoration: none; font-size: 13px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>🏇 LA RINCONADA ORIENTAL</h2>
        <p style="font-size: 13px; color: #666;">Ingreso para Vendedores y Admin</p>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Usuario" required>
            <input type="password" name="password" placeholder="Contraseña" required>
            <button type="submit">Entrar al Sistema</button>
        </form>
        <a href="/" class="back-link">← Volver al Portal Público</a>
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
        .header-app h1 { margin: 0; font-size: 20px; text-transform: uppercase; }
        .user-bar { background: #ffffff; max-width: 500px; margin: 10px auto; padding: 8px 15px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; font-size: 13px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
        .card { background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); max-width: 500px; margin: auto; margin-bottom: 20px; }
        h2, h3, h4 { color: #1a73e8; text-align: center; margin-top: 5px; }
        label { font-weight: bold; display: block; margin-top: 10px; font-size: 14px; }
        input[type="text"], select { width: 100%; padding: 10px; margin-top: 4px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 15px; }
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
            <span>👤 Usuario: <b>{{ current_user.username }}</b> ({{ current_user.role.upper() }})</span>
            <a href="/logout" style="color: #d93025; font-weight: bold; text-decoration: none;">Cerrar Sesión</a>
        {% else %}
            <span>🌐 Modo: <b>PÚBLICO / CLIENTE</b></span>
            <a href="/login" style="color: #1a73e8; font-weight: bold; text-decoration: none;">Acceso Vendedores / Admin →</a>
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
            <form method="POST" action="/reset" style="margin:0;" onsubmit="return confirm('¿Seguro que deseas reiniciar el acumulado e historial?');">
                <button type="submit" class="btn-reset">🔄 Reiniciar Sistema General a 0 Bs.</button>
            </form>
            {% endif %}
        </div>

        {% if current_user.is_authenticated %}
        <h2>🎟️ Registrador de Tickets (Vendedor)</h2>
        <form method="POST" action="/vender">
            <label>Lotería:</label>
            <select name="loteria">
                <option value="Loto Activo">Loto Activo</option>
                <option value="La Granjita">La Granjita</option>
                <option value="Lotto Rey">Lotto Rey</option>
            </select>

            <label>Nombre del Cliente:</label>
            <input type="text" name="cliente" required placeholder="Ej: Juan Pérez">

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

            <button type="submit" class="btn">🎟️ Generar Ticket</button>
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
        <div style="text-align: center; padding: 20px 0;">
            <h3 style="color: #1a73e8;">📢 ¡Bienvenido a La Rinconada Oriental!</h3>
            <p style="font-size: 14px; color: #555;">Consulta aquí el gran pozo acumulado diario y solicita tus jugadas dirigiéndote a cualquiera de nuestros vendedores autorizados.</p>
        </div>
        {% endif %}
    </div>

    <!-- RESULTADOS Y GANADORES (VISIBLES SEGÚN EL ROL) -->
    {% if ganadores is not none %}
    <div class="card" style="border: 2px solid #28a745;">
        <h3 style="color: #28a745;">🎉 Resultados de la Jornada</h3>
        
        {% if current_user.is_authenticated and current_user.role == 'admin' and financiero %}
        <div class="reporte-box">
            <h4 style="margin: 0 0 10px 0; text-align:center;">📊 Balance General de la Jornada (Admin)</h4>
            <b>💵 Ventas Totales:</b> {{ "%.2f"|format(financiero.total_ventas) }} Bs.<br>
            <b style="color: #28a745;">🏦 Ganancia Banca (30%):</b> {{ "%.2f"|format(financiero.ganancia_banca) }} Bs.<br>
            <b>🎯 Fondo Ingresado a Premios (70%):</b> {{ "%.2f"|format(financiero.pozo_hoy) }} Bs.
            <hr style="border: 0; border-top: 1px solid #aecbfa; margin: 8px 0;">
            <h4 style="margin: 5px 0; text-align:center;">🎁 Reparto de Pozos Disponibles</h4>
            • <b>6 Aciertos Total:</b> {{ "%.2f"|format(financiero.pozo_6_total) }} Bs.<br>
            • <b>5 Aciertos Total:</b> {{ "%.2f"|format(financiero.pozo_5_total) }} Bs.<br>
            • <b>4 Aciertos Total:</b> {{ "%.2f"|format(financiero.pozo_4_total) }} Bs.<br>
            • <b>🔥 Pote Fijo Total:</b> {{ "%.2f"|format(financiero.pozo_pote_total) }} Bs.
        </div>
        {% endif %}

        <h4 style="margin-top: 15px; margin-bottom: 5px;">📋 Tickets Ganadores</h4>
        {% if ganadores %}
            {% for g in ganadores %}
            <div class="winner">
                <b>{{ g.cliente }}</b> ({{ g.telefono }}) - {{ g.loteria }}<br>
                • Premio: <b>{{ g.tipo }}</b>
                {% if current_user.is_authenticated and current_user.role == 'admin' %}
                <br>• Vendedor: <i>{{ g.vendedor }}</i>
                {% endif %}
            </div>
            {% endfor %}
        {% else %}
            <p style="text-align: center; color: #d93025; font-weight: bold; font-size: 14px;">❌ No hubo tickets ganadores en esta jugada. ¡El pozo pasa al acumulado!</p>
        {% endif %}
    </div>
    {% endif %}

    {% if current_user.is_authenticated and current_user.role == 'admin' %}
    <!-- ESCRUTINIO SOLO PARA ADMINISTRADOR -->
    <div class="card" style="border: 2px solid #d93025;">
        <h3 style="color: #d93025;">🏆 Escrutinio y Finanzas (Solo Admin)</h3>
        <form method="POST" action="/escrutar">
            <p style="font-size: 13px; color: #666; text-align: center;">Ingresa los 6 animalitos premiados del día:</p>
            {% for i, hora in validas %}
            <label>Válida {{ i }} ({{ hora }}):</label>
            <select name="res_val_{{ i }}" required>
                <option value="">-- Selecciona ganador --</option>
                {% for k, v in animalitos.items() %}
                <option value="{{ k }}">{{ k }} - {{ v }}</option>
                {% endfor %}
            </select>
            {% endfor %}

            <button type="submit" class="btn btn-resultados">🔍 Cargar Resultados y Procesar</button>
        </form>
    </div>

    <!-- HISTORIAL DIARIO SOLO PARA ADMINISTRADOR -->
    <div class="card" style="border: 1px solid #1a73e8;">
        <h3>📅 Historial de Ventas Diarias</h3>
        {% if historial %}
        <table>
            <thead>
                <tr>
                    <th>Fecha / Hora</th>
                    <th>Venta Total</th>
                    <th>Ganancia (30%)</th>
                    <th>Premios (70%)</th>
                    <th>Resultado</th>
                </tr>
            </thead>
            <tbody>
                {% for item in historial %}
                <tr>
                    <td><b>{{ item.fecha }}</b></td>
                    <td>{{ "%.2f"|format(item.ventas) }} Bs.</td>
                    <td style="color: #28a745; font-weight: bold;">{{ "%.2f"|format(item.ganancia) }} Bs.</td>
                    <td>{{ "%.2f"|format(item.premios) }} Bs.</td>
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

# --- RUTAS ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('home'))
        return render_template_string(LOGIN_HTML, error="Usuario o contraseña incorrectos")
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/')
def home():
    validas_list = [(1, "1:00 PM"), (2, "2:00 PM"), (3, "3:00 PM"), (4, "4:00 PM"), (5, "5:00 PM"), (6, "6:00 PM")]
    acum = Acumulado.query.first()
    if not acum:
        acum = Acumulado(acum_6=0, acum_5=0, acum_4=0, acum_pote=0)
        db.session.add(acum)
        db.session.commit()
    historial = Historial.query.order_by(Historial.id.desc()).all()
    return render_template_string(MAIN_HTML, animalitos=ANIMALITOS, validas=validas_list, acum=acum, historial=historial, ganadores=None, financiero=None)

@app.route('/vender', methods=['POST'])
@login_required
def vender():
    validas_list = [(1, "1:00 PM"), (2, "2:00 PM"), (3, "3:00 PM"), (4, "4:00 PM"), (5, "5:00 PM"), (6, "6:00 PM")]
    acum = Acumulado.query.first()
    historial = Historial.query.order_by(Historial.id.desc()).all()
    
    loteria = request.form.get('loteria')
    cliente = request.form.get('cliente')
    telefono = request.form.get('telefono')
    fecha_emision = datetime.now().strftime("%d/%m/%Y %I:%M %p")
    
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
    
    if error or not pote_3 or not pote_6:
        ticket_res = "⚠️ Error: Faltan marcar válidas o potes fijos."
    else:
        monto_total = combinaciones * PRECIO_POR_COMBINACION
        nuevo_boleto = Boleto(
            cliente=cliente,
            telefono=telefono if telefono else "N/A",
            loteria=loteria,
            vendedor_id=current_user.id,
            cuadro_json=json.dumps(cuadro_res),
            pote_3=pote_3,
            pote_6=pote_6,
            monto=monto_total
        )
        db.session.add(nuevo_boleto)
        db.session.commit()
        
        ticket_res = f"""🧾 LA RINCONADA ORIENTAL DE LA SUERTE
📅 Fecha: {fecha_emision}
🎰 Lotería: {loteria.upper()}
👤 Cliente: {cliente}
📱 Teléfono: {telefono if telefono else 'N/A'}
🏷️ Vendedor: {current_user.username}
----------------------------------------
🔥 POTE FIJO:
  • Válida 3: {pote_3} - {ANIMALITOS.get(pote_3)}
  • Válida 6: {pote_6} - {ANIMALITOS.get(pote_6)}
----------------------------------------
📊 Combinaciones: {combinaciones}
💵 TOTAL A PAGAR: {monto_total:.2f} Bs.
----------------------------------------
✅ Ticket Registrado."""

    return render_template_string(MAIN_HTML, animalitos=ANIMALITOS, validas=validas_list, ticket=ticket_res, acum=acum, historial=historial, ganadores=None, financiero=None)

@app.route('/escrutar', methods=['POST'])
@login_required
def escrutar():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
        
    validas_list = [(1, "1:00 PM"), (2, "2:00 PM"), (3, "3:00 PM"), (4, "4:00 PM"), (5, "5:00 PM"), (6, "6:00 PM")]
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
    
    ganadores = []
    cant_6, cant_5, cant_4, cant_pote = 0, 0, 0, 0

    for b in boletos:
        vendedor = User.query.get(b.vendedor_id)
        vendedor_nombre = vendedor.username if vendedor else "Desconocido"
        
        cuadro = json.loads(b.cuadro_json)
        aciertos = sum(1 for i in range(1, 7) if resultados[str(i)] in cuadro[str(i)])
        
        if aciertos == 6:
            cant_6 += 1
            ganadores.append({"cliente": b.cliente, "telefono": b.telefono, "loteria": b.loteria, "vendedor": vendedor_nombre, "vendedor_id": b.vendedor_id, "tipo": "🥇 Primer Premio (6 Aciertos)"})
        elif aciertos == 5:
            cant_5 += 1
            ganadores.append({"cliente": b.cliente, "telefono": b.telefono, "loteria": b.loteria, "vendedor": vendedor_nombre, "vendedor_id": b.vendedor_id, "tipo": "🥈 Segundo Premio (5 Aciertos)"})
        elif aciertos == 4:
            cant_4 += 1
            ganadores.append({"cliente": b.cliente, "telefono": b.telefono, "loteria": b.loteria, "vendedor": vendedor_nombre, "vendedor_id": b.vendedor_id, "tipo": "🥉 Tercer Premio (4 Aciertos)"})
            
        if b.pote_3 == resultados['3'] and b.pote_6 == resultados['6']:
            cant_pote += 1
            ganadores.append({"cliente": b.cliente, "telefono": b.telefono, "loteria": b.loteria, "vendedor": vendedor_nombre, "vendedor_id": b.vendedor_id, "tipo": "🔥 Pote Fijo"})

    if current_user.role == 'vendedor':
        ganadores_visibles = [g for g in ganadores if g['vendedor_id'] == current_user.id]
    else:
        ganadores_visibles = ganadores

    acum_anterior.acum_6 = 0.0 if cant_6 > 0 else pozo_6_total
    acum_anterior.acum_5 = 0.0 if cant_5 > 0 else pozo_5_total
    acum_anterior.acum_4 = 0.0 if cant_4 > 0 else pozo_4_total
    acum_anterior.acum_pote = 0.0 if cant_pote > 0 else pozo_pote_total
    
    total_ganadores_hoy = cant_6 + cant_5 + cant_4 + cant_pote
    ganadores_str = f"🎉 {total_ganadores_hoy} ganador(es)" if total_ganadores_hoy > 0 else "❌ Pasa a Acumulado"
    
    registro_dia = Historial(
        fecha=datetime.now().strftime("%d/%m/%Y %I:%M %p"),
        ventas=total_ventas,
        ganancia=ganancia_banca,
        premios=pozo_hoy,
        ganadores_txt=ganadores_str
    )
    db.session.add(registro_dia)
    
    Boleto.query.delete()
    db.session.commit()

    financiero = {
        "total_ventas": total_ventas, "ganancia_banca": ganancia_banca, "pozo_hoy": pozo_hoy,
        "pozo_6_total": pozo_6_total, "pozo_5_total": pozo_5_total,
        "pozo_4_total": pozo_4_total, "pozo_pote_total": pozo_pote_total
    }

    historial = Historial.query.order_by(Historial.id.desc()).all()
    return render_template_string(MAIN_HTML, animalitos=ANIMALITOS, validas=validas_list, financiero=financiero, ganadores=ganadores_visibles, acum=acum_anterior, historial=historial)

@app.route('/reset', methods=['POST'])
@login_required
def reset():
    if current_user.role == 'admin':
        Boleto.query.delete()
        Historial.query.delete()
        acum = Acumulado.query.first()
        if acum:
            acum.acum_6 = 0
            acum.acum_5 = 0
            acum.acum_4 = 0
            acum.acum_pote = 0
        db.session.commit()
    return redirect(url_for('home'))

# --- INICIALIZACIÓN DE LA BASE DE DATOS Y USUARIO ADMIN ---
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            password_hash=generate_password_hash('rinconada2026'),
            role='admin'
        )
        db.session.add(admin_user)
        db.session.commit()

if __name__ == '__main__':
    webbrowser.open("http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000)
