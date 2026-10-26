import sqlite3
import unicodedata
import io
import csv
from flask import Flask, render_template, request, redirect, url_for, session, Response

app = Flask(__name__)
app.secret_key = 'llave_secreta_ina_commerce_2026'

# Categorías definidas para el catálogo
CATEGORIAS = ["Accesorios", "Audio", "Baterias Portatiles", "Computación", "Celulares", "Consolas", "Gaming", "Pendrives", "Televisiones", "Tablets", "Wearables (Accesorios vestibles)"]

# -------------------------------------------------------------------
# FUNCIONES DE BÚSQUEDA Y FILTRADO
# -------------------------------------------------------------------
def normalizar(texto):
    """Minúsculas y sin tildes: 'Computación' -> 'computacion'."""
    t = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")

def buscar_por_nombre(productos, texto):
    """Busca coincidencia de todas las palabras ignorando tildes y mayúsculas."""
    palabras = normalizar(texto).split()
    if not palabras:
        return list(productos)
    return [p for p in productos if all(w in normalizar(p['nombre']) for w in palabras)]

def filtrar_y_ordenar(productos, texto="", categoria=None, orden=None):
    """Aplica búsqueda, filtro por categoría y ordenamiento."""
    resultado = buscar_por_nombre(productos, texto)

    if categoria:
        resultado = [p for p in resultado if normalizar(p.get('categoria', '')) == normalizar(categoria)]

    if orden == "precio_desc":
        resultado = sorted(resultado, key=lambda p: round(p['precio'] * (1 - (p.get('descuento', 0) or 0) / 100)), reverse=True)
    elif orden == "precio_asc":
        resultado = sorted(resultado, key=lambda p: round(p['precio'] * (1 - (p.get('descuento', 0) or 0) / 100)))
    elif orden == "nombre":
        resultado = sorted(resultado, key=lambda p: normalizar(p['nombre']))

    return resultado

# -------------------------------------------------------------------
# CONEXIÓN Y BASE DE DATOS
# -------------------------------------------------------------------
def obtener_conexion_db():
    conexion = sqlite3.connect('tienda.db')
    conexion.row_factory = sqlite3.Row
    return conexion

def inicializar_base_de_datos():
    conexion = obtener_conexion_db()
    cursor = conexion.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio INTEGER NOT NULL,
            stock INTEGER DEFAULT 10,
            descuento INTEGER DEFAULT 0,
            en_venta INTEGER DEFAULT 1,
            imagen TEXT,
            video TEXT DEFAULT '',
            descripcion TEXT DEFAULT '',
            categoria TEXT DEFAULT 'Accesorios'
        )
    ''')

    cursor.execute("PRAGMA table_info(productos)")
    columnas = [col['name'] for col in cursor.fetchall()]
    if 'categoria' not in columnas:
        cursor.execute("ALTER TABLE productos ADD COLUMN categoria TEXT DEFAULT 'Accesorios'")

    cursor.execute('SELECT COUNT(*) FROM productos')
    if cursor.fetchone()[0] == 0:
        productos_iniciales = [
            (
                "Carcasa de Celular", 3990, 10, 0, 1,
                "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTVo1jCLqx-kBj6xtY34V_fbkfr5i0ien4fmjLupz10eg&s=10",
                "", "Carcasa de alta protección antigolpes para smartphone.", "Accesorios"
            ),
            (
                "Mando Gamer Inalámbrico DualSense PS5", 45990, 5, 22, 1,
                "https://clsonyb2c.vtexassets.com/arquivos/ids/428974-800-800?v=637363067288170000&width=800&height=800&aspect=true",
                "/static/videos/55678-joystick-playstation-dualsense-ps5-blanco.mp4",
                "Control inalámbrico DualSense PS5 con retroalimentación háptica y gatillos adaptativos.", "Gaming"
            ),
            (
                "Mica de Vidrio Templado", 2490, 15, 0, 1,
                "https://rimage.ripley.cl/home.ripley/Attachment/MKP/6456/MPM00074809454/full_image-1.png",
                "", "Protector de pantalla de vidrio templado 9H resistente a rayaduras.", "Accesorios"
            ),
            (
                "Caja de Herramientas Tech", 12990, 8, 0, 1,
                "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTRJ2PHeDKaqBTCvAw-FMbMH0Kki-XipQGNuTzwG2mhpw9oTB4S_K_w4239&s=10",
                "", "Set completo de herramientas de precisión para electrónica y mantención.", "Computación"
            )
        ]
        cursor.executemany('''
            INSERT INTO productos (nombre, precio, stock, descuento, en_venta, imagen, video, descripcion, categoria)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', productos_iniciales)
        conexion.commit()
    conexion.close()

