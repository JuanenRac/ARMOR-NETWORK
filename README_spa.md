<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-NETWORK banner" width="100%">
</p>

# 🛰️ ARMOR-NETWORK

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  🇪🇸 <b>Español</b> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>

### Vigila la red local: los dispositivos que hay, si hay internet, qué cambia y qué es nuevo (un programa de Python sin dependencias, de solo lectura; se ejecuta en una máquina de la red y informa a ARMOR-SERVER)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-53-00E5FF.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-ff9800.svg" alt="Maturity">
</p>

---

**Comprobación de honestidad - qué funciona hoy:** **Madurez: scaffolding.** El escáner, el inventario que dice qué ha cambiado, la comprobación de internet y el mensaje se prueban en un ordenador contra una red simulada (53 pruebas; ARMOR-COMMON acepta todos los mensajes), y el programa se ha ejecutado una vez en una red real, que tenía un router y un móvil. No ha vigilado una casa entera durante días, al router solo le pregunta y nunca lo configura, y lo que es un dispositivo (su tipo, su sistema, su fabricante) es una suposición. No captura paquetes: no ve quién habla con quién, y el tráfico por dispositivo y la detección de intrusiones en sentido estricto necesitan los contadores del router o un puerto espejo, que es un paso posterior.

---

## 🎯 Descripción general

* **Qué hay en la red:** la tabla de vecinos de la máquina, un toque a cada dirección para que se llene, un eco a cada dispositivo encontrado (latencia y TTL) y lo que los dispositivos anuncian de sí mismos (mDNS, UPnP, NetBIOS, DNS inverso). De cada uno: dirección, MAC, fabricante (del registro de la IEEE, 40.000 bloques), nombre, tipo, sistema, puertos abiertos con lo que dice cada uno y cuándo se vio por primera y por última vez.
* **Puertos:** una conexión TCP a 17 (o 44) puertos de cada dispositivo, de doce en doce, leyendo como mucho unos cientos de bytes de lo que responde; nunca un inicio de sesión, nunca un exploit. Un dispositivo nuevo se mira enseguida, los demás cada cuarto de hora.
* **Qué cambia:** un dispositivo que aparece (el primer barrido solo aprende), calla o vuelve, cambia de dirección, un puerto que se abre o se cierra, y dos máquinas que responden por una misma dirección (sobre todo la del router). Cada evento tiene un id, así que se cuenta una vez.
* **Internet:** cada pocos segundos un eco al router, una conexión TCP, dos preguntas DNS a resolvedores elegidos y una página web. Un corte necesita tres rondas para llamarse así y dos para darse por terminado, se fecha desde su primera ronda fallida y se cuenta hasta la primera buena, y dice de quién es la culpa: del operador (el router responde y nada más allá) o de este lado (el router tampoco responde). Latencia, pérdida y los cortes de las últimas 24 horas.
* **Solo mira tu propia red:** rechaza cualquier dirección que no sea privada (10/8, 172.16/12, 192.168/16) y cualquier rango mayor que un /22; una lista de exclusión lo mantiene lejos de lo frágil; a un dispositivo no se le envía nada que no sea una pregunta.
* **El mensaje** `armor/network/<nodo>/state`: la interfaz, internet, cada dispositivo y los últimos eventos; está en el contrato compartido (330 vectores) y lleva hallazgos, nunca órdenes. `python -m armor_network scan` lo imprime como tabla, `watch` informa a ARMOR-SERVER y `demo` representa una casa inventada (se une un dispositivo nuevo, una cámara abre Telnet, se cae internet y vuelve, alguien responde por el router) sin tocar ninguna red.
* **Dónde se ve:** el menú Red de ARMOR-STUDIO (los dispositivos, internet con sus cortes y su latencia, el tráfico y los eventos; un administrador pone nombre a los dispositivos y marca los conocidos, que es lo que apaga la alarma de un dispositivo nuevo), el Diseñador de red (el dibujo de la red de la casa, comparado con lo encontrado y capaz de dibujarlo) y la pantalla Red de la app Android. ARMOR-SERVER genera las alarmas.
* **Todavía no:** los contadores del propio router (tráfico por dispositivo), la captura de paquetes, controlar nada (bloquear un dispositivo, cerrar un puerto, cambiar el router) y semanas en una red real.

## 📂 Estructura del repositorio

