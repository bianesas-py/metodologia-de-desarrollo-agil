-- ==========================================
-- ESTRUCTURA DE TABLAS PARA SQLITE
-- ==========================================

DROP TABLE IF EXISTS detalles_ventas;
DROP TABLE IF EXISTS simulacion_tarjeta;
DROP TABLE IF EXISTS galeria_producto;
DROP TABLE IF EXISTS venta;
DROP TABLE IF EXISTS carrito;
DROP TABLE IF EXISTS producto;
DROP TABLE IF EXISTS cliente;

CREATE TABLE cliente (
    rut_cliente TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    apellido TEXT NOT NULL,
    correo_electronico TEXT
);

CREATE TABLE producto (
    id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    precio REAL NOT NULL, 
    stock INTEGER NOT NULL,
    descripcion TEXT
);

CREATE TABLE galeria_producto (
    id_archivo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL,
    ruta_archivo TEXT NOT NULL, 
    tipo_archivo TEXT NOT NULL,  
    FOREIGN KEY (id_producto) REFERENCES producto(id_producto)
);

CREATE TABLE carrito (
    id_carrito INTEGER PRIMARY KEY AUTOINCREMENT,
    rut_cliente TEXT NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    FOREIGN KEY (rut_cliente) REFERENCES cliente(rut_cliente),
    FOREIGN KEY (id_producto) REFERENCES producto(id_producto)
);

CREATE TABLE venta (
    id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
    rut_cliente TEXT NOT NULL,
    fecha TEXT DEFAULT CURRENT_TIMESTAMP,
    subtotal REAL,         
    descuento REAL DEFAULT 0, 
    iva REAL,              
    total REAL,           
    FOREIGN KEY (rut_cliente) REFERENCES cliente(rut_cliente)
);

CREATE TABLE simulacion_tarjeta (
    id_tarjeta INTEGER PRIMARY KEY AUTOINCREMENT,
    id_venta INTEGER NOT NULL,
    monto_pagar REAL NOT NULL,
    tipo_tarjeta TEXT NOT NULL,           
    ultimos_cuatro_digitos TEXT NOT NULL,
    estado_pago TEXT NOT NULL,            
    motivo_rechazo TEXT,          
    fecha_pago TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_venta) REFERENCES venta(id_venta)
);

CREATE TABLE detalles_ventas (
    id_detalles_ven INTEGER PRIMARY KEY AUTOINCREMENT,
    id_venta INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario REAL,   
    FOREIGN KEY (id_venta) REFERENCES venta(id_venta),
    FOREIGN KEY (id_producto) REFERENCES producto(id_producto)
);

