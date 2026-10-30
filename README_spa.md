<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="Banner de ARMOR-NETWORK" width="100%">
</p>

# 🛰️ ARMOR-NETWORK

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  🇪🇸 <b>Español</b> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Vigila la red local: los dispositivos que hay, si hay internet, qué cambia y qué es nuevo (un programa de Python sin dependencias; corre en una máquina de la red e informa a ARMOR-SERVER)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 o posterior">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Lenguaje">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-181%20passing-2ea44f.svg" alt="Pruebas">
  <img src="https://img.shields.io/badge/Version-0.1.5-0f6cbd.svg" alt="Versión">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Madurez">
</p>

---

**Comprobación de honestidad - qué funciona hoy:** El escáner, el inventario que dice qué cambió, la comprobación de internet, la consulta de la dirección pública, las órdenes desde Studio y los accesos sellados se prueban en un ordenador contra una red guionizada (181 tests; cada mensaje lo acepta el contrato de ARMOR-COMMON), y el programa corre como servicio en el banco de pruebas de la CM5, vigilando la red real en la que está el banco (un router, los móviles y los nodos de la casa). No ha vigilado una casa entera durante semanas, solo pregunta al router y nunca lo configura, y qué es un dispositivo (su tipo, su sistema, su fabricante) es una suposición. No captura paquetes: no puede ver quién habla con quién, y el tráfico por dispositivo y la detección de intrusos en sentido estricto necesitan los contadores del router o un puerto espejo, que es un paso posterior.

---

## 📋 De un vistazo

| | |
|---|---|
| Versión | `0.1.5` |
| Madurez | Establecido |
| Función | Nodo de red local: qué hay en la red, qué cambió, internet, órdenes de Studio |
| Tecnología | Python 3.11+, solo biblioteca estándar |
| Pruebas | 181 (`python -m unittest discover -s tests`) |
| Contrato | Mensaje `armor/network/<nodo>/state`, 111 vectores de conformidad (mensajes y órdenes) |
| Funciona en | Una máquina de la red a vigilar (Linux, Windows o macOS); el banco de la CM5 como servicio |
| En hardware real | Corre como servicio en el banco de pruebas de la CM5, vigilando su red real (un router, los móviles y los nodos de la casa) |
| Licencia | GPL-3.0-or-later |

