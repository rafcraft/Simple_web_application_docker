from dotenv import load_dotenv
import os
import mysql.connector
from flask import Flask, render_template, flash, request
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired
from flask_socketio import SocketIO, emit
import socket
import threading


load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
bootstrap = Bootstrap(app)
socketio = SocketIO(app)

# Konfiguracja bazy danych MySQL
conn = mysql.connector.connect(
    host=os.getenv('DB_HOST'),       # Pobierane z .env
    user=os.getenv('DB_USER'),       # Pobierane z .env
    password=os.getenv('DB_PASSWORD'),  # Pobierane z .env
    database=os.getenv('DB_NAME')    # Pobierane z .env
)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS form (id INT AUTO_INCREMENT PRIMARY KEY, email VARCHAR(30), name VARCHAR(30), last_name VARCHAR(30), message TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS messages (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(30), message TEXT, data DATETIME)')
cursor.close()


class MyForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    name = StringField('Imie', validators=[DataRequired()])
    last_name = StringField('Nazwisko', validators=[DataRequired()])
    message = TextAreaField('Wiadomość', validators=[DataRequired()])


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat')
def chat():
    cursor.execute('SELECT username, message FROM messages ORDER BY id DESC LIMIT 20')
    messages = cursor.fetchall()
    messages.reverse()
    return render_template('chat.html', messages=messages)


@app.route('/form', methods=['GET', 'POST'])
def form():
    form1 = MyForm()

    if form1.validate_on_submit():
        email = form1.email.data
        name = form1.name.data
        last_name = form1.last_name.data
        message = form1.message.data
        cursor.execute('INSERT INTO form (email, name, last_name, message) VALUES (%s, %s, %s, %s)', (email, name, last_name, message))
        conn.commit()
        flash('Dane zostały zapisane pomyślnie!', 'success')
    return render_template('form.html', form=form1)


@socketio.on('connect')
def handle_connect():
    print('Połączono z klientem:', request.sid)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('flask_app', 5000))
    client_socket.send(f"Połączono z klientem: {request.sid}".encode())
    client_socket.close()


@socketio.on('message')
def handle_message(data):
    name = data['name']
    message = data['message']
    cursor.execute('INSERT INTO messages (username, message, data) VALUES (%s, %s, NOW())', (name, message))
    conn.commit()
    emit('message', {'name': name, 'message': message}, broadcast=True)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('flask_app', 5000))
    client_socket.send(f'Otrzymano wiadomość od {name}: {message}'.encode())
    client_socket.close()


@socketio.on('disconnect')
def handle_disconnect():
    print('Rozłączono z klientem:', request.sid)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('flask_app', 5000))
    client_socket.send(f"Rozłączono z klientem: {request.sid}".encode())
    client_socket.close()


def save_message_to_database(message, nickname):
    cursor.execute('INSERT INTO messages (username, message) VALUES (%s, %s)', (nickname, message))
    conn.commit()


if __name__ == '__main__':
    thread = threading.Thread(target=socketio.run(app), kwargs={'host': '0.0.0.0', 'port': 5000})
    thread.daemon = True
    thread.start()
