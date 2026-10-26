"""Tienda online - (versión simple en consola, con clases).
Para correrlo:  python tienda_completa.py
"""
import csv
import hashlib
import hmac
import io
import os
import time
import unicodedata
from datetime import date, datetime

IVA = 0.19
TARJETA_APROBADA = "4242424242424242"
TARJETA_RECHAZADA = "4000000000000002"
# El backlog solo muestra "Su pago ha sido rechazado...": completar según ECL-CCC-010.
MSG_RECHAZO = "Su pago ha sido rechazado. Revise los datos de su tarjeta o use otra e intente nuevamente."

UMBRAL_STOCK_BAJO = 5          # avisar cuando queden 5 o menos
MAX_INTENTOS = 3               # intentos de login antes de bloquear
SEGUNDOS_BLOQUEO = 300         # 5 minutos
CATEGORIAS = ["Celulares", "Computación", "Audio", "Accesorios", "Wearables", "Gaming"]  # solo tecnología


def plata(n):
    """Da formato a un precio: 12990 -> $12.990"""
    return "$" + f"{n:,}".replace(",", ".")


def normalizar(texto):
    """Minúsculas y sin tildes: 'Computación' -> 'computacion'."""
    t = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# PRODUCTO
class Producto:
    def __init__(self, id, nombre, precio, stock, descuento=0, en_venta=True, imagen="", categoria=""):
        self.id = id
        self.nombre = nombre
        self.precio = precio          # sin IVA
        self.stock = stock
        self.descuento = descuento    # porcentaje, de 0 a 100
        self.en_venta = en_venta
        self.imagen = imagen          # nombre o ruta del archivo de la imagen
        self.categoria = categoria    # una de CATEGORIAS

    def precio_final(self):
        return round(self.precio * (1 - self.descuento / 100))

    def __str__(self):
        alerta = alerta_stock(self)
        aviso = f"  [{alerta}]" if alerta else ""
        desc = f" (-{self.descuento}%)" if self.descuento else ""
        return (f"{self.id}. {self.nombre} ({self.categoria}) - {plata(self.precio_final())}{desc}"
                f" - stock: {self.stock}{aviso}")


def alerta_stock(producto):
    """'Sin stock' si es 0, aviso de stock bajo si quedan 5 o menos, '' si está normal."""
    if producto.stock < 1:
        return "Sin stock"
    if producto.stock <= UMBRAL_STOCK_BAJO:
        return f"¡Stock bajo! Quedan solo {producto.stock} unidad(es)."
    return ""


# CARRITO
class Carrito:
    def __init__(self):
        self.items = {}   # {producto: cantidad}

    def agregar(self, producto):
        if not producto.en_venta or producto.stock < 1:
            return "Ese producto no está disponible."
        actual = self.items.get(producto, 0)
        if actual >= producto.stock:
            return f"Solo quedan {producto.stock} unidades de {producto.nombre}."
        self.items[producto] = actual + 1
        return f"{producto.nombre} agregado al carrito. {alerta_stock(producto)}".strip()

    def cambiar_cantidad(self, producto, cantidad):
        if producto in self.items and cantidad >= 1:
            self.items[producto] = cantidad

    def eliminar(self, producto):
        self.items.pop(producto, None)

    def aviso(self, producto, cantidad):
        """Devuelve el aviso del producto, o '' si está todo bien."""
        if not producto.en_venta:
            return "Este producto ya no está a la venta. Elimínelo para continuar."
        if producto.stock < 1:
            return "Este producto se quedó sin stock. Elimínelo para continuar."
        if cantidad > producto.stock:
            return f"Solo quedan {producto.stock} unidades. Baje la cantidad para continuar."
        return ""

    def hay_avisos(self):
        return any(self.aviso(p, c) for p, c in self.items.items())

    def totales(self):
        subtotal = sum(p.precio * c for p, c in self.items.items())
        neto = sum(p.precio_final() * c for p, c in self.items.items())
        iva = round(neto * IVA)
        return {"subtotal": subtotal, "descuento": subtotal - neto, "iva": iva, "total": neto + iva}

    def mostrar(self):
        if not self.items:
            print("El carrito está vacío.")
            return
        for p, c in self.items.items():
            print(f"{p.id}. {p.nombre} x{c} = {plata(p.precio_final() * c)}")
            aviso = self.aviso(p, c)
            if aviso:
                print("   AVISO:", aviso)
            elif alerta_stock(p):
                print("   ", alerta_stock(p))
        self.mostrar_totales()

    def mostrar_totales(self):
        t = self.totales()
        print(f"Subtotal: {plata(t['subtotal'])}")
        print(f"Descuento: -{plata(t['descuento'])}")
        print(f"IVA (19%): {plata(t['iva'])}")
        print(f"TOTAL: {plata(t['total'])}")


