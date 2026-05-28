#!/usr/bin/env python3
"""
Equipo 2: Servidor Web de Chat Interactivos HTTP (Texto Plano)
Laboratorio de Ciberseguridad
"""

import os
import sys
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request

app = Flask(__name__, template_folder='templates')

# Almacenamiento temporal en memoria de los mensajes del chat
messages = []

@app.route('/')
def index():
    """Sirve la interfaz principal del Servidor con chat integrado"""
    return render_template('index.html')

@app.route('/api/messages', methods=['GET'])
def get_messages():
    """Devuelve la lista completa de mensajes recibidos/enviados"""
    return jsonify({
        "messages": messages,
        "count": len(messages)
    })

@app.route('/api/message', methods=['POST'])
def receive_message():
    """Recibe un mensaje en texto plano (HTTP POST sin cifrar) desde el Cliente o desde el mismo Servidor"""
    data = request.json or {}
    sender = data.get("sender", "Desconocido").strip()
    text = data.get("text", "").strip()
    
    if not text:
        return jsonify({"success": False, "error": "El mensaje no puede estar vacío."}), 400
        
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    message_entry = {
        "id": len(messages),
        "sender": sender,
        "text": text,
        "timestamp": timestamp
    }
    
    messages.append(message_entry)
    print(f"[+] [{timestamp}] Mensaje recibido de {sender}: {text}")
    return jsonify({"success": True, "message": message_entry})

if __name__ == '__main__':
    # Inicia el servidor HTTP en el puerto 80 (estándar plano)
    print("*" * 60)
    print(" INICIANDO EQUIPO 2 - SERVIDOR DE CHAT EN PUERTO 80 (HTTP PLANO)")
    print("*" * 60)
    
    try:
        app.run(host='0.0.0.0', port=80, debug=True)
    except PermissionError:
        print("[✗] Error: Se requieren permisos de root para escuchar en el puerto 80.")
        print("    Ejecuta el script usando: sudo python3 server_app.py")
        sys.exit(1)
