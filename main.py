import os
import uuid
import sqlite3
from flask import Flask, request, jsonify, g, send_file

conn = sqlite3.connect('usersData.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  email TEXT,
                  password TEXT)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS files
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filename TEXT UNIQUE,
                  file_link TEXT,
                  download_key TEXT)''')

conn.commit()

app = Flask(__name__)

DATABASE = 'usersData.db'
UPLOAD_FOLDER = 'uploads'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('usersData.db')
    return db

def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    cursor.close()

    if user:
        return jsonify({'message': 'Login successful', 'role': user[3]}), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401


@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'message': 'Username, email, and password are required'}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
        db.commit()
        return jsonify({'message': 'Signup successful'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Username or email already exists'}), 400
    finally:
        cursor.close()


@app.route('/upload-file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    unique_key = str(uuid.uuid4())[:8]  # Generate a unique key for the file

    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO files (filename, file_link, download_key) VALUES (?, ?, ?)", (file.filename, os.path.join(UPLOAD_FOLDER, file.filename), unique_key))
    db.commit()
    cursor.close()

    file.save(os.path.join(UPLOAD_FOLDER, file.filename))
    return jsonify({'message': 'File uploaded successfully', 'download_key': unique_key}), 200


@app.route('/download-file/<download_key>', methods=['GET'])
def download_file(download_key):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM files WHERE download_key = ?", (download_key,))
    file_data = cursor.fetchone()
    cursor.close()

    if file_data:
        file_path = file_data[2]
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'message': 'File not found'}), 404


@app.route('/list-uploaded-files', methods=['GET'])
def list_uploaded_files():
    cursor.execute("SELECT filename FROM files")
    uploaded_files_list = cursor.fetchall()

    if uploaded_files_list:
        file_names = [file[0] for file in uploaded_files_list]
        return jsonify({'uploaded-files': file_names})
    else:
        return jsonify({'message': 'No uploaded files yet'})


if __name__ == '__main__':
    app.run(debug=True)