# ... (Mantén toda la configuración inicial, clases User, Boleto, etc., igual que antes)

# --- AJUSTE EN LA RUTA DE REGISTRO ---
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            return render_template_string(REGISTRO_HTML, error="El usuario ya existe.")
        
        # Se registra siempre como 'cliente'
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role='cliente' 
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('home'))
    return render_template_string(REGISTRO_HTML)

# --- AJUSTE EN LA RUTA DE VENDER (Lógica de Permisos) ---
@app.route('/vender', methods=['POST'])
@login_required
def vender():
    # AHORA PERMITIMOS QUE ADMIN, VENDEDOR O CLIENTE PUEDAN VENDER/JUGAR
    if current_user.role not in ['admin', 'vendedor', 'cliente']:
        return redirect(url_for('home'))
        
    # ... (El resto de la lógica de guardado sigue igual)
    # IMPORTANTE: Si es cliente, puedes guardar su propio nombre/teléfono automáticamente
    # usando su username, o dejar que el cliente lo llene manualmente como ya hace el formulario.
    
    # ... (código de guardado igual que antes)
    return render_template_string(MAIN_HTML, ...)

# --- AJUSTE EN EL HTML (MAIN_HTML) ---
# Busca la sección donde dice:
# {% if current_user.is_authenticated and current_user.role in ['admin', 'vendedor'] %}
# Y cámbialo por:

"""
        {% if current_user.is_authenticated %}
        <h2>🎟️ Registrador de Tickets</h2>
        <form method="POST" action="/vender">
            <!-- (Tu formulario de jugada aquí) -->
            <!-- ... -->
"""
