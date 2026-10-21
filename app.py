import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SYNC_SECRET_KEY = "boda_cuñada_secreto_2026"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        accion = request.form.get('accion', 'existente') # 'existente' o 'nuevo'
        
        if not nombre:
            return "Por favor ingresa tu nombre", 400
        
        nombre_limpio = secure_filename(nombre)
        if not nombre_limpio:
            nombre_limpio = "Invitado"
            
        # Si el usuario eligió crear una carpeta nueva a pesar de ya existir, le agregamos un sufijo único
        if accion == 'nuevo':
            contador = 1
            while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], f"{nombre_limpio}_{contador}")):
                contador += 1
            nombre_limpio = f"{nombre_limpio}_{contador}"

        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], nombre_limpio)
        os.makedirs(user_folder, exist_ok=True)
        
        archivos = request.files.getlist('archivos')
        for archivo in archivos:
            if archivo and allowed_file(archivo.filename):
                filename = secure_filename(archivo.filename)
                archivo.save(os.path.join(user_folder, filename))
                
        return redirect(url_for('gracias'))
        
    return render_template('index.html')

@app.route('/gracias')
def gracias():
    return render_template('gracias.html')

# API para verificar si la carpeta del invitado ya existe
@app.route('/api/verificar-nombre', methods=['GET'])
def verificar_nombre():
    nombre = request.args.get('nombre', '').strip()
    if not nombre:
        return jsonify({"existe": False})
    
    nombre_limpio = secure_filename(nombre)
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], nombre_limpio)
    
    existe = os.path.exists(user_folder) and os.path.isdir(user_folder)
    return jsonify({"existe": existe})

# ==========================================
# API PARA TU LAPTOP (SINCRONIZADOR)
# ==========================================

@app.route('/api/listar', methods=['GET'])
def api_listar():
    if request.headers.get('X-Sync-Key') != SYNC_SECRET_KEY:
        return jsonify({"error": "No autorizado"}), 403
    data = {}
    if os.path.exists(UPLOAD_FOLDER):
        for invitado in os.listdir(UPLOAD_FOLDER):
            invitado_dir = os.path.join(UPLOAD_FOLDER, invitado)
            if os.path.isdir(invitado_dir):
                archivos = os.listdir(invitado_dir)
                if archivos:
                    data[invitado] = archivos
    return jsonify(data)

@app.route('/api/descargar/<invitado>/<filename>', methods=['GET'])
def api_descargar(invitado, filename):
    if request.headers.get('X-Sync-Key') != SYNC_SECRET_KEY:
        return "No autorizado", 403
    user_folder = os.path.join(UPLOAD_FOLDER, invitado)
    return send_from_directory(user_folder, filename)

@app.route('/api/eliminar/<invitado>/<filename>', methods=['DELETE'])
def api_eliminar(invitado, filename):
    if request.headers.get('X-Sync-Key') != SYNC_SECRET_KEY:
        return jsonify({"error": "No autorizado"}), 403
    file_path = os.path.join(UPLOAD_FOLDER, invitado, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        invitado_dir = os.path.join(UPLOAD_FOLDER, invitado)
        if not os.listdir(invitado_dir):
            os.rmdir(invitado_dir)
        return jsonify({"status": "eliminado"})
    return jsonify({"error": "Archivo no encontrado"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
