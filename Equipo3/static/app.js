// ==========================================================================
// ARP Spoofing Control Center - Dynamic Frontend Controller (Vanilla JS)
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    // ---- Elementos del DOM ----
    const interfaceSelect = document.getElementById('interface-select');
    const targetIpInput = document.getElementById('target-ip');
    const gatewayIpInput = document.getElementById('gateway-ip');
    const ipForwardingStatus = document.getElementById('ip-forwarding-status');
    const attackTimer = document.getElementById('attack-timer');
    
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    const btnFlush = document.getElementById('btn-flush');
    const btnClearConsole = document.getElementById('btn-clear-console');
    
    const metricPackets = document.getElementById('metric-packets');
    const metricRequests = document.getElementById('metric-requests');
    const metricCredentials = document.getElementById('metric-credentials');
    const cardCredentials = document.getElementById('card-credentials');
    
    const statusBadge = document.getElementById('status-badge');
    const statusText = document.getElementById('status-text');
    
    const consoleOutput = document.getElementById('console-output');
    const autoscrollChk = document.getElementById('autoscroll-chk');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');

    // ---- Variables de Estado ----
    let isAttackRunning = false;
    let lastLogId = -1;
    let statusIntervalId = null;
    let logsIntervalId = null;
    let timerIntervalId = null;
    let durationSeconds = 0;
    let activeFilter = 'all';

    // ---- Inicialización ----
    loadInterfaces();
    checkSystemStatus();
    
    // Iniciar monitoreo del estado general del backend (cada 2 segundos)
    statusIntervalId = setInterval(checkSystemStatus, 2000);

    // ---- Listeners de Eventos ----
    
    // Iniciar Ataque
    btnStart.addEventListener('click', async (e) => {
        e.preventDefault();
        
        const interfaceVal = interfaceSelect.value;
        const targetIp = targetIpInput.value.trim();
        const gatewayIp = gatewayIpInput.value.trim();
        
        if (!interfaceVal || !targetIp || !gatewayIp) {
            showToast("⚠️ Por favor, rellena todos los campos de configuración.");
            return;
        }

        btnStart.disabled = true;
        showToast("🚀 Iniciando ataque...");

        try {
            const response = await fetch('/api/attack/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    interface: interfaceVal,
                    target_ip: targetIp,
                    gateway_ip: gatewayIp
                })
            });
            const data = await response.json();
            
            if (data.success) {
                isAttackRunning = true;
                showToast("🔥 ¡ARP Spoofing e interceptación activados exitosamente!");
                // Forzar actualización de UI inmediata
                checkSystemStatus();
            } else {
                showToast(`❌ Error: ${data.error}`);
                btnStart.disabled = false;
            }
        } catch (err) {
            showToast("❌ Error de red al iniciar el ataque.");
            btnStart.disabled = false;
        }
    });

    // Detener Ataque
    btnStop.addEventListener('click', async () => {
        btnStop.disabled = true;
        showToast("🛑 Deteniendo ataque y restaurando red...");
        
        try {
            const response = await fetch('/api/attack/stop', { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                isAttackRunning = false;
                showToast("✅ Ataque finalizado. Tablas de red restauradas.");
                checkSystemStatus();
            } else {
                showToast(`❌ Error al detener: ${data.error}`);
                btnStop.disabled = false;
            }
        } catch (err) {
            showToast("❌ Error de red al detener el ataque.");
            btnStop.disabled = false;
        }
    });

    // Limpiar Caché ARP
    btnFlush.addEventListener('click', async () => {
        btnFlush.disabled = true;
        showToast("🧹 Limpiando caché ARP...");
        try {
            const response = await fetch('/api/flush-arp', { method: 'POST' });
            const data = await response.json();
            if (data.success) {
                showToast("🧹 Tabla ARP local limpiada correctamente.");
            } else {
                showToast(`❌ Error: ${data.error}`);
            }
        } catch (err) {
            showToast("❌ Error de comunicación con el backend.");
        } finally {
            btnFlush.disabled = false;
        }
    });

    // Limpiar Consola Local
    btnClearConsole.addEventListener('click', () => {
        consoleOutput.innerHTML = `
            <div class="console-placeholder">
                <i class="fa-solid fa-satellite-dish"></i>
                <p>Consola vacía. Capturando nuevas peticiones en tiempo real...</p>
            </div>
        `;
        showToast("🧹 Vista de consola limpia.");
    });

    // Control de Filtros de Logs
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeFilter = btn.dataset.filter;
            applyLogFilters();
        });
    });

    // ---- Funciones Lógicas ----

    // Obtener interfaces de red
    async function loadInterfaces() {
        try {
            const response = await fetch('/api/interfaces');
            const data = await response.json();
            
            if (data.interfaces && data.interfaces.length > 0) {
                interfaceSelect.innerHTML = '';
                data.interfaces.forEach(iface => {
                    const option = document.createElement('option');
                    option.value = iface;
                    option.textContent = iface;
                    // Auto-seleccionar la recomendada
                    if (iface === data.recommended) {
                        option.selected = true;
                    }
                    interfaceSelect.appendChild(option);
                });
            } else {
                interfaceSelect.innerHTML = '<option value="" disabled>No se detectaron interfaces</option>';
            }
        } catch (err) {
            interfaceSelect.innerHTML = '<option value="" disabled>Error al cargar interfaces</option>';
        }
    }

    // Consultar el estado del sistema en el backend
    async function checkSystemStatus() {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();
            
            isAttackRunning = status.running;
            
            // Actualizar indicación de IP Forwarding
            if (status.ip_forwarding) {
                ipForwardingStatus.textContent = "ACTIVO";
                ipForwardingStatus.className = "badge badge-success";
            } else {
                ipForwardingStatus.textContent = "INACTIVO";
                ipForwardingStatus.className = "badge badge-error";
            }

            // Actualizar Métricas
            metricPackets.textContent = status.statistics.total_packets.toLocaleString();
            metricRequests.textContent = status.statistics.total_requests.toLocaleString();
            metricCredentials.textContent = status.statistics.total_credentials.toLocaleString();
            
            // Efecto Glow de Alarma de credenciales
            if (status.statistics.total_credentials > 0) {
                cardCredentials.classList.add('alarm-active');
            } else {
                cardCredentials.classList.remove('alarm-active');
            }

            // Cambiar estados visuales según el modo (Atacando / Inactivo)
            if (isAttackRunning) {
                // Modo Ataque Activo
                statusBadge.className = "status-indicator-badge active";
                statusText.textContent = "MONITOREANDO RED (MitM)";
                
                // Bloquear inputs
                interfaceSelect.disabled = true;
                targetIpInput.disabled = true;
                gatewayIpInput.disabled = true;
                
                // Rellenar valores si no estaban puestos (ej: recarga de página)
                if (status.interface && !interfaceSelect.value) {
                    const opt = document.createElement('option');
                    opt.value = status.interface;
                    opt.textContent = status.interface;
                    opt.selected = true;
                    interfaceSelect.appendChild(opt);
                }
                if (status.target_ip && !targetIpInput.value) {
                    targetIpInput.value = status.target_ip;
                }
                if (status.gateway_ip && !gatewayIpInput.value) {
                    gatewayIpInput.value = status.gateway_ip;
                }

                // Botones
                btnStart.disabled = true;
                btnStop.disabled = false;
                
                // Iniciar contador e intervalo de logs si no estaban corriendo
                durationSeconds = status.duration_seconds;
                updateTimerUI();
                if (!timerIntervalId) {
                    timerIntervalId = setInterval(() => {
                        durationSeconds++;
                        updateTimerUI();
                    }, 1000);
                }

                if (!logsIntervalId) {
                    // Cargar logs existentes rápidamente en primer consumo
                    fetchNewLogs();
                    logsIntervalId = setInterval(fetchNewLogs, 600);
                }
            } else {
                // Modo Inactivo
                statusBadge.className = "status-indicator-badge idles";
                statusText.textContent = "SISTEMA INACTIVO";
                
                // Habilitar inputs
                interfaceSelect.disabled = false;
                targetIpInput.disabled = false;
                gatewayIpInput.disabled = false;
                
                // Botones
                btnStart.disabled = false;
                btnStop.disabled = true;
                
                // Detener cronómetro
                if (timerIntervalId) {
                    clearInterval(timerIntervalId);
                    timerIntervalId = null;
                }
                durationSeconds = 0;
                updateTimerUI();

                // Detener lectura de logs
                if (logsIntervalId) {
                    clearInterval(logsIntervalId);
                    logsIntervalId = null;
                }
                lastLogId = -1;
            }
        } catch (err) {
            console.error("Error al consultar estado:", err);
        }
    }

    // Cronómetro de Ataque
    function updateTimerUI() {
        const hrs = String(Math.floor(durationSeconds / 3600)).padStart(2, '0');
        const mins = String(Math.floor((durationSeconds % 3600) / 60)).padStart(2, '0');
        const secs = String(durationSeconds % 60).padStart(2, '0');
        attackTimer.textContent = `${hrs}:${mins}:${secs}`;
    }

    // Polling de nuevos logs del tcpdump
    async function fetchNewLogs() {
        try {
            const response = await fetch(`/api/logs?since=${lastLogId}`);
            const data = await response.json();
            
            if (data.logs && data.logs.length > 0) {
                // Eliminar placeholder inicial si existe
                const placeholder = consoleOutput.querySelector('.console-placeholder');
                if (placeholder) {
                    placeholder.remove();
                }
                
                data.logs.forEach(log => {
                    appendLogToConsole(log);
                });
                
                lastLogId = data.last_id;
                
                // Desplazamiento automático si está activado
                if (autoscrollChk.checked) {
                    consoleOutput.scrollTop = consoleOutput.scrollHeight;
                }
            }
        } catch (err) {
            console.error("Error de polling de logs:", err);
        }
    }

    // Insertar un log en el DOM
    function appendLogToConsole(log) {
        const logDiv = document.createElement('div');
        logDiv.className = `log-item log-${log.type}`;
        logDiv.dataset.type = log.type;
        
        // Formatear emojis o tags en el mensaje del log
        let formattedMessage = log.message;
        let iconHtml = '';
        
        if (log.type === 'get') iconHtml = '<i class="fa-solid fa-cloud-arrow-down"></i> GET ';
        else if (log.type === 'post') iconHtml = '<i class="fa-solid fa-cloud-arrow-up"></i> POST ';
        else if (log.type === 'credential') iconHtml = '🔑 ¡CREDENCIAL DETECTADA! ';
        else if (log.type === 'response') iconHtml = '✅ ';
        else if (log.type === 'chat_message') iconHtml = '💬 CHAT INTERCEPTADO: ';
        
        // Crear estructura interna
        logDiv.innerHTML = `
            <div class="log-time">${log.timestamp}</div>
            <div class="log-content">${iconHtml}${escapeHTML(formattedMessage)}</div>
        `;
        
        // Aplicar filtros según estado actual
        if (activeFilter !== 'all' && log.type !== activeFilter) {
            logDiv.classList.add('hidden-log');
        }
        
        consoleOutput.appendChild(logDiv);
    }

    // Ocultar/Mostrar logs según filtro activo
    function applyLogFilters() {
        const logs = consoleOutput.querySelectorAll('.log-item');
        logs.forEach(log => {
            const logType = log.dataset.type;
            if (activeFilter === 'all') {
                log.classList.remove('hidden-log');
            } else {
                if (logType === activeFilter) {
                    log.classList.remove('hidden-log');
                } else {
                    log.classList.add('hidden-log');
                }
            }
        });
        
        // Re-desplazar al final después de filtrar
        if (autoscrollChk.checked) {
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }
    }

    // Toast slider
    function showToast(message) {
        toastMessage.innerHTML = message;
        toast.classList.remove('hidden');
        
        // Ocultar después de 4 segundos
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 4000);
    }

    // Escapar tags HTML para evitar vulnerabilidad XSS en el log viewer
    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    }
});

// Estilo de ayuda para ocultar logs filtrados
const style = document.createElement('style');
style.textContent = '.hidden-log { display: none !important; }';
document.head.appendChild(style);