inicializar_base_de_datos()

@app.context_processor
def inyectar_contador_carrito():
    carrito = session.get('carrito', {})
    total_items = sum(carrito.values())
    return dict(total_items_carrito=total_items)

# -------------------------------------------------------------------
# RUTAS PRINCIPALES DE NAVEGACIÓN
# -------------------------------------------------------------------
@app.route('/')
def inicio():
    busqueda = request.args.get('q', '').strip()
    categoria = request.args.get('categoria', '').strip()
    orden = request.args.get('orden', '').strip()

    conexion = obtener_conexion_db()
    productos_db = conexion.execute('SELECT * FROM productos WHERE en_venta = 1').fetchall()
    conexion.close()

    productos_lista = [dict(p) for p in productos_db]

    productos_filtrados = filtrar_y_ordenar(
        productos_lista,
        texto=busqueda,
        categoria=categoria,
        orden=orden
    )

    return render_template(
        'index.html',
        productos=productos_filtrados,
        busqueda=busqueda,
        categoria_sel=categoria,
        orden=orden,
        categorias=CATEGORIAS
    )

@app.route('/producto/<int:id>')
def detalle_producto(id):
    conexion = obtener_conexion_db()
    producto = conexion.execute('SELECT * FROM productos WHERE id = ?', (id,)).fetchone()
    conexion.close()
    if producto is None:
        return "Producto no encontrado", 404
    return render_template('detalle_producto.html', producto=producto)

@app.route('/mando')
def redireccion_mando():
    return redirect(url_for('detalle_producto', id=2))

