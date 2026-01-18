import os
import pyodbc
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()

app = Flask("Login")

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'clave_default_solo_para_local')


def get_connection_string(user, pwd):

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

        conn_str = get_connection_string(username, password)
        connection = pyodbc.connect(conn_str)

        session['username'] = username


        return redirect(url_for('tables'))

    except Exception as e:
        print(f"Fallo de login para {username}: {e}")
        return render_template('login.html', error="Usuario o contraseña incorrectos.")
    finally:
        if connection:
            connection.close()


@app.route('/tables', methods=['GET', 'POST'])
def tables():
    #verificar log
    if 'username' not in session:
        return redirect(url_for('home'))

    connection = None
    cursor = None

    try:

        sys_user = os.getenv('DB_USER')
        sys_pwd = os.getenv('DB_PASSWORD')

        connection = pyodbc.connect(get_connection_string(sys_user, sys_pwd))
        cursor = connection.cursor()

        # Obtener lista de tablas
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        tables_list = [row[0] for row in cursor.fetchall()]

        selected_data = None

        if request.method == 'POST':
            selected_table = request.form['table_name']

            #VALIDACIÓN DE SEGURIDAD
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