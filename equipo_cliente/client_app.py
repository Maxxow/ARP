#!/usr/bin/env python3
"""
Equipo 1: Cliente Web de Chat Interactivos HTTP (Texto Plano)
Laboratorio de Ciberseguridad
"""

import os
import sys
import json
import urllib.request
import urllib.error
from flask import Flask, render_template, jsonify, request

app = Flask(__name__, template_folder='templates')

# IP del Servidor (Equipo 2) - Configurable dinámicamente desde el panel
server_ip = ""

@app.route('/')
def index():
    """Sirve la interfaz principal de chat del Cliente"""
    return render_template('client.html')

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Consulta o guarda la IP del Servidor de Destino"""
    global server_ip
    if request.method == 'POST':
        data = request.json or {}
        ip = data.get("server_ip", "").strip()
        if not ip:
            return jsonify({"success": False, "error": "IP no válida."}), 400
        server_ip = ip
        print(f"[+] IP del Servidor configurada en: {server_ip}")
        return jsonify({"success": True, "server_ip": server_ip})
    
    return jsonify({
        "server_ip": server_ip,
        "configured": bool(server_ip)
    })

@app.route('/api/messages', methods=['GET'])
def get_server_messages():
    """Proxy para obtener los mensajes directamente del Servidor de forma transparente (evitando CORS)"""
    global server_ip
    if not server_ip:
        return jsonify({"messages": [], "error": "Servidor no configurado."}), 200
        
    url = f"http://{server_ip}/api/messages"
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            return jsonify(data)
    except urllib.error.URLError as e:
        return jsonify({"messages": [], "error": f"Error de red: {e.reason}"}), 200
    except Exception as e:
        return jsonify({"messages": [], "error": f"Error inesperado: {str(e)}"}), 200

@app.route('/api/send', methods=['POST'])
def send_message_to_server():
    """Envía un mensaje en texto plano mediante HTTP POST al Servidor"""
    global server_ip
    if not server_ip:
        return jsonify({"success": False, "error": "Configura primero la IP del Servidor."}), 400
        
    data = request.json or {}
    text = data.get("text", "").strip()
    
    if not text:
        return jsonify({"success": False, "error": "Mensaje vacío."}), 400
        
    url = f"http://{server_ip}/api/message"
    payload = json.dumps({
        "sender": "Cliente",
        "text": text
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=payload, method='POST')
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=3) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return jsonify(res_data)
            
    except urllib.error.URLError as e:
        return jsonify({"success": False, "error": f"No se pudo conectar al servidor: {e.reason}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": f"Error al enviar mensaje: {str(e)}"}), 500

if __name__ == '__main__':
    print("*" * 60)
    print(" INICIANDO EQUIPO 1 - CLIENTE DE CHAT EN PORT 8081 (HTTP PLANO)")
    print("*" * 60)
    
    # Inicia en puerto 8081 local
    app.run(host='0.0.0.0', port=8081, debug=True)
