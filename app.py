from datetime import datetime
from flask import Flask, flash, redirect, render_template_string, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_rinconada_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rinconada.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# --- MODELOS DE LA BASE DE DATOS ---
class User(UserMixin, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(150), unique=True, nullable=False)
  password = db.Column(db.String(150), nullable=False)
  role = db.Column(
      db.String(50), nullable=False
  )  # 'admin', 'vendedor', 'cliente'
  balance = db.Column(
      db.Float, default=0.0
  )  # Billetera o saldo disponible
  commission_earned = db.Column(
      db.Float, default=0.0
  )  # Comisiones acumuladas (10% para vendedores)


class RechargeRequest(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
  amount = db.Column(db.Float, nullable=False)
  reference = db.Column(db.String(100), nullable=False)
  bank = db.Column(db.String(100), nullable=False)
  status = db.Column(
      db.String(20), default='Pendiente'
  )  # Pendiente, Aprobado
  date = db.Column(db.DateTime, default=datetime.utcnow)
  user = db.relationship('User', backref=db.backref('recharges', lazy=True))


class Ticket(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
  seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
  total_amount = db.Column(db.Float, nullable=False)
  commission = db.Column(db.Float, default=0.0)  # El 10% del vendedor
  status = db.Column(db.String(20), default='Activo')
  date = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
  return User.query.get(int(user_id))


# --- RUTAS Y LÓGICA DEL SISTEMA ---


@app.route('/')
def index():
  return render_template_string(
      '<h1>Bienvenido a La Rinconada Oriental de la Suerte</h1>'
      '{% if current_user.is_authenticated %}'
      '<p>Hola, {{ current_user.username }} | Saldo: {{ current_user.balance'
      ' }} Bs</p>'
      '<a href="{{ url_for(\'perfil\') }}">Mi Perfil / Recargar</a> | '
      '<a href="{{ url_for(\'crear_jugada\') }}">Hacer Jugada</a> | '
      '{% if current_user.role == "admin" %}<a'
      ' href="{{ url_for(\'admin_panel\') }}">Panel Admin</a> | {% endif %}'
      '<a href="{{ url_for(\'logout\') }}">Salir</a>'
      '{% else %}'
      '<a href="{{ url_for(\'login\') }}">Iniciar Sesión</a>'
      '{% endif %}'
  )


@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    user = User.query.filter_by(username=request.form.get('username')).first()
    if user and user.password == request.form.get('password'):
      login_user(user)
      return redirect(url_for('index'))
    flash('Credenciales incorrectas', 'danger')
  return render_template_string(
      '<form method="POST"><h2>Login</h2><input type="text" name="username"'
      ' placeholder="Usuario" required><input type="password" name="password"'
      ' placeholder="Contraseña" required><button'
      ' type="submit">Entrar</button></form>'
  )


@app.route('/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('index'))


# 1. SOLICITUD DE RECARGA (Mínimo 1,000 Bs)
@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
  if request.method == 'POST':
    try:
      amount = float(request.form.get('amount'))
    except ValueError:
      flash('Monto inválido.', 'danger')
      return redirect(url_for('perfil'))

    reference = request.form.get('reference')
    bank = request.form.get('bank')

    if amount < 1000:
      flash(
          'El monto mínimo de recarga es de 1,000 Bs.', 'danger'
      )  # Límite aplicado
      return redirect(url_for('perfil'))

    nueva_recarga = RechargeRequest(
        user_id=current_user.id, amount=amount, reference=reference, bank=bank
    )
    db.session.add(nueva_recarga)
    db.session.commit()
    flash(
        'Solicitud de recarga enviada con éxito. Esperando aprobación del'
        ' administrador.',
        'success',
    )
    return redirect(url_for('perfil'))

  mis_recargas = RechargeRequest.query.filter_by(
      user_id=current_user.id
  ).all()
  return render_template_string(
      '<h2>Mi Perfil</h2>'
      '<p>Usuario: {{ current_user.username }}</p>'
      '<p><b>Saldo Actual: {{ current_user.balance }} Bs</b></p>'
      '<hr>'
      '<h3>Solicitar Recarga (Mínimo 1,000 Bs)</h3>'
      '<form method="POST">'
      '<input type="number" step="0.01" name="amount" placeholder="Monto (Min'
      ' 1000)" required><br>'
      '<input type="text" name="reference" placeholder="Nro de Referencia"'
      ' required><br>'
      '<input type="text" name="bank" placeholder="Banco Emisor" required><br>'
      '<button type="submit">Enviar Solicitud</button>'
      '</form>'
      '<hr>'
      '<a href="{{ url_for(\'index\') }}">Volver al Inicio</a>'
  )


# 2. PANEL DE ADMIN PARA APROBAR RECARGAS Y ACREDITAR SALDO
@app.route('/admin', methods=['GET'])
@login_required
def admin_panel():
  if current_user.role != 'admin':
    return redirect(url_for('index'))

  pendientes = RechargeRequest.query.filter_by(status='Pendiente').all()
  return render_template_string(
      '<h2>Panel de Administración - Recargas Pendientes</h2>'
      '<table border="1"><tr><th>Usuario</th><th>Monto</th><th>Banco</th><th>Referencia</th><th>Acción</th></tr>'
      '{% for r in pendientes %}'
      '<tr>'
      '<td>{{ r.user.username }}</td>'
      '<td>{{ r.amount }} Bs</td>'
      '<td>{{ r.bank }}</td>'
      '<td>{{ r.reference }}</td>'
      '<td>'
      '<form'
      ' action="{{ url_for(\'aprobar_recarga\','
      ' recarga_id=r.id) }}"'
      ' method="POST"><button type="submit">Aprobar y'
      ' Acreditar</button></form>'
      '</td>'
      '</tr>'
      '{% endfor %}'
      '</table>'
      '<br><a href="{{ url_for(\'index\') }}">Volver al Inicio</a>'
  )


@app.route('/admin/aprobar/<int:recarga_id>', methods=['POST'])
@login_required
def aprobar_recarga(recarga_id):
  if current_user.role != 'admin':
    return redirect(url_for('index'))

  recarga = RechargeRequest.query.get_or_404(recarga_id)
  if recarga.status == 'Pendiente':
    recarga.status = 'Aprobado'
    # Suma automática del dinero a la billetera del usuario
    cliente = User.query.get(recarga.user_id)
    cliente.balance += recarga.amount
    db.session.commit()
    flash(
        f'Recarga de {recarga.amount} Bs aprobada y sumada al saldo de'
        f' {cliente.username}.',
        'success',
    )

  return redirect(url_for('admin_panel'))


# 3. CREAR JUGADA (Descuenta saldo y calcula automáticamente el 10% al vendedor)
@app.route('/crear-jugada', methods=['GET', 'POST'])
@login_required
def crear_jugada():
  costo_jugada = 100.0  # Costo fijo de ejemplo por ticket

  if request.method == 'POST':
    if current_user.balance < costo_jugada:
      flash(
          'Saldo insuficiente en tu billetera. Por favor recarga para jugar.',
          'danger',
      )
      return redirect(url_for('perfil'))

    # Descontar saldo al cliente
    current_user.balance -= costo_jugada

    # Calcular el 10% de comisión si la jugada la registra un Vendedor
    comision = costo_jugada * 0.10
    vendedor_id = request.form.get('seller_id')

    if vendedor_id:
      vendedor = User.query.get(vendedor_id)
      if vendedor and vendedor.role == 'vendedor':
        vendedor.commission_earned += comision

    nuevo_ticket = Ticket(
        user_id=current_user.id,
        seller_id=vendedor_id if vendedor_id else None,
        total_amount=costo_jugada,
        commission=comision,
    )

    db.session.add(nuevo_ticket)
    db.session.commit()

    flash(
        f'¡Jugada creada con éxito! Se descontaron {costo_jugada} Bs de tu'
        ' saldo.',
        'success',
    )
    return redirect(url_for('index'))

  vendedores = User.query.filter_by(role='vendedor').all()
  return render_template_string(
      '<h2>Realizar Jugada</h2>'
      '<p>Costo del ticket: {{ costo }} Bs | Tu saldo disponible: {{'
      ' current_user.balance }} Bs</p>'
      '<form method="POST">'
      '<label>Vendedor (Opcional, si te atiende una taquilla):</label><br>'
      '<select name="seller_id">'
      '<option value="">-- Jugada directa online --</option>'
      '{% for v in vendedores %}'
      '<option value="{{ v.id }}">{{ v.username }}</option>'
      '{% endfor %}'
      '</select><br><br>'
      '<button type="submit">Comprar Ticket</button>'
      '</form>'
      '<br><a href="{{ url_for(\'index\') }}">Volver al Inicio</a>',
      costo=costo_jugada,
  )


if __name__ == '__main__':
  with app.app_context():
    db.create_all()
    # Crear un admin por defecto si no existe
    if not User.query.filter_by(username='admin').first():
      admin_user = User(
          username='admin', password='rinconada2026', role='admin', balance=0.0
      )
      db.create_all()
      # Nota: Asegúrate de registrar los usuarios iniciales o usar tu script de creación
  app.run(debug=True)