# TIENDA
class Tienda:
    def __init__(self):
        self.productos = [
            Producto(1, "Audífonos Bluetooth", 24990, 10, categoria="Audio"),
            Producto(2, "Smartphone Galaxy A15", 189990, 4, descuento=10, categoria="Celulares"),
            Producto(3, "Notebook Lenovo IdeaPad", 449990, 0, categoria="Computación"),
            Producto(4, "Mouse inalámbrico", 9990, 25, categoria="Accesorios"),
            Producto(5, "Teclado mecánico", 34990, 5, categoria="Gaming"),
            Producto(6, "Tablet 10 pulgadas", 159990, 6, en_venta=False, categoria="Computación"),
        ]
        self.siguiente_id = 7

    def buscar(self, id):
        for p in self.productos:
            if p.id == id:
                return p
        return None

    def catalogo(self):
        return [p for p in self.productos if p.en_venta]

    def crear(self, datos):
        p = Producto(self.siguiente_id, **datos)
        self.productos.append(p)
        self.siguiente_id += 1
        return p


def validar_producto(nombre, precio, stock, descuento, categoria):
    """Recibe textos. Devuelve (errores, datos). Nombre, precio, stock y categoría son obligatorios.
    La categoría debe ser una de CATEGORIAS (así la tienda solo vende tecnología)."""
    errores = []
    if nombre.strip() == "":
        errores.append("El nombre es obligatorio.")
    if not precio.isdigit() or int(precio) <= 0:
        errores.append("El precio es obligatorio y debe ser un número mayor a 0.")
    if not stock.isdigit():
        errores.append("El stock es obligatorio (número entero, 0 o más).")
    if descuento == "":
        descuento = "0"
    if not descuento.isdigit() or int(descuento) > 100:
        errores.append("El descuento debe estar entre 0 y 100.")
    categoria_ok = next((c for c in CATEGORIAS if normalizar(c) == normalizar(categoria)), None)
    if categoria_ok is None:
        errores.append("La categoría es obligatoria y debe ser tecnológica: " + ", ".join(CATEGORIAS) + ".")
    if errores:
        return errores, None
    return [], {"nombre": nombre.strip(), "precio": int(precio), "stock": int(stock),
                "descuento": int(descuento), "categoria": categoria_ok}


# BÚSQUEDA, FILTRO Y ORDEN
def buscar_por_nombre(productos, texto):
    """Ignora mayúsculas y tildes; todas las palabras escritas deben estar en el nombre
    (en cualquier orden). 'inalambrico mouse' encuentra 'Mouse inalámbrico'."""
    palabras = normalizar(texto).split()
    if not palabras:
        return list(productos)
    return [p for p in productos if all(w in normalizar(p.nombre) for w in palabras)]


def filtrar_y_ordenar(productos, texto="", categoria=None, orden=None):
    """orden: 'precio_desc' (más caro a más barato), 'precio_asc' (más barato a más caro) o 'nombre'."""
    resultado = buscar_por_nombre(productos, texto)
    if categoria:
        resultado = [p for p in resultado if normalizar(p.categoria) == normalizar(categoria)]
    if orden == "precio_desc":
        resultado.sort(key=lambda p: p.precio_final(), reverse=True)
    elif orden == "precio_asc":
        resultado.sort(key=lambda p: p.precio_final())
    elif orden == "nombre":
        resultado.sort(key=lambda p: normalizar(p.nombre))
    return resultado


