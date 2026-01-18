import os
import pyodbc
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()

app = Flask("Login")
# Esta llave encripta la cookie para que nadie pueda falsificar su sesión
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'clave_default_solo_para_local')


# --- CONFIGURACIÓN DE CONEXIÓN ---
def get_connection_string(user, pwd):
    """Genera el texto de conexión para SQL Server"""
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_NAME')
    driver = '{ODBC Driver 18 for SQL Server}'

    return (f"DRIVER={driver};SERVER={server};DATABASE={database};"
            f"UID={user};PWD={pwd};TrustServerCertificate=Yes;")


@app.route('/')
def home():
    return render_template('login.html', error="")


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    connection = None
    try:
        # 1. PRUEBA DE FUEGO: Intentamos conectar con lo que escribió el usuario.
        # Si la contraseña es incorrecta, pyodbc dará error y saltará al 'except'.
        conn_str = get_connection_string(username, password)
        connection = pyodbc.connect(conn_str)

        # Si la línea de arriba no falló, ¡es el usuario correcto!
        session['username'] = username

        # NOTA IMPORTANTE: Ya NO guardamos session['password'].
        # Esto elimina la vulnerabilidad crítica de exponer credenciales en cookies.

        return redirect(url_for('tables'))

    except Exception as e:
        print(f"Fallo de login para {username}: {e}")
        return render_template('login.html', error="Usuario o contraseña incorrectos.")
    finally:
        if connection:
            connection.close()


@app.route('/tables', methods=['GET', 'POST'])
def tables():
    # Si no se ha logueado, va para afuera
    if 'username' not in session:
        return redirect(url_for('home'))

    connection = None
    cursor = None

    try:
        # TRUCO PARA EL PROYECTO:
        # Como ya validamos que el usuario es real en el Login, ahora usamos
        # la "Cuenta Maestra" (del .env) para mostrarle los datos.
        # Esto evita tener que guardar la contraseña del alumno en la sesión.
        sys_user = os.getenv('DB_USER')
        sys_pwd = os.getenv('DB_PASSWORD')

        connection = pyodbc.connect(get_connection_string(sys_user, sys_pwd))
        cursor = connection.cursor()

        # 1. Obtener lista de tablas (Lista Blanca para evitar Hackeos)
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        tables_list = [row[0] for row in cursor.fetchall()]

        selected_data = None

        if request.method == 'POST':
            selected_table = request.form['table_name']

            # 2. VALIDACIÓN DE SEGURIDAD (Anti-SQL Injection)
            if selected_table in tables_list:
                cursor.execute(f"SELECT * FROM [{selected_table}]")
                # Obtenemos los nombres de las columnas para que la tabla se vea bonita
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                selected_data = {'columns': columns, 'rows': rows}
            else:
                return "Error: Tabla no autorizada", 403

        return render_template('tables.html', tables=tables_list, data=selected_data)

    except Exception as e:
        print("Error en tablas:", e)
        return "Error de conexión con la base de datos", 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)