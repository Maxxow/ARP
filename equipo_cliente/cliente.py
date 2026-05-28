#!/usr/bin/env python3
import urllib.request
import time
import sys

def main():
    print("=" * 60)
    print("      LABORATORIO DE ARP SPOOFING - EQUIPO 1 (CLIENTE/VÍCTIMA)      ")
    print("=" * 60)

    # Definir la IP del servidor de destino
    # Puedes pasar la IP como argumento de línea de comandos o escribirla cuando te lo pida
    if len(sys.argv) > 1:
        ip_servidor = sys.argv[1]
    else:
        print("[-] No se proporcionó ninguna IP como argumento.")
        try:
            ip_servidor = input("[?] Por favor, introduce la IP del Servidor (Equipo 2): ").strip()
        except KeyboardInterrupt:
            print("\n[!] Operación cancelada por el usuario.")
            sys.exit(0)

    if not ip_servidor:
        print("[!] Error: Debes especificar una dirección IP válida.")
        sys.exit(1)

    url = f"http://{ip_servidor}"
    print(f"\n[+] Iniciando peticiones HTTP constantes hacia: {url}")
    print("[+] El tráfico enviado no está cifrado (HTTP en texto plano).")
    print("[+] Presiona Ctrl+C para detener el script.\n")
    print("-" * 60)

    contador = 0
    while True:
        try:
            contador += 1
            # Realiza una petición GET al servidor
            inicio = time.time()
            respuesta = urllib.request.urlopen(url, timeout=5)
            duracion = (time.time() - inicio) * 1000
            codigo_estado = respuesta.getcode()
            
            if codigo_estado == 200:
                print(f"[+] [{contador:04d}] Petición exitosa! Código: {codigo_estado} | Latencia: {duracion:.2f}ms")
            else:
                print(f"[-] [{contador:04d}] Servidor respondió con código: {codigo_estado} | Latencia: {duracion:.2f}ms")
                
        except urllib.error.URLError as e:
            print(f"[!] [{contador:04d}] Error de Red/Conexión: {e.reason}")
        except Exception as e:
            print(f"[!] [{contador:04d}] Error inesperado al conectar: {e}")
            
        # Espera 3 segundos antes de hacer la siguiente petición
        time.sleep(3)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Script finalizado. Saliendo del laboratorio cliente...")
        sys.exit(0)
