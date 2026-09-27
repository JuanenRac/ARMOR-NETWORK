<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-NETWORK banner" width="100%">
</p>

# 🛰️ ARMOR-NETWORK

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  🇩🇪 <b>Deutsch</b> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>

### Überwacht das lokale Netzwerk: welche Geräte es gibt, ob das Internet da ist, was sich ändert und was neu ist (ein Python-Programm ohne Abhängigkeiten, nur lesend; es läuft auf einem Rechner des Netzwerks und meldet an ARMOR-SERVER)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-53-00E5FF.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-ff9800.svg" alt="Maturity">
</p>

---

**Ehrlichkeitsprüfung - was heute läuft:** **Reife: Scaffolding.** Der Scanner, das Inventar, das sagt, was sich geändert hat, die Internetprüfung und die Nachricht werden auf einem Rechner gegen ein gestelltes Netzwerk getestet (53 Tests; ARMOR-COMMON akzeptiert jede Nachricht), und das Programm lief einmal in einem echten Netzwerk mit einem Router und einem Handy. Es hat noch kein ganzes Haus tagelang beobachtet, es fragt den Router nur und konfiguriert ihn nie, und was ein Gerät ist (Art, System, Hersteller), ist eine Vermutung. Es zeichnet keine Pakete auf: Es sieht nicht, wer mit wem spricht, und Verkehr je Gerät sowie Einbruchserkennung im engeren Sinn brauchen die Zähler des Routers oder einen Mirror-Port, was ein späterer Schritt ist.

---

## 🎯 Überblick

* **Was im Netzwerk ist:** die Nachbartabelle des Rechners, ein Anstupsen jeder Adresse, damit sie sich füllt, ein Echo an jedes gefundene Gerät (Latenz und TTL) und was Geräte über sich selbst ankündigen (mDNS, UPnP, NetBIOS, Reverse-DNS). Je Gerät: Adresse, MAC, Hersteller (aus dem IEEE-Register mit 40.000 Blöcken), Name, Art, System, offene Ports mit dem, was jeder sagt, und wann es zuerst und zuletzt gesehen wurde.
* **Ports:** eine TCP-Verbindung zu 17 (oder 44) Ports je Gerät, zwölf gleichzeitig, mit höchstens einigen hundert gelesenen Bytes der Antwort; nie ein Login, nie ein Exploit. Ein neues Gerät wird sofort angesehen, die anderen alle Viertelstunde.
* **Was sich ändert:** ein Gerät, das auftaucht (der erste Scan lernt nur), verstummt oder zurückkommt, seine Adresse ändert, ein Port, der sich öffnet oder schließt, und zwei Rechner, die für eine Adresse antworten (vor allem die des Routers). Jedes Ereignis hat eine ID und wird daher nur einmal gemeldet.
* **Das Internet:** alle paar Sekunden ein Echo an den Router, eine TCP-Verbindung, zwei DNS-Fragen an gewählte Resolver und eine Webseite. Ein Ausfall braucht drei Runden, um so zu heißen, und zwei, um beendet zu sein, wird ab der ersten fehlgeschlagenen Runde datiert und bis zur ersten guten gezählt und sagt, wessen Schuld es ist: die des Anbieters (der Router antwortet, dahinter nichts) oder die dieser Seite (auch der Router antwortet nicht). Latenz, Verlust und die Ausfälle der letzten 24 Stunden.
* **Es sieht nur Ihr eigenes Netzwerk:** es verweigert jede nicht private Adresse (10/8, 172.16/12, 192.168/16) und jeden Bereich über /22; eine Ausschlussliste hält es von Empfindlichem fern; an ein Gerät wird nichts gesendet, was keine Frage ist.
* **Die Nachricht** `armor/network/<Knoten>/state`: die Schnittstelle, das Internet, jedes Gerät und die letzten Ereignisse; sie steht im gemeinsamen Vertrag (330 Vektoren) und trägt Befunde, nie Befehle. `python -m armor_network scan` druckt sie als Tabelle, `watch` meldet an ARMOR-SERVER, `demo` spielt ein erfundenes Haus (ein neues Gerät kommt hinzu, eine Kamera öffnet Telnet, das Internet fällt aus und kommt zurück, jemand antwortet für den Router) ohne ein Netzwerk zu berühren.
* **Wo man es sieht:** das Netzwerk-Menü von ARMOR-STUDIO (die Geräte, das Internet mit Ausfällen und Latenz, der Datenverkehr und die Ereignisse; ein Administrator benennt Geräte und markiert bekannte, was den Alarm eines neuen Geräts beruhigt), der Netzwerkplaner (die Zeichnung des Hausnetzwerks, verglichen mit dem Gefundenen und fähig, es zu zeichnen) und der Netzwerk-Bildschirm der Android-App. ARMOR-SERVER löst die Alarme aus.
* **Noch nicht:** die Zähler des Routers selbst (Verkehr je Gerät), Paketmitschnitt, irgendetwas steuern (ein Gerät sperren, einen Port schließen, den Router ändern) und Wochen in einem echten Netzwerk.