```text
ARMOR-NETWORK/
├── src/armor_network/  ipnet (what may be probed), oui (makers), neighbors + parsers + dnswire (what the system and the devices say), services (ports and guesses), inventory (devices and their events),
│                       internet (the outage state machine), agent (what to look at and how often), system_io (the real network), sim_io (a scripted one), publisher, cli
│   └── data/           oui.tsv.gz, the IEEE register of makers
├── tools/              fetch_oui.py
├── tests/              test_network.py
├── docs/               DESIGN, SAFETY, USAGE, MESSAGES
└── images/             brand assets
```

## 🛠️ Entorno de desarrollo

```bash
python -m unittest discover -s tests                  # 53 tests: the parsers with real samples, the guard on what may be probed, the inventory, the internet, the whole agent against a scripted house
python -m armor_network scan                          # look at the network once and print it (only the private network of this machine)
python -m armor_network watch --server-url http://127.0.0.1:8080 --ingest-token ...    # keep watching and tell ARMOR-SERVER
python -m armor_network demo --count 3                # a made-up house: nothing on any network is touched
python tools/fetch_oui.py                             # refresh the table of makers from the IEEE register (run by a person, now and then)
```

See the [usage](docs/USAGE.md) and the [design](docs/DESIGN.md).

Véanse el [diseño](docs/DESIGN.md), las [notas de seguridad](docs/SAFETY.md), el [uso](docs/USAGE.md) y los [mensajes](docs/MESSAGES.md).

## 🔗 Proyectos relacionados

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) es un sistema de seguridad perimetral hecho de repositorios independientes. Cada uno tiene su propia versión, sus propias pruebas y su propio README; esta es la familia:

* **[ARMOR-COMMON](../ARMOR-COMMON)** - Contratos de mensajes, validadores, vectores de conformidad y tipos generados
* **[ARMOR-RADAR](../ARMOR-RADAR)** - Firmware del nodo de campo para ESP32-S3 con tres radares y su propio panel web
* **[ARMOR-SOLAR](../ARMOR-SOLAR)** - Protocolos de inversores y baterías solares y los mensajes de un nodo pasarela
* **[ARMOR-ELECTRICAL](../ARMOR-ELECTRICAL)** - Nodo eléctrico: contadores, el mensaje de las lecturas de la red y las reglas para maniobrar
* **ARMOR-NETWORK** (este repositorio) - La red local: sus dispositivos, internet y lo que cambia
* **[ARMOR-SERVER](../ARMOR-SERVER)** - Coordinador central: telemetría, alarmas, dispositivos, lecturas solares y cámaras
* **[ARMOR-STUDIO](../ARMOR-STUDIO)** - Consola web: cámaras, radar, alarmas, energía solar y el diseñador de sitio 2D/3D
* **[ARMOR-ANDROID-CONTROL](../ARMOR-ANDROID-CONTROL)** - Cliente Android del operador con radar 2D/3D en vivo
* **[ARMOR-SERVER-AI](../ARMOR-SERVER-AI)** - Política de inferencia visual que explica sus decisiones y nunca actúa
* **[ARMOR-VOICE-AI](../ARMOR-VOICE-AI)** - Intenciones de voz sin conexión con una confirmación imposible de falsificar
* **[ARMOR-HARDWARE](../ARMOR-HARDWARE)** - Cajas, electrónica y la matriz de aceptación en banco
* **[ARMOR-DEVOPS](../ARMOR-DEVOPS)** - Despliegue, el banco de pruebas de la CM5, copias de seguridad y TLS
* **[ARMOR-SIMULATOR](../ARMOR-SIMULATOR)** - Simulador de telemetría sin conexión con fallos repetibles
* **[ARMOR-DOCS](../ARMOR-DOCS)** - Arquitectura, base de seguridad y la matriz de capacidades

## 📚 Documentación y comunidad

Dónde leer más:

* [Matriz de capacidades: qué está probado y qué no](../ARMOR-DOCS/docs/CAPABILITY_MATRIX.md)
* [Catálogo de proyectos: versiones y cómo dependen unos de otros](../ARMOR-DOCS/docs/PROJECT_CATALOG.md)
* [Historial de cambios de este repositorio](CHANGELOG.md)
* [Licencia (GPL-3.0-or-later)](LICENSE)
* Preguntas, ideas e informes: electrohobby3d@gmail.com

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCIA

GPL-3.0-or-later - véase [LICENSE](LICENSE).