**Ir a:** [Resumen](#-resumen) · [Arquitectura](#-arquitectura) · [Seguridad](#-seguridad-y-protección) · [Interfaces](#-interfaces) · [Configuración](#-configuración) · [Inicio rápido](#-inicio-rápido) · [Pruebas](#-pruebas) · [Problemas](#-resolución-de-problemas) · [Estructura](#-estructura-del-repositorio) · [Relacionados](#-proyectos-relacionados)

## 🚦 Estado del proyecto

Cada línea es una parte de este repositorio y la luz dice hasta dónde llega hoy. Está escrito con lo que el repositorio puede demostrar (pruebas, compilaciones, ejecuciones), no con lo que está planeado.

🟢 Hecho y verificado · 🟡 Funciona, con límites conocidos · 🟠 Parcial o sin verificar todavía · 🔴 No hecho o no funciona

| Área | Estado | Qué significa aquí |
|---|---|---|
| Software | 🟢 | El escáner, el inventario que dice qué cambió, la comprobación de internet, la consulta de la dirección pública y las órdenes de Studio funcionan como servicio en el banco de pruebas CM5. |
| Pruebas | 🟢 | Pasan 181 pruebas contra una red guionizada, y cada mensaje lo acepta el contrato de ARMOR-COMMON. |
| Protocolos y datos | 🟡 | Qué es un dispositivo (su tipo, su sistema, su fabricante) es una suposición, y nada captura paquetes: el tráfico por dispositivo y la detección de intrusiones en sentido estricto no están hechos. |
| Hardware | 🟡 | Vigila la red real del banco de pruebas CM5 (un router, los móviles y nodos de la casa) pero no ha vigilado una casa entera durante semanas. |
| Seguridad | 🟡 | Solo pregunta al router y nunca lo configura; los accesos sellados están probados en el host y no ha habido una revisión independiente. |
| Integración | 🟡 | Sus mensajes llegan al servidor del banco de pruebas CM5 y a Studio; las órdenes de Studio se prueban contra una red guionizada. |
| Documentación | 🟢 | Ocho idiomas y el historial de cambios están al día. |

## 🎯 Resumen

* **Qué hay en la red:** la tabla de vecinos de la máquina, un toque a cada dirección para que se llene, un eco a cada dispositivo encontrado (latencia y TTL) y lo que los dispositivos anuncian de sí mismos (mDNS, UPnP, NetBIOS, DNS inverso). De cada uno: dirección, MAC, fabricante (del registro de la IEEE, 40.000 bloques), nombre, tipo, sistema, puertos abiertos con lo que dice cada uno y cuándo se vio por primera y por última vez.
* **Puertos:** una conexión TCP a 17 (o 44) puertos de cada dispositivo, de doce en doce, leyendo como mucho unos cientos de bytes de lo que responde; nunca un inicio de sesión, nunca un exploit. Un dispositivo nuevo se mira enseguida, los demás cada cuarto de hora.
* **Qué cambia:** un dispositivo que aparece (los tres primeros barridos solo aprenden), calla o vuelve, cambia de dirección, un puerto que se abre o se cierra, y dos máquinas que responden por una misma dirección (sobre todo la del router). Cada evento tiene un id, así que se cuenta una vez.
* **Internet:** cada pocos segundos un eco al router, una conexión TCP, dos preguntas DNS a resolvedores elegidos y una página web. Un corte necesita tres rondas para llamarse así y dos para darse por terminado, se fecha desde su primera ronda fallida y se cuenta hasta la primera buena, y dice de quién es la culpa: del operador (el router responde y nada más allá) o de este lado (el router tampoco responde). Latencia, pérdida y los cortes de las últimas 24 horas.
* **Solo mira tu propia red:** rechaza cualquier dirección que no sea privada (10/8, 172.16/12, 192.168/16) y cualquier rango mayor que un /22; una lista de exclusión lo mantiene lejos de lo frágil; a un dispositivo no se le envía nada que no sea una pregunta.
* **El mensaje** `armor/network/<nodo>/state`: la interfaz, internet, cada dispositivo y los últimos eventos; está en el contrato compartido (111 vectores) y lleva hallazgos, nunca órdenes. `python -m armor_network scan` lo imprime como tabla, `watch` informa a ARMOR-SERVER y `demo` representa una casa inventada (se une un dispositivo nuevo, una cámara abre Telnet, se cae internet y vuelve, alguien responde por el router) sin tocar ninguna red.
* **Dónde se ve:** el menú Red de ARMOR-STUDIO (los dispositivos, internet con sus cortes y su latencia, el tráfico y los eventos; un administrador pone nombre a los dispositivos y marca los conocidos, que es lo que apaga la alarma de un dispositivo nuevo), el Diseñador de red (el dibujo de la red de la casa, comparado con lo encontrado y capaz de dibujarlo) y la pantalla Red de la app Android. ARMOR-SERVER genera las alarmas.
* **Órdenes desde Studio:** un barrido ya, un ping, un traceroute, una activación por red, los puertos o la página web de un dispositivo y una inspección con un acceso que das; las órdenes llegan en la respuesta al propio mensaje del nodo (nunca como una conexión hecha al nodo), cada una se comprueba antes de hacer nada y nada se ejecuta por un shell.
* **Accesos que se mantienen seguros:** el acceso de una inspección viaja sellado solo para este nodo, se envía solo por Digest o HTTPS (nunca Basic por HTTP plano), solo al dispositivo cuyo certificado HTTPS se vio la primera vez, y nunca se repite en la respuesta.
* **El lado público:** la dirección pública de la casa, quién la da y dónde está (una petición HTTPS a un servicio público fijo cada pocos minutos; `--no-public-info` la apaga). Con `--dns-name` resuelve además el nombre con el que se llega a la casa desde fuera y dice si apunta a esa dirección.
* **Un servicio:** corre como unidad systemd en el banco de pruebas de la CM5 (escrita a mano, véase la guía de uso) y guarda sus datos en su propia carpeta.
* **Todavía no:** los contadores del propio router (tráfico por dispositivo), la captura de paquetes, controlar nada (bloquear un dispositivo, cerrar un puerto, cambiar el router) y semanas en una red real.

## 🧩 Papel en A.R.M.O.R.

ARMOR-NETWORK es el ojo de la familia sobre la red local. Corre en una máquina de la red (la CM5 en el banco), mira lo que hay sin tocarlo e informa a [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER), que guarda los nombres, los dispositivos ocultos y vigilados y los cortes; el menú *Red* y el *Diseñador de red* de [ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) y la pantalla Red de [ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL) lo muestran, y Studio puede darle órdenes. Nunca configura el router ni ningún dispositivo.

| Habla con | Cómo | Para qué |
|---|---|---|
| ARMOR-SERVER | HTTP `POST` con el token de ingesta (`--server-url`) | entra el estado; las órdenes vuelven en la respuesta |
| MQTT | `--mqtt-url` (`mqtt://` o `mqtts://`) | el mismo mensaje también en el broker; las órdenes manuales no viajan así |
| ARMOR-STUDIO | a través del servidor | el menú Red y el Diseñador de red lo muestran y le dan órdenes |
| ARMOR-ANDROID-CONTROL | a través del servidor | la pantalla Red |
| ARMOR-COMMON | el contrato del mensaje y de las órdenes | `--validate` comprueba cada mensaje con él |

## 🏛️ Arquitectura

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-NETWORK architecture: the local network it looks at, the modules of the node and what it tells the server, Studio and the broker" width="100%">
</p>

## 🔒 Seguridad y protección

| Amenaza | Defensa |
|---|---|
| Escanear fuera de la casa o una red ajena | Solo rangos privados (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) y nunca más de 1024 direcciones (un /22); `--cidr` es siempre privado; la guarda es `check_scan_range`, no una opción |
| Romper algo frágil | Una lista de exclusión (`--skip IP`, repetible); no se envía nada a un equipo que no sea una pregunta; nunca un login, nunca un exploit; 12 conexiones a la vez leyendo unos cientos de bytes |
| Puertos abiertos de riesgo pasan inadvertidos | Se marcan: 21, 23, 3389, 5900, 6379, 3306, 5432, 7547 y 445 |
| Órdenes del servidor que inyecten comandos | Una lista cerrada: `scan_now`, `ping`, `traceroute`, `wake`, `ports`, `http`, `inspect`; como mucho 4 a la vez; un id de orden de letras, dígitos, `_` y `-` (32 como máximo); salida cortada a 2000; MAC comprobada; nada pasa por un shell; las órdenes llegan en la respuesta al mensaje del propio nodo, nunca como una conexión hecha al nodo |
| Se filtra el login de una inspección | Viaja sellado solo para este nodo, solo por Digest o HTTPS (nunca Basic por HTTP plano), solo al equipo cuyo certificado HTTPS se vio la primera vez, y nunca se repite en una respuesta; los accesos de fábrica que prueba salen de una lista fija |
| Una petición que sale de la casa | Una petición HTTPS a un servicio público fijo (`https://ipinfo.io/json` por defecto) cada pocos minutos, para la dirección pública; `--no-public-info` la apaga; `--dns-name` comprueba además que el nombre con el que se llega a la casa apunta a ella |

**Lo que nunca hace:** configurar el router, capturar paquetes, bloquear un equipo ni cerrar un puerto. Lo que es un equipo (su tipo, su sistema, su fabricante) es una suposición. Las notas de seguridad están en [docs/SAFETY.md](docs/SAFETY.md); no ha habido revisión independiente.

## 🔌 Interfaces

| Ruta | Autenticación | Qué hace |
|---|---|---|
| `armor/network/<node>/state` | mensaje | la interfaz, internet, cada equipo y los últimos eventos; lleva hallazgos, nunca órdenes |
| `python -m armor_network scan [--json]` | - | mira la red una vez y la imprime como tabla (o como el mensaje) |
| `python -m armor_network watch` | - | sigue vigilando; con `--server-url` y `--ingest-token` informa a ARMOR-SERVER, con `--mqtt-url` también al broker |
| `python -m armor_network demo [--count N]` | - | una casa inventada (entra un equipo, una cámara abre Telnet, cae internet): no se toca ninguna red |
| `python -m armor_network internet`  `oui <mac>` | - | una ronda de la comprobación de internet; quién fabricó una tarjeta de red |

Las órdenes de Studio (`scan_now`, `ping`, `traceroute`, `wake`, `ports`, `http`, `inspect`) las encola el servidor en las rutas `/api/v1/network/...` de ARMOR-SERVER y llegan al nodo en la respuesta a su mensaje; el contrato del mensaje y de las órdenes está en ARMOR-COMMON (111 vectores de conformidad). Mira [docs/MESSAGES.md](docs/MESSAGES.md) y [docs/USAGE.md](docs/USAGE.md).

## ⚙️ Configuración

| Ajuste | Por defecto | Qué hace |
|---|---|---|
| `--node-id` | network-1 | el nombre de este nodo en los mensajes (minúsculas, dígitos, `-` y `_`) |
| `--profile {quick,standard}` | quick | 17 o 44 puertos por equipo; un equipo nuevo se mira al instante, los demás cada cuarto de hora |
| `--no-ports`  `--skip IP`  `--cidr` | - | sin puertos; una dirección que no sondear nunca; la red a escanear (privada, como mucho 1024 direcciones) |
| `--scan-every`  `--internet-every` | 60 s  5 s | segundos entre barridos y entre comprobaciones de internet |
| `--server-url`  `--ingest-token`  `--mqtt-url`  `--mqtt-user` | - | adónde informa; el token de este nodo (Studio lo muestra) o el token de ingesta compartido, nunca escrito en un fichero |
| `--data-dir` | armor-network-data | dónde se guardan el inventario y las caídas entre ejecuciones |
| `--validate`  `--no-public-info`  `--public-info-url`  `--dns-name` | - | comprueba cada mensaje con ARMOR-COMMON; la consulta de la dirección pública (apagarla, su dirección, el nombre a comprobar) |

Todo se fija con opciones de línea de órdenes (mira [docs/USAGE.md](docs/USAGE.md), que muestra también la unidad systemd que lo mantiene en marcha). Una caída se declara tras tres rondas fallidas y termina tras dos buenas; los tres primeros barridos solo aprenden lo que hay.

## 🚀 Inicio rápido

**Requisitos:** Python 3.11+ (solo biblioteca estándar) y una máquina en la red a vigilar (Linux, Windows o macOS).

```powershell
python -m unittest discover -s tests                                                 # 181 pruebas: analizadores con muestras reales, la guarda de lo que se puede sondear, el inventario, internet, el agente completo contra una casa guionizada
python -m armor_network scan                                                         # mira la red una vez y la imprime (solo la red privada de esta máquina)
python -m armor_network watch --server-url http://127.0.0.1:8080 --ingest-token ...  # sigue vigilando e informa a ARMOR-SERVER
python -m armor_network demo --count 3                                               # una casa inventada: no se toca ninguna red
python tools/fetch_oui.py                                                            # renueva la tabla de fabricantes desde el registro IEEE (lo ejecuta una persona, de vez en cuando)
```

Mira el [uso](docs/USAGE.md) y el [diseño](docs/DESIGN.md).

## 🧪 Pruebas

```powershell
python -m unittest discover -s tests  # 181 pruebas
python -I tools/armor_ci_validate.py
```

| Fichero de pruebas | Pruebas | Qué cubre |
|---|---|---|
| `test_network.py` | 56 | los analizadores con muestras reales, la guarda de lo que se puede sondear, el inventario, internet y el agente contra una casa guionizada |
| `test_system_io_layer.py`  `test_system_io.py` | 39 | la capa de red real: vecinos, ecos, TCP, DNS |
| `test_orders.py`  `test_orders_edges.py` | 56 | las órdenes de Studio y sus límites |
| `test_cli_commands.py` | 20 | la línea de órdenes |
| `test_mqtt_out.py`  `test_seal.py` | 10 | la salida MQTT y los accesos sellados |

GitHub Actions ejecuta la base de A.R.M.O.R. en cada push y pull request: la validación del manifiesto, la versión, el registro de cambios y la paridad de los README, y luego la compilación y las pruebas del propio proyecto.

## 🏗️ Compilación y publicación

Es Python puro: no hay nada que compilar. La versión vive en `pyproject.toml`, en `armor.project.json` y en la insignia del README (leída del manifiesto); cada versión tiene su entrada en [CHANGELOG.md](CHANGELOG.md). Las versiones se publican en GitHub.

## 🩺 Resolución de problemas

| Ves | Porque | Haz |
|---|---|---|
| `... is not a private network` o `... has N addresses; at most 1024` | `--cidr` nombra un rango público o mayor que un /22 | usa un rango privado de como mucho 1024 direcciones |
| Pocos equipos o ninguno | la tabla de vecinos del sistema se llena sondeando cada dirección, y eso necesita permiso para hacer ping o leerla | ejecútalo con los permisos de un usuario que pueda hacer ping y leer la tabla de vecinos |
| Un equipo frágil se porta mal al escanearlo | no le gusta que se prueben puertos | añade `--skip <dirección>` (repetible) o `--no-ports` |
| Studio nunca recibe un mensaje | no se llega al servidor o este rechaza el token (el problema se cuenta como cualquier otro: `unreachable`, `unauthorized`) | revisa `--server-url` y el token (el de este nodo que muestra Studio, o el token de ingesta compartido) |

## 📂 Estructura del repositorio

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-NETWORK" width="100%">
</p>

<details>
<summary>Versión en texto del árbol</summary>

```text
ARMOR-NETWORK/
├── src/armor_network/
│   ├── ipnet.py oui.py                      qué se puede sondear; los fabricantes
│   ├── system_io.py sim_io.py               la red real; una guionizada
│   ├── neighbors.py parsers.py dnswire.py   lo que dicen el sistema y los equipos
│   ├── services.py                          puertos y suposiciones
│   ├── inventory.py internet.py             equipos y eventos; la máquina de caídas
│   ├── agent.py publisher.py mqtt_out.py    qué mirar; cómo informa
│   ├── orders.py seal.py                    órdenes de Studio; accesos sellados
│   ├── cli.py __main__.py                   scan, watch y demo
│   └── data/                                oui.tsv.gz, el registro IEEE
├── tests/                                   181 pruebas en 8 módulos
├── docs/                                    DESIGN, SAFETY, USAGE, MESSAGES
├── tools/                                   fetch_oui.py renueva el registro de fabricantes; las comprobaciones de CI y el lanzador
├── images/                                  banner, icono y las imágenes del README
├── .github/                                 flujo de CI, aviso al panel, plantillas de incidencias y pull requests
├── armor.project.json                       manifiesto: versión, función, madurez
├── pyproject.toml                           metadatos del paquete, entradas
├── CHANGELOG.md                             qué cambió en cada versión
├── run.sh run.bat                           arrancar, flujo compartido
├── build.sh build.bat                       construir y probar, flujo compartido
├── build-test.sh build-test.bat             construir, probar y empaquetar
├── test.sh test.bat                         solo las pruebas, nunca la versión
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Hoja de ruta y límites conocidos

**Límites conocidos hoy**

* No ha vigilado una casa entera durante semanas.
* Solo pregunta al router y nunca lo configura; lo que es un equipo (tipo, sistema, fabricante) es una suposición.
* No captura paquetes, así que no ve quién habla con quién; el tráfico por equipo y la detección de intrusos en sentido estricto necesitan los contadores del router o un puerto espejo.
* Sin revisión de seguridad independiente.

**Lo siguiente**

* Los contadores propios del router (tráfico por equipo), la captura de paquetes y semanas en una red real.
* Controlar algo (bloquear un equipo, cerrar un puerto, cambiar el router) no está previsto sin una revisión de riesgos documentada.

## 🌍 Idiomas

El README y los textos existen en inglés, español, francés, italiano, alemán, chino, japonés y portugués de Portugal.

## 🔗 Proyectos relacionados

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) es un sistema de seguridad perimetral hecho de repositorios independientes. Cada uno tiene su propia versión, sus propias pruebas y su propio README; esta es la familia:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratos de mensajes, validadores, vectores de conformidad y tipos generados
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Firmware de nodo de campo para ESP32-S3 con tres radares y su propio panel web
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protocolos de inversores y baterías solares y los mensajes de un nodo pasarela
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Nodo eléctrico: medidores, el mensaje de las lecturas de la red y las reglas de maniobra
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Nodo y panel de alarma: zonas, armado, retardos, sirena y PIN, con el servidor o sin él
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Panel táctil: el estado del sistema en una pantalla de pared, armar y reconocer, y el hogar del asistente de voz
* **ARMOR-NETWORK** (este repositorio) - La red local: sus dispositivos, internet y lo que cambia
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinador central: telemetría, alarmas, dispositivos, lecturas solares y cámaras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Consola web: cámaras, radar, alarmas, energía solar y el diseñador 2D/3D del emplazamiento
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Cliente de operador Android con radar 2D/3D en vivo
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - Cliente de operador para iPhone
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Política de inferencia visual que explica sus decisiones y nunca actúa
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zonas de cámara, máscaras y reglas de detección para la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenciones de voz sin conexión con una confirmación que no se puede falsificar
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Cajas, electrónica y la matriz de aceptación en banco
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Despliegue, el banco de pruebas de la CM5, copias de seguridad y TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulador de telemetría sin conexión con fallos repetibles
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Detecta, instala y actualiza los repositorios del propio ecosistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Arquitectura, base de seguridad y la matriz de capacidades

## 📚 Documentación

* [Diseño](docs/DESIGN.md): cómo mira, recuerda y decide el nodo
* [Seguridad](docs/SAFETY.md): qué puede tocar y qué nunca hace
* [Uso](docs/USAGE.md): las órdenes, las opciones y la unidad systemd
* [Mensajes](docs/MESSAGES.md): el mensaje del nodo y sus órdenes
* [Matriz de capacidades: qué está demostrado y qué no](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catálogo de proyectos: versiones y cómo dependen unos repositorios de otros](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Registro de cambios de este repositorio](CHANGELOG.md)

## 🤝 Contribuir y comunidad

* Antes de un pull request ejecuta `python -I tools/armor_ci_validate.py` y las pruebas: ambos deben pasar. Mira [CONTRIBUTING.md](CONTRIBUTING.md) y el [código de conducta](CODE_OF_CONDUCT.md).
* El README existe en ocho idiomas y se genera desde las fuentes de ARMOR-DOCS: un cambio de texto se hace allí.
* Un cambio en un mensaje entre componentes empieza en ARMOR-COMMON.
* No describas como funcionando en una placa lo que solo se ha compilado.
* Informa de una vulnerabilidad en privado: [SECURITY.md](SECURITY.md). Preguntas, ideas e informes: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCIA

GPL-3.0-or-later - véase [LICENSE](LICENSE).
