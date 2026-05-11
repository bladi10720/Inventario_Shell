# Inventario (Streamlit + Neon)

App web para controlar stock por **entradas** y **salidas diarias**, con **alertas** de bajo stock (stock < 2) y acceso por **PIN**.

## Requisitos
- Python 3.12+
- Una base de datos Postgres (recomendado: Neon)

## Variables de entorno
- `DATABASE_URL`: connection string Postgres (Neon). Debe incluir SSL (ej. `sslmode=require`).
- `PIN_ADMIN`: PIN para rol admin
- `PIN_OPERADOR`: PIN para rol operador

## Roles y PINs adicionales (opcional)

Siempre puedes entrar con `PIN_ADMIN` o `PIN_OPERADOR`. Además, un administrador puede definir **más roles y PINs** en la base de datos: entra con un PIN de admin → menú **Roles y PINs (admin)**. Ahí creas roles (con un *slug* interno que queda en los movimientos para auditoría), marcas si el rol es administrador y asignas PINs por rol. Cada PIN debe ser único en toda la aplicación.

Al arrancar la app se aplican migraciones mínimas en Postgres (tablas `roles` / `role_pins` y relajación de restricciones en `actor_role` si la base ya existía). No sustituye a **Inicializar base de datos** la primera vez: sigue haciendo falta para crear el resto de tablas si el esquema aún no está cargado.

## Ejecutar local
1. Instala dependencias:

```bash
python -m pip install -r requirements.txt
```

2. Exporta variables de entorno (PowerShell):

```powershell
$env:DATABASE_URL="postgresql://..."
$env:PIN_ADMIN="1234"
$env:PIN_OPERADOR="1111"
```

3. Ejecuta Streamlit:

```bash
python -m streamlit run app.py
```

## Inicializar la base de datos
- En la app, entra como admin → **Productos (admin)** → **Inicialización** → **Inicializar base de datos**.
- Luego importa `Productos.csv`.

## Despliegue gratis (Streamlit Community Cloud + Neon)
1. Sube este proyecto a GitHub.
2. Crea una base de datos en Neon y copia el connection string.
3. Crea la app en Streamlit Community Cloud desde el repo.
4. Configura Secrets:
   - `DATABASE_URL`
   - `PIN_ADMIN`
   - `PIN_OPERADOR`
5. Deploy. Usa la pantalla de admin para inicializar tablas e importar productos. Si necesitas más cuentas por PIN, configura **Roles y PINs (admin)** tras el primer acceso con `PIN_ADMIN`.