def productos_con_stock_bajo(productos, incluir_agotados=False):
    return [p for p in productos if p.stock <= UMBRAL_STOCK_BAJO and (p.stock >= 1 or incluir_agotados)]


# LOGIN Y CARRITO DEL USUARIO
class Usuario:
    def __init__(self, nombre, clave):
        self.nombre = nombre.strip()
        self._salt = os.urandom(16)
        self._hash = self._calcular(clave)
        self.carrito = None          # aquí queda vinculado el carrito de este usuario

    def _calcular(self, clave):
        return hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), self._salt, 100_000)

    def verificar(self, clave):
        return hmac.compare_digest(self._hash, self._calcular(clave))


class Autenticador:
    """Registro e inicio de sesión con máximo 3 intentos."""

    def __init__(self, crear_carrito):
        self._crear_carrito = crear_carrito   # la clase Carrito
        self._usuarios = {}
        self._intentos = {}
        self._bloqueado_hasta = {}

    def registrar(self, nombre, clave):
        """Devuelve (usuario o None, mensaje)."""
        llave = nombre.strip().lower()
        if not llave or not clave:
            return None, "Nombre y contraseña son obligatorios."
        if llave in self._usuarios:
            return None, "Ese nombre de usuario ya existe."
        self._usuarios[llave] = Usuario(nombre, clave)
        return self._usuarios[llave], "Usuario registrado."

    def iniciar_sesion(self, nombre, clave, ahora=None):
        """Devuelve (usuario o None, mensaje). Al 3er error se bloquea por 5 minutos."""
        ahora = time.time() if ahora is None else ahora
        llave = nombre.strip().lower()
        hasta = self._bloqueado_hasta.get(llave, 0)
        if ahora < hasta:
            minutos = int((hasta - ahora) // 60) + 1
            return None, f"Cuenta bloqueada por demasiados intentos. Intente en {minutos} minuto(s)."
        if hasta:                                   # el bloqueo ya venció
            self._bloqueado_hasta.pop(llave)
            self._intentos[llave] = 0

        usuario = self._usuarios.get(llave)
        if usuario and usuario.verificar(clave):
            self._intentos[llave] = 0
            if usuario.carrito is None:             # vincula el carrito a la cuenta
                usuario.carrito = self._crear_carrito()
            return usuario, f"Bienvenido, {usuario.nombre}."

        # Mismo mensaje exista o no el usuario, para no revelar cuáles existen.
        self._intentos[llave] = self._intentos.get(llave, 0) + 1
        restantes = MAX_INTENTOS - self._intentos[llave]
        if restantes <= 0:
            self._bloqueado_hasta[llave] = ahora + SEGUNDOS_BLOQUEO
            return None, f"Credenciales inválidas. Cuenta bloqueada por {SEGUNDOS_BLOQUEO // 60} minutos."
        return None, f"Credenciales inválidas. Le quedan {restantes} intento(s)."


# HISTORIAL DE VENTAS Y CSV
COLUMNAS_CSV = ["id_venta", "fecha", "usuario", "productos", "subtotal", "descuento", "iva", "total"]


class Venta:
    def __init__(self, id, usuario, lineas, totales):
        self.id = id
        self.usuario = usuario
        self.lineas = lineas                    # lista de (nombre, cantidad, precio_unitario)
        self.totales = totales                  # dict de Carrito.totales()
        self.fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def a_fila(self):
        detalle = " | ".join(f"{n} x{c}" for n, c, _ in self.lineas)
        return {"id_venta": self.id, "fecha": self.fecha, "usuario": self.usuario, "productos": detalle,
                "subtotal": self.totales["subtotal"], "descuento": self.totales["descuento"],
                "iva": self.totales["iva"], "total": self.totales["total"]}


def registrar_venta(historial, usuario, carrito):
    """Llamar ANTES de vaciar el carrito, cuando el pago fue exitoso."""
    lineas = [(p.nombre, c, p.precio_final()) for p, c in carrito.items.items()]
    venta = Venta(len(historial) + 1, usuario, lineas, carrito.totales())
    historial.append(venta)
    return venta


def _seguro(valor):
    """Evita que Excel ejecute como fórmula un texto que empiece con = + - @."""
    texto = str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@") else texto


def ventas_a_csv(historial):
    """Recibe el historial (lista de Venta o de diccionarios con las mismas columnas) y devuelve el CSV como texto."""
    salida = io.StringIO()
    escritor = csv.DictWriter(salida, fieldnames=COLUMNAS_CSV)
    escritor.writeheader()
    for venta in historial:
        fila = venta.a_fila() if hasattr(venta, "a_fila") else venta
        escritor.writerow({k: _seguro(fila[k]) for k in COLUMNAS_CSV})
    return salida.getvalue()


def exportar_ventas_csv(historial, ruta="ventas.csv"):
    """Crea el archivo .csv (utf-8-sig para que Excel muestre bien las tildes)."""
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        f.write(ventas_a_csv(historial))
    return ruta


# esto hace que el navegador DESCARGUE el archivo:
#
#   from flask import Response
#   @app.route("/ventas.csv")
#   def descargar_ventas():
#       return Response("\ufeff" + ventas_a_csv(historial), mimetype="text/csv",
#                       headers={"Content-Disposition": "attachment; filename=ventas.csv"})


# PAGO
def vencida(vencimiento, hoy=None):
    """True si MM/AA es menor al mes y año actual. None si el formato es inválido."""
    partes = vencimiento.split("/")
    if len(partes) != 2 or not (partes[0].isdigit() and partes[1].isdigit()) or len(partes[1]) != 2:
        return None
    mes, anio = int(partes[0]), 2000 + int(partes[1])
    if mes < 1 or mes > 12:
        return None
    hoy = hoy or date.today()
    return (anio, mes) < (hoy.year, hoy.month)


def validar_tarjeta(titular, numero, vencimiento, cvv, hoy=None):
    """Devuelve (errores, rechazado)."""
    numero = numero.replace(" ", "")
    errores = []
    if titular.strip() == "":
        errores.append("Ingrese el titular.")
    if numero == "":
        errores.append("Ingrese el número de tarjeta.")
    elif numero not in (TARJETA_APROBADA, TARJETA_RECHAZADA):
        errores.append("Use una tarjeta de prueba válida.")
    if vencimiento == "":
        errores.append("Ingrese el vencimiento.")
    elif vencida(vencimiento, hoy) is None:
        errores.append("El vencimiento debe tener formato MM/AA.")
    if cvv == "":
        errores.append("Ingrese el CVV.")
    elif not (cvv.isdigit() and len(cvv) == 3):
        errores.append("El CVV debe tener 3 dígitos.")
    if errores:
        return errores, False
    return [], numero == TARJETA_RECHAZADA or vencida(vencimiento, hoy)


# MENÚS
def pedir_numero(mensaje):
    texto = input(mensaje).strip()
    return int(texto) if texto.isdigit() else None


def elegir_categoria(actual=""):
    """Muestra las categorías y devuelve la elegida (Enter = la actual)."""
    for i, c in enumerate(CATEGORIAS, 1):
        print(f"  {i}) {c}")
    texto = input(f"Categoría (número){' [' + actual + ']' if actual else ''}: ").strip()
    if texto == "":
        return actual
    if texto.isdigit() and 1 <= int(texto) <= len(CATEGORIAS):
        return CATEGORIAS[int(texto) - 1]
    return texto


def ver_catalogo(tienda):
    print("\n--- CATÁLOGO ---")
    for p in tienda.catalogo():
        print(p)


def buscar_productos(tienda):
    print("\n--- BUSCAR / FILTRAR / ORDENAR (Enter = sin filtro) ---")
    texto = input("Nombre contiene: ")
    categoria = elegir_categoria()
    if categoria and normalizar(categoria) not in [normalizar(c) for c in CATEGORIAS]:
        print("Categoría no válida.")
        return
    print("Ordenar: 1) Más caro a más barato  2) Más barato a más caro  3) Nombre")
    orden = {"1": "precio_desc", "2": "precio_asc", "3": "nombre"}.get(input("Orden: ").strip())
    resultados = filtrar_y_ordenar(tienda.catalogo(), texto, categoria, orden)
    print(f"\n{len(resultados)} resultado(s):")
    for p in resultados:
        print(p)


def agregar_al_carrito(tienda, carrito):
    producto = tienda.buscar(pedir_numero("ID del producto: "))
    if producto is None:
        print("No existe ese producto.")
    else:
        print(carrito.agregar(producto))


def modificar_carrito(tienda, carrito):
    producto = tienda.buscar(pedir_numero("ID del producto del carrito: "))
    if producto is None or producto not in carrito.items:
        print("Ese producto no está en el carrito.")
        return
    opcion = input("1) Cambiar cantidad  2) Eliminar: ").strip()
    if opcion == "1":
        cantidad = pedir_numero("Nueva cantidad: ")
        if cantidad:
            carrito.cambiar_cantidad(producto, cantidad)
        else:
            print("Cantidad inválida.")
    elif opcion == "2":
        carrito.eliminar(producto)


def pagar(carrito, usuario, historial):
    if not carrito.items or carrito.hay_avisos():
        print("Revise su carrito antes de pagar (vacío o con avisos).")
        return
    print("\n--- CHECKOUT ---")
    carrito.mostrar()
    print("Tarjetas de prueba: 4242 4242 4242 4242 (aprobada), 4000 0000 0000 0002 (rechazada)")
    while True:
        titular = input("Titular: ")
        numero = input("Número de tarjeta: ")
        vencimiento = input("Vencimiento (MM/AA): ").strip()
        cvv = input("CVV: ").strip()
        errores, rechazado = validar_tarjeta(titular, numero, vencimiento, cvv)
        if errores:
            for e in errores:
                print(" -", e)
        elif rechazado:
            print("\n¡ALERTA!", MSG_RECHAZO, "\n")   # se queda en el checkout
        else:
            break
        if input("¿Reintentar? (s/n): ").lower() != "s":
            return
    registrar_venta(historial, usuario.nombre, carrito)    # antes de vaciar el carrito
    for producto, cantidad in carrito.items.items():
        producto.stock -= cantidad
        if alerta_stock(producto):
            print(f"AVISO ADMIN: {producto.nombre} -> {alerta_stock(producto)}")
    carrito.items.clear()
    print("\n¡Simulación de pago exitosa!")


def panel_interno(tienda, historial):
    while True:
        print("\n--- PANEL INTERNO ---")
        for p in tienda.productos:
            print(p, "| en venta" if p.en_venta else "| oculto", "| imagen:", p.imagen or "-")
        bajos = productos_con_stock_bajo(tienda.productos)
        if bajos:
            print("\nPRODUCTOS CON STOCK BAJO (5 o menos):", ", ".join(p.nombre for p in bajos))
        opcion = input("\n1) Crear  2) Editar  3) Exportar ventas a CSV  4) Volver: ").strip()
        if opcion == "1":
            nombre = input("Nombre: ")
            precio = input("Precio (sin IVA): ")
            stock = input("Stock: ")
            descuento = input("Descuento % (Enter = 0): ")
            categoria = elegir_categoria()
            errores, datos = validar_producto(nombre, precio, stock, descuento, categoria)
            if errores:
                for e in errores:
                    print(" -", e)
                continue
            datos["en_venta"] = input("¿En venta? (s/n): ").lower() == "s"
            datos["imagen"] = input("Archivo de imagen (Enter = ninguna): ").strip()
            producto = tienda.crear(datos)
            print("Creado:", producto)
        elif opcion == "2":
            producto = tienda.buscar(pedir_numero("ID a editar: "))
            if producto is None:
                print("No existe ese producto.")
                continue
            print("(Enter deja el valor actual)")
            nombre = input(f"Nombre [{producto.nombre}]: ") or producto.nombre
            precio = input(f"Precio [{producto.precio}]: ") or str(producto.precio)
            stock = input(f"Stock [{producto.stock}]: ") or str(producto.stock)
            descuento = input(f"Descuento % [{producto.descuento}]: ") or str(producto.descuento)
            categoria = elegir_categoria(producto.categoria)
            errores, datos = validar_producto(nombre, precio, stock, descuento, categoria)
            if errores:
                for e in errores:
                    print(" -", e)
                continue
            producto.nombre, producto.precio = datos["nombre"], datos["precio"]
            producto.stock, producto.descuento = datos["stock"], datos["descuento"]
            producto.categoria = datos["categoria"]
            venta = input(f"¿En venta? (s/n) [{'s' if producto.en_venta else 'n'}]: ").lower()
            if venta in ("s", "n"):
                producto.en_venta = venta == "s"
            imagen = input("Nueva imagen (Enter = igual): ").strip()
            if imagen:
                producto.imagen = imagen
            print("Guardado:", producto)
        elif opcion == "3":
            if not historial:
                print("Todavía no hay ventas para exportar.")
            else:
                ruta = exportar_ventas_csv(historial)
                print(f"Archivo creado: {os.path.abspath(ruta)}  (ábrelo con Excel)")
        elif opcion == "4":
            return


def menu_acceso(auth):
    """Devuelve el usuario que inició sesión, o None si se sale."""
    while True:
        print("\n===== ACCESO =====")
        opcion = input("1) Iniciar sesión  2) Registrarse  0) Salir: ").strip()
        if opcion == "1":
            usuario, mensaje = auth.iniciar_sesion(input("Usuario: "), input("Contraseña: "))
            print(mensaje)
            if usuario:
                return usuario
        elif opcion == "2":
            _, mensaje = auth.registrar(input("Nuevo usuario: "), input("Contraseña: "))
            print(mensaje)
        elif opcion == "0":
            return None


def menu_tienda(tienda, usuario, historial):
    carrito = usuario.carrito          # el carrito pertenece a la cuenta
    while True:
        print(f"\n===== TIENDA TECNOLÓGICA - {usuario.nombre} =====")
        print("1) Ver catálogo   2) Buscar/filtrar/ordenar   3) Agregar al carrito   4) Ver carrito")
        print("5) Cambiar/eliminar del carrito   6) Pagar   7) Panel interno   8) Cerrar sesión")
        opcion = input("Opción: ").strip()
        if opcion == "1":
            ver_catalogo(tienda)
        elif opcion == "2":
            buscar_productos(tienda)
        elif opcion == "3":
            ver_catalogo(tienda)
            agregar_al_carrito(tienda, carrito)
        elif opcion == "4":
            print("\n--- CARRITO ---")
            carrito.mostrar()
        elif opcion == "5":
            modificar_carrito(tienda, carrito)
        elif opcion == "6":
            pagar(carrito, usuario, historial)
        elif opcion == "7":
            panel_interno(tienda, historial)
        elif opcion == "8":
            print("Sesión cerrada.")
            return
        else:
            print("Opción no válida.")


def main():
    tienda = Tienda()
    historial = []
    auth = Autenticador(Carrito)
    auth.registrar("nico", "1234")     # usuario de prueba (borrar al entregar)
    while True:
        usuario = menu_acceso(auth)
        if usuario is None:
            print("¡Hasta luego!")
            break
        menu_tienda(tienda, usuario, historial)


if __name__ == "__main__":
    main()
