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
  role = db.Column(db.String(50), nullable=False)  # 'admin', 'vendedor', 'cliente'
  balance = db.Column(db.Float, default=0.0)
  commission_earned = db.Column(db.Float, default=0.0)


class RechargeRequest(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
  amount = db.Column(db.Float, nullable=False)
  reference = db.Column(db.String(100), nullable=False)
  bank = db.Column(db.String(100), nullable=False)
  status = db.Column(db.String(20), default='Pendiente')
  date = db.Column(db.DateTime, default=datetime.utcnow)
  user = db.relationship('User', backref=db.backref('recharges', lazy=True))


class Ticket(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
  seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
  total_amount = db.Column(db.Float, nullable=False)
  commission = db.Column(db.Float, default=0.0)
  status = db.Column(db.String(20), default='Activo')
  date = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
  return User.query.get(int(user_id))


# --- PLANTILLA BASE CON BOOTSTRAP ---
LAYOUT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>La Rinconada Oriental de la Suerte</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">🐎 La Rinconada Oriental</a>
            <div class="navbar-nav ms-auto">
                {% if current_user.is_authenticated %}
                    <span class="nav-item nav-link text-warning">Saldo: {{ "%.2f"|format(current_user.balance) }} Bs</span>
                    <a class="nav-link" href="{{ url_for('perfil') }}">Mi Perfil / Recargar</a>
                    <a class="nav-link" href="{{ url_for('crear_jugada') }}">Hacer Jugada</a>
                    {% if current_user.role == 'admin' %}
                        <a class="nav-link text-info" href="{{ url_for('admin_panel') }}">Panel Admin</a>
                    {% endif %}
                    <a class="nav-link text-danger" href="{{ url_for('logout') }}">Salir</a>
                {% else %}
                    <a class="nav-link" href="{{ url_for('login') }}">Iniciar Sesión</a>
                {% endif %}
            </div>
        </div>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'danger' else 'success' }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {{ content | safe }}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""


# --- RUTAS Y VISTAS ---


@app.route('/')
def index():
  body = """
    <div class="p-5 mb-4 bg-white rounded-3 shadow-sm text-center">
        <div class="container-fluid py-5">
            <h1 class="display-5 fw-bold text-success">La Rinconada Oriental de la Suerte</h1>
            <p class="col-md-8 fs-4 mx-auto text-muted">Tu sistema de apuestas confiable, rápido y automatizado.</p>
            {% if not current_user.is_authenticated %}
                <a class="btn btn-primary btn-lg" href="/login" role="button">Iniciar Sesión</a>
            {% else %}
                <a class="btn btn-success btn-lg" href="/crear-jugada" role="button">Hacer una Jugada Ahora</a>
            {% endif %}
        </div>
    </div>
    """
  return render_template_string(LAYOUT, content=body)


@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    user = User.query.filter_by(username=request.form.get('username')).first()
    if user and user.password == request.form.get('password'):
      login_user(user)
      return redirect(url_for('index'))
    flash('Usuario o contraseña incorrectos.', 'danger')

  body = """
    <div class="row justify-content-center">
        <div class="col-md-4">
            <div class="card shadow-sm p-4">
                <h3 class="text-center mb-3">Iniciar Sesión</h3>
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Usuario</label>
                        <input type="text" class="form-control" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Contraseña</label>
                        <input type="password" class="form-control" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Entrar</button>
                </form>
            </div>
        </div>
    </div>
    """
  return render_template_string(LAYOUT, content=body)


@app.route('/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('index'))


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
      )  # Límite activo
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

  recargas_html = ''
  for r in mis_recargas:
    badge_color = (
        'warning'
        if r.status == 'Pendiente'
        else ('success' if r.status == 'Aprobado' else 'danger')
    )
    recargas_html += f"""
        <tr>
            <td>{r.amount} Bs</td>
            <td>{r.bank}</td>
            <td>{r.reference}</td>
            <td><span class="badge bg-{badge_color}">{r.status}</span></td>
            <td>{r.date.strftime('%Y-%m-%d %H:%M')}</td>
        </tr>
        """

  body = f"""
    <div class="row">
        <div class="col-md-4 mb-4">
            <div class="card shadow-sm p-4">
                <h4>Mi Cuenta</h4>
                <p>Usuario: <b>{current_user.username}</b></p>
                <div class="alert alert-success text-center">
                    <h5>Saldo Disponible</h5>
                    <h3 class="fw-bold">{current_user.balance} Bs</h3>
                </div>
            </div>
        </div>
        <div class="col-md-8">
            <div class="card shadow-sm p-4 mb-4">
                <h4 class="mb-3 text-primary">Solicitar Recarga (Mínimo 1,000 Bs)</h4>
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Monto a Recargar (Bs)</label>
                        <input type="number" step="0.01" class="form-control" name="amount" placeholder="Ej. 1500" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Banco Emisor</label>
                        <input type="text" class="form-control" name="bank" placeholder="Ej. Banco de Venezuela" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Número de Referencia del Pago</label>
                        <input type="text" class="form-control" name="reference" placeholder="Últimos dígitos o referencia" required>
                    </div>
                    <button type="submit" class="btn btn-success w-100">Enviar Solicitud de Recarga</button>
                </form>
            </div>
            
            <div class="card shadow-sm p-4">
                <h4 class="mb-3">Historial de Mis Recargas</h4>
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr><th>Monto</th><th>Banco</th><th>Referencia</th><th>Estado</th><th>Fecha</th></tr>
                        </thead>
                        <tbody>
                            {recargas_html if recargas_html else '<tr><td colspan="5" class="text-center text-muted">No tienes recargas registradas.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    """
  return render_template_string(LAYOUT, content=body)


@app.route('/admin', methods=['GET'])
@login_required
def admin_panel():
  if current_user.role != 'admin':
    return redirect(url_for('index'))

  pendientes = RechargeRequest.query.filter_by(status='Pendiente').all()
  filas = ''
  for r in pendientes:
    filas += f"""
        <tr>
            <td>{r.user.username}</td>
            <td class="fw-bold text-success">{r.amount} Bs</td>
            <td>{r.bank}</td>
            <td>{r.reference}</td>
            <td>{r.date.strftime('%d/%m/%Y %H:%M')}</td>
            <td>
                <form action="{url_for('aprobar_recarga', recarga_id=r.id)}" method="POST">
                    <button type="submit" class="btn btn-sm btn-success">Aprobar y Acreditar</button>
                </form>
            </td>
        </tr>
        """

  body = f"""
    <div class="card shadow-sm p-4">
        <h2 class="mb-4 text-danger">Panel de Administración - Recargas Pendientes</h2>
        <div class="table-responsive">
            <table class="table table-hover align-middle">
                <thead class="table-dark">
                    <tr><th>Usuario</th><th>Monto</th><th>Banco</th><th>Referencia</th><th>Fecha</th><th>Acción</th></tr>
                </thead>
                <tbody>
                    {filas if filas else '<tr><td colspan="6" class="text-center text-muted py-4">No hay solicitudes de recarga pendientes por aprobar. ¡Todo al día!</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
    """
  return render_template_string(LAYOUT, content=body)


@app.route('/admin/aprobar/<int:recarga_id>', methods=['POST'])
@login_required
def aprobar_recarga(recarga_id):
  if current_user.role != 'admin':
    return redirect(url_for('index'))

  recarga = RechargeRequest.query.get_or_404(recarga_id)
  if recarga.status == 'Pendiente':
    recarga.status = 'Aprobado'
    cliente = User.query.get(recarga.user_id)
    cliente.balance += recarga.amount
    db.session.commit()
    flash(
        f'Recarga de {recarga.amount} Bs aprobada y sumada a la billetera de'
        f' {cliente.username}.',
        'success',
    )

  return redirect(url_for('admin_panel'))


@app.route('/crear-jugada', methods=['GET', 'POST'])
@login_required
def crear_jugada():
  costo_jugada = 100.0

  if request.method == 'POST':
    if current_user.balance < costo_jugada:
      flash(
          'Saldo insuficiente en tu billetera. Por favor recarga para jugar.',
          'danger',
      )
      return redirect(url_for('perfil'))

    current_user.balance -= costo_jugada

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
        f'¡Jugada procesada con éxito! Se descontaron {costo_jugada} Bs de tu'
        ' saldo.',
        'success',
    )
    return redirect(url_for('index'))

  vendedores = User.query.filter_by(role='vendedor').all()
  options_vendedores = ''
  for v in vendedores:
    options_vendedores += f'<option value="{v.id}">{v.username}</option>'

  body = f"""
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card shadow-sm p-4">
                <h3 class="mb-3 text-center">Realizar Jugada</h3>
                <div class="alert alert-info d-flex justify-content-between align-items-center">
                    <span>Costo por Ticket: <b>{costo_jugada} Bs</b></span>
                    <span>Tu Saldo: <b>{current_user.balance} Bs</b></span>
                </div>
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Vendedor (Opcional, si te atiende una taquilla)</label>
                        <select class="form-select" name="seller_id">
                            <option value="">-- Jugada directa online --</option>
                            {options_vendedores}
                        </select>
                    </div>
                    <button type="submit" class="btn btn-primary w-100 btn-lg">Comprar Ticket</button>
                </form>
            </div>
        </div>
    </div>
    """
  return render_template_string(LAYOUT, content=body)


if __name__ == '__main__':
  with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
      admin_user = User(
          username='admin', password='rinconada2026', role='admin', balance=0.0
      )
      db.session.add(admin_user)
      db.session.commit()
  app.run(debug=True)