# -------------------------------------------------------------------
# AUTENTICACIÓN Y SESIONES
# -------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username and password:
            session['usuario_nombre'] = username
            return redirect(url_for('inicio'))
        else:
            return render_template('login.html', error="Credenciales inválidas. Inténtalo de nuevo.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario_nombre', None)
    return redirect(url_for('inicio'))

@app.route('/login-social/<red>')
def login_social(red):
    session['usuario_nombre'] = f"Usuario_{red.capitalize()}"
    return redirect(url_for('inicio'))

@app.route('/invitado')
def login_invitado():
    session['usuario_nombre'] = "Invitado 👻"
    return redirect(url_for('inicio'))

# -------------------------------------------------------------------
# GESTIÓN DE PRODUCTOS (PUBLICAR CON STOCK Y ELIMINAR)
# -------------------------------------------------------------------
@app.route('/agregar', methods=['POST'])
@app.route('/admin/producto/nuevo', methods=['POST'])
def agregar_producto():
    nombre = request.form.get('nombre')
    precio = request.form.get('precio')
    stock = request.form.get('stock', 10)
    imagen = request.form.get('imagen_url') or request.form.get('imagen') or ''
    descripcion = request.form.get('descripcion', '')
    categoria = request.form.get('categoria', 'Accesorios')

    if nombre and precio:
        conexion = obtener_conexion_db()
        conexion.execute('''
            INSERT INTO productos (nombre, precio, stock, descuento, en_venta, imagen, descripcion, categoria)
            VALUES (?, ?, ?, 0, 1, ?, ?, ?)
        ''', (nombre, int(precio), int(stock), imagen, descripcion, categoria))
        conexion.commit()
        conexion.close()

    return redirect(url_for('inicio'))

@app.route('/eliminar/<int:id>')
def eliminar_producto(id):
    conexion = obtener_conexion_db()
    conexion.execute('DELETE FROM productos WHERE id = ?', (id,))
    conexion.commit()
    conexion.close()
    return redirect(url_for('inicio'))

# -------------------------------------------------------------------
# EXPORTACIÓN DE REPORTES CSV
# -------------------------------------------------------------------
@app.route('/exportar_csv')
@app.route('/ventas.csv')
def exportar_csv():
    conexion = obtener_conexion_db()
    productos = conexion.execute('SELECT * FROM productos').fetchall()
    conexion.close()

    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(['ID', 'Nombre', 'Precio', 'Stock', 'Categoría'])

    for p in productos:
        escritor.writerow([p['id'], p['nombre'], p['precio'], p['stock'], p['categoria']])

    return Response("\ufeff" + salida.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=productos_ina_commerce.csv"})

# -------------------------------------------------------------------
# CARRITO Y PAGO (SUMAR, RESTAR Y LIMITAR STOCK)
# -------------------------------------------------------------------
@app.route('/agregar_al_carrito/<int:producto_id>')
def agregar_al_carrito(producto_id):
    if 'carrito' not in session:
        session['carrito'] = {}
    
    carrito = session['carrito']
    str_id = str(producto_id)
    cantidad_actual = carrito.get(str_id, 0)

    # Validar stock real disponible antes de agregar unidades extras
    conexion = obtener_conexion_db()
    producto = conexion.execute('SELECT stock FROM productos WHERE id = ?', (producto_id,)).fetchone()
    conexion.close()

    if producto and cantidad_actual < producto['stock']:
        carrito[str_id] = cantidad_actual + 1
        session.modified = True

    return redirect(request.referrer or url_for('inicio'))

@app.route('/restar_del_carrito/<int:producto_id>')
def restar_del_carrito(producto_id):
    if 'carrito' in session:
        str_id = str(producto_id)
        if str_id in session['carrito']:
            session['carrito'][str_id] -= 1
            if session['carrito'][str_id] <= 0:
                del session['carrito'][str_id]
            session.modified = True
    return redirect(request.referrer or url_for('ver_carrito'))

@app.route('/eliminar_del_carrito/<int:producto_id>')
def eliminar_del_carrito(producto_id):
    if 'carrito' in session:
        str_id = str(producto_id)
        if str_id in session['carrito']:
            del session['carrito'][str_id]
            session.modified = True
    return redirect(url_for('ver_carrito'))

@app.route('/vaciar_carrito')
def vaciar_carrito():
    session.pop('carrito', None)
    return redirect(url_for('ver_carrito'))

@app.route('/carrito')
def ver_carrito():
    carrito = session.get('carrito', {})
    items_carrito = []
    total_general = 0

    if carrito:
        conexion = obtener_conexion_db()
        ids = list(carrito.keys())
        placeholders = ','.join('?' for _ in ids)
        productos = conexion.execute(f'SELECT * FROM productos WHERE id IN ({placeholders})', ids).fetchall()
        conexion.close()

        for prod in productos:
            cantidad = carrito[str(prod['id'])]
            subtotal = prod['precio'] * cantidad
            total_general += subtotal
            items_carrito.append({
                'id': prod['id'],
                'nombre': prod['nombre'],
                'precio': prod['precio'],
                'stock': prod['stock'],
                'imagen': prod['imagen'],
                'cantidad': cantidad,
                'subtotal': subtotal
            })

    return render_template('carrito.html', items=items_carrito, total=total_general)

@app.route('/pago', methods=['GET', 'POST'])
def simular_pago():
    carrito = session.get('carrito', {})
    if not carrito and request.method == 'GET':
        return redirect(url_for('ver_carrito'))

    if request.method == 'POST':
        numero_tarjeta = request.form.get('numero_tarjeta', '').replace(" ", "")
        titular = request.form.get('titular')
        cvv = request.form.get('cvv')

        if len(numero_tarjeta) < 15 or not cvv or not titular:
            return render_template('pago.html', error="Por favor completa todos los datos de la tarjeta.")

        if numero_tarjeta.endswith('0000') or cvv == '000':
            return render_template('pago_rechazado.html', motivo="Fondos insuficientes o transacción denegada por la entidad bancaria.")

        # Descuenta el stock de la base de datos al confirmar el pago
        conexion = obtener_conexion_db()
        for prod_id_str, cantidad in carrito.items():
            conexion.execute(
                'UPDATE productos SET stock = MAX(0, stock - ?) WHERE id = ?',
                (cantidad, int(prod_id_str))
            )
        conexion.commit()
        conexion.close()

        session.pop('carrito', None)
        return render_template('pago_exitoso.html', titular=titular, tarjeta_oculta=f"**** **** **** {numero_tarjeta[-4:]}")

    return render_template('pago.html')

if __name__ == '__main__':
    app.run(debug=True)