from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc = Document()

style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(10)

VERDE = RGBColor(0x04, 0x49, 0x26)
VERDE_CLARO = RGBColor(0x29, 0xb3, 0x4b)
GRIS = RGBColor(0x6b, 0x72, 0x80)


def heading1(text):
    p = doc.add_heading(text, level=1)
    p.runs[0].font.color.rgb = VERDE
    p.runs[0].font.size = Pt(14)


def heading2(text):
    p = doc.add_heading(text, level=2)
    p.runs[0].font.color.rgb = VERDE_CLARO
    p.runs[0].font.size = Pt(11)


def add_bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    if bold_prefix:
        p.add_run(bold_prefix + ' ').bold = True
    p.add_run(text)


def add_check(text):
    p = doc.add_paragraph(style='List Bullet')
    p.add_run('☐  ' + text)


def cell_fill(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)


def add_table(headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        run = hdr_cells[i].paragraphs[0].runs[0]
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        cell_fill(hdr_cells[i], '044926')
    for r, row in enumerate(rows, 1):
        cells = table.rows[r].cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
            if r % 2 == 0:
                cell_fill(cells[i], 'F0F9F4')
    doc.add_paragraph()


# TITULO
title = doc.add_heading('DSMS Molpack — Guia de Despliegue y Seguridad', 0)
title.runs[0].font.color.rgb = VERDE
title.runs[0].font.size = Pt(18)
sub = doc.add_paragraph('Documento de referencia para reunion con IT - Junio 2026')
sub.runs[0].font.color.rgb = GRIS
doc.add_paragraph()

# 1. STACK
heading1('1. Stack y Arquitectura')
add_table(
    ['Capa', 'Tecnologia', 'Version'],
    [
        ('Backend API', 'FastAPI (Python)', '0.115.0'),
        ('Servidor ASGI', 'Uvicorn', '0.30.0'),
        ('Base de datos', 'PostgreSQL + pgvector', '--'),
        ('ORM', 'SQLAlchemy (async)', '2.0.36'),
        ('Frontend', 'React + Vite', '19 / 5'),
        ('Autenticacion', 'LDAP/Active Directory + JWT', '--'),
        ('Busqueda semantica', 'sentence-transformers (all-MiniLM-L6-v2)', '3.0.1'),
    ]
)
p = doc.add_paragraph()
p.add_run('Flujo de datos en produccion:').bold = True
doc.add_paragraph(
    'Usuario (browser)  ->  Nginx (HTTPS:443)  ->  Uvicorn/FastAPI (:8000)'
    '  ->  PostgreSQL + pgvector  ->  filesystem: uploads/productos/{id_ficha}/'
)
doc.add_paragraph()

# 2. AUTENTICACION
heading1('2. Autenticacion y Control de Acceso')

heading2('2.1 LDAP / Active Directory')
doc.add_paragraph('El sistema autentica contra el AD de Molpack como primera opcion. Pasos:')
for step in [
    'Conecta al DC usando cuenta de servicio (svc_dsms)',
    'Busca el usuario por sAMAccountName',
    'Realiza bind con credenciales del usuario para verificar contrasena',
    'Verifica membresia en grupo DSMS_Users',
    'Deriva el rol desde los grupos AD del usuario',
]:
    add_bullet(step)
doc.add_paragraph()
add_table(
    ['Grupo AD', 'Rol en sistema'],
    [
        ('Grupos con "admin"', 'Administrador'),
        ('Grupos con "qa" o "calidad"', 'QA'),
        ('Resto de usuarios autorizados', 'Consultor'),
    ]
)

heading2('2.2 JWT (JSON Web Tokens)')
items = [
    ('Algoritmo:', 'HS256'),
    ('Expiracion:', '8 horas (configurable via JWT_EXPIRATION_HOURS)'),
    ('Header:', 'Authorization: Bearer <token>'),
    ('Renovacion:', 'POST /auth/refresh -- sin re-login, token vigente requerido'),
]
for label, val in items:
    p = doc.add_paragraph(style='List Bullet')
    p.add_run(label + ' ').bold = True
    p.add_run(val)

doc.add_paragraph()
heading2('2.3 Rate Limiting (anti fuerza bruta)')
for item in [
    'Maximo 5 intentos fallidos por IP en 1 minuto',
    'Bloqueo de 5 minutos al exceder el limite',
    'Se resetea automaticamente al hacer login exitoso',
    'LIMITACION: implementado en memoria -- ver seccion 4.5',
]:
    add_bullet(item)
doc.add_paragraph()

# 3. VULNERABILIDADES
heading1('3. Vulnerabilidades OWASP Cubiertas')
add_table(
    ['Riesgo', 'Estado', 'Mecanismo'],
    [
        ('SQL Injection', 'Cubierto', 'SQLAlchemy ORM con consultas parametrizadas. No hay SQL crudo.'),
        ('XSS', 'Cubierto', 'React escapa texto por defecto. No se usa dangerouslySetInnerHTML.'),
        ('Fuerza bruta', 'Cubierto', 'Rate limiting por IP en /auth/login (5 intentos / 5 min bloqueo).'),
        ('Upload malicioso', 'Cubierto', 'Validacion de content-type, extension, tamano (5 MB), dimensiones.'),
        ('Path traversal', 'Cubierto', 'Rutas fijas: uploads/productos/{uuid}/tipo.ext'),
        ('Acceso no autorizado', 'Cubierto', 'Todos los endpoints protegidos con JWT. Sin token -> 401.'),
        ('Escalacion de estado', 'Cubierto', 'Maquina de estados estricta: Borrador->Preliminar->Vigente->Obsoleto.'),
        ('SQL en logs', 'Pendiente', 'echo=True activo en dev -- desactivar antes de produccion.'),
    ]
)

# 4. PENDIENTES
heading1('4. Puntos Pendientes para Produccion')

heading2('4.1 HTTPS -- No configurado')
doc.add_paragraph(
    'Actualmente el sistema corre en HTTP plano. En produccion es obligatorio colocar Nginx '
    'delante de Uvicorn con certificado TLS (puede ser certificado interno de la empresa).'
)

heading2('4.2 Credenciales en .env')
doc.add_paragraph('El archivo .env actual tiene valores de desarrollo que DEBEN cambiarse:')
add_table(
    ['Variable', 'Estado actual', 'Accion requerida'],
    [
        ('DB_PASSWORD', '0000', 'Cambiar por contrasena segura'),
        ('JWT_SECRET', 'your_secret_key_here', 'Generar: python -c "import secrets; print(secrets.token_hex(32))"'),
        ('LDAP_BIND_PASSWORD', 'vacio', 'Ingresar contrasena de cuenta svc_dsms'),
    ]
)

heading2('4.3 Usuarios locales de desarrollo')
doc.add_paragraph(
    'auth_service.py tiene usuarios hardcodeados (admin/admin, demo/demo) para desarrollo. '
    'Antes de produccion:'
)
add_bullet('Eliminar o deshabilitar los usuarios demo y marco.agrusa')
add_bullet('El usuario admin puede mantenerse como emergencia con contrasena fuerte')

heading2('4.4 Logging de SQL')
doc.add_paragraph('database.py tiene echo=True -- imprime cada query SQL al log. Cambiar a echo=False en produccion.')

heading2('4.5 Rate Limiter en Memoria')
doc.add_paragraph('El rate limiter usa un dict Python en memoria. Limitaciones:')
add_bullet('Se reinicia al reiniciar el proceso')
add_bullet('No funciona con multiples workers (Gunicorn multi-process)')
add_bullet('Para produccion con carga real: reemplazar con Redis + slowapi')

heading2('4.6 CORS')
doc.add_paragraph(
    'No hay CORSMiddleware configurado en main.py. Si frontend y backend se sirven desde dominios '
    'distintos hay que configurarlo con el dominio exacto (no usar "*").'
)
doc.add_paragraph()

# 5. REQUISITOS
heading1('5. Requisitos del Servidor')

heading2('5.1 Base de datos')
add_bullet('PostgreSQL 15+')
add_bullet('Extension pgvector: apt install postgresql-16-pgvector (Ubuntu/Debian)')
add_bullet('Ejecutar en psql: CREATE EXTENSION IF NOT EXISTS vector;')

heading2('5.2 Modelo NLP -- Descarga automatica')
doc.add_paragraph(
    'La primera vez que se inicia el backend descarga all-MiniLM-L6-v2 (~90 MB) desde Hugging Face.'
)
p = doc.add_paragraph()
p.add_run('Si el servidor no tiene salida a internet:').bold = True
add_bullet('Descargar el modelo en una maquina con internet')
add_bullet('Copiar la carpeta ~/.cache/huggingface/ al servidor')
add_bullet('Configurar: SENTENCE_TRANSFORMERS_HOME=/ruta/local/al/modelo')

heading2('5.3 Almacenamiento de imagenes')
doc.add_paragraph('Las imagenes se guardan en uploads/productos/ en el filesystem del servidor:')
add_bullet('La carpeta debe tener permisos de escritura para el proceso Uvicorn')
add_bullet('DEBE incluirse en el plan de backups -- no se replica en la BD')
add_bullet('Espacio estimado: hasta 5 MB por imagen, maximo 2 imagenes por ficha')
doc.add_paragraph()

# 6. VARIABLES
heading1('6. Variables de Entorno -- Referencia Completa')
add_table(
    ['Variable', 'Descripcion', 'Ejemplo'],
    [
        ('DB_HOST', 'Host del servidor PostgreSQL', 'localhost'),
        ('DB_PORT', 'Puerto PostgreSQL', '5432'),
        ('DB_NAME', 'Nombre de la base de datos', 'molpack_dsms'),
        ('DB_USER', 'Usuario BD (no superuser)', 'dsms_user'),
        ('DB_PASSWORD', 'Contrasena BD', '<contrasena_segura>'),
        ('LDAP_SERVER', 'URL del servidor AD', 'ldap://dc01.molpack.local'),
        ('LDAP_BASE_DN', 'DN base del dominio', 'DC=molpack,DC=net'),
        ('LDAP_BIND_DN', 'DN cuenta de servicio', 'CN=svc_dsms,OU=Service Accounts,...'),
        ('LDAP_BIND_PASSWORD', 'Contrasena cuenta servicio', '<contrasena>'),
        ('LDAP_GRUPO_AUTORIZADO', 'Grupo AD con acceso', 'CN=DSMS_Users,OU=Groups,...'),
        ('LDAP_USE_SSL', 'Usar LDAPS (puerto 636)', 'false'),
        ('JWT_SECRET', 'Clave secreta JWT (64 chars hex)', '<secrets.token_hex(32)>'),
        ('JWT_EXPIRATION_HOURS', 'Duracion del token en horas', '8'),
    ]
)

# 7. CHECKLIST
heading1('7. Checklist de Despliegue')

heading2('Servidor')
for item in [
    'Ubuntu 22.04+ o RHEL 8+',
    'Python 3.12 instalado',
    'PostgreSQL 15+ instalado',
    'Extension postgresql-pgvector instalada',
    'Nginx instalado',
    'Certificado TLS valido',
]:
    add_check(item)

heading2('Base de datos')
for item in [
    'Base de datos molpack_dsms creada',
    'Usuario BD con permisos minimos (no superuser)',
    'CREATE EXTENSION vector; ejecutado',
    'Migraciones aplicadas',
]:
    add_check(item)

heading2('Backend')
for item in [
    'pip install -r requirements.txt ejecutado',
    'pip install ldap3 ejecutado (no esta en requirements.txt)',
    '.env con valores de produccion (no defaults)',
    'JWT_SECRET generado con secrets.token_hex(32)',
    'DB_PASSWORD segura',
    'echo=False en app/core/database.py',
    'Usuarios locales de desarrollo eliminados de auth_service.py',
    'Carpeta uploads/ creada con permisos de escritura',
]:
    add_check(item)

heading2('Frontend')
for item in [
    'npm install ejecutado en carpeta frontend/',
    'npm run build ejecutado -- genera carpeta dist/',
    'dist/ copiada al directorio de Nginx',
]:
    add_check(item)

heading2('Nginx / Red')
for item in [
    'Nginx configurado con proxy hacia :8000 para /api/',
    'HTTPS habilitado con certificado valido',
    'Puerto 8000 bloqueado en firewall (solo Nginx accede)',
    'Puerto 443 abierto para usuarios internos',
]:
    add_check(item)

heading2('Post-despliegue -- Verificacion')
for item in [
    'Login con AD funciona correctamente',
    'Busqueda semantica responde (modelo NLP cargado)',
    'Subida de imagenes funciona y persiste en uploads/',
    'Exportacion PDF genera correctamente',
    'Auditoria registra acciones en la BD',
    'Backups de PostgreSQL y uploads/ programados',
]:
    add_check(item)

doc.add_paragraph()

# 8. PUERTOS
heading1('8. Puertos y Comunicacion Interna')
add_table(
    ['Servicio', 'Puerto', 'Acceso'],
    [
        ('Nginx (HTTPS)', '443', 'Usuarios de red interna'),
        ('Uvicorn (API)', '8000', 'Solo localhost -- NO exponer directamente'),
        ('PostgreSQL', '5432', 'Solo localhost (desde Uvicorn)'),
        ('AD/LDAP', '389 / 636', 'Desde servidor hacia DC de Molpack'),
    ]
)

p = doc.add_paragraph()
p.add_run('Generado: Junio 2026 -- DSMS Molpack Corporation').italic = True
p.runs[0].font.color.rgb = GRIS

out = r'c:\Users\marco\OneDrive\Documents\GitHub\Molpack_DSMS\IT_Deployment_Guide.docx'
doc.save(out)
print(f'Documento guardado: {out}')