## 📂 Struktur des Repositorys

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

## 🛠️ Entwicklungsumgebung

```bash
python -m unittest discover -s tests                  # 53 tests: the parsers with real samples, the guard on what may be probed, the inventory, the internet, the whole agent against a scripted house
python -m armor_network scan                          # look at the network once and print it (only the private network of this machine)
python -m armor_network watch --server-url http://127.0.0.1:8080 --ingest-token ...    # keep watching and tell ARMOR-SERVER
python -m armor_network demo --count 3                # a made-up house: nothing on any network is touched
python tools/fetch_oui.py                             # refresh the table of makers from the IEEE register (run by a person, now and then)
```

See the [usage](docs/USAGE.md) and the [design](docs/DESIGN.md).

Siehe den [Entwurf](docs/DESIGN.md), die [Sicherheitshinweise](docs/SAFETY.md), die [Benutzung](docs/USAGE.md) und die [Nachrichten](docs/MESSAGES.md).

## 🔗 Verwandte Projekte

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) ist ein Perimeter-Sicherheitssystem aus unabhängigen Repositorys. Jedes hat eine eigene Version, eigene Tests und ein eigenes README; hier ist die Familie:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Nachrichtenverträge, Validierer, Konformitätsvektoren und generierte Typen
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - Feldknoten-Firmware für ESP32-S3 mit drei Radaren und eigenem Web-Panel
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - Protokolle für Solar-Wechselrichter und -Batterien und die Nachrichten eines Gateway-Knotens
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - Elektroknoten: Zähler, die Nachricht der Netzmesswerte und die Regeln fürs Schalten
* **ARMOR-NETWORK** (dieses Repository) - Das lokale Netzwerk: seine Geräte, das Internet und was sich ändert
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Zentraler Koordinator: Telemetrie, Alarme, Geräte, Solarmesswerte und Kameras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Web-Konsole: Kameras, Radar, Alarme, Solarenergie und 2D/3D-Standortdesigner
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Android-Bedienclient mit Live-Radar in 2D/3D
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Visuelle Inferenzrichtlinie, die ihre Entscheidungen erklärt und nie handelt
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Offline-Sprachabsichten mit einer nicht fälschbaren Bestätigung
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Gehäuse, Elektronik und die Abnahmematrix am Prüfstand
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Bereitstellung, CM5-Prüfstand, Backup und TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Offline-Telemetriesimulator mit wiederholbaren Fehlern
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Erkennt, installiert und aktualisiert die eigenen Repositories des Ökosystems
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architektur, Sicherheitsgrundlage und die Fähigkeitsmatrix

## 📚 Dokumentation und Community

Hier gibt es mehr zu lesen:

* [Fähigkeitsmatrix: was belegt ist und was nicht](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Projektkatalog: Versionen und wie die Repositorys voneinander abhängen](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Änderungsverlauf dieses Repositorys](CHANGELOG.md)
* [Lizenz (GPL-3.0-or-later)](LICENSE)
* Fragen, Ideen und Meldungen: electrohobby3d@gmail.com

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LIZENZ

GPL-3.0-or-later - siehe [LICENSE](LICENSE).
