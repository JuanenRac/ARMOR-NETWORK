<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-NETWORK banner" width="100%">
</p>

# 🛰️ ARMOR-NETWORK

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  🇮🇹 <b>Italiano</b> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>

### Sorveglia la rete locale: i dispositivi che ci sono, se internet c'è, cosa cambia e cosa è nuovo (un programma Python senza dipendenze, in sola lettura; gira su una macchina della rete e riferisce ad ARMOR-SERVER)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-53-00E5FF.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-ff9800.svg" alt="Maturity">
</p>

---

**Controllo di onestà - cosa funziona oggi:** **Maturità: scaffolding.** Lo scanner, l'inventario che dice cosa è cambiato, il controllo di internet e il messaggio sono provati su un computer contro una rete simulata (53 test; ARMOR-COMMON accetta tutti i messaggi), e il programma è stato eseguito una volta su una rete reale, con un router e un telefono. Non ha sorvegliato una casa intera per giorni, al router chiede soltanto e non lo configura mai, e ciò che è un dispositivo (tipo, sistema, produttore) è un'ipotesi. Non cattura pacchetti: non vede chi parla con chi, e il traffico per dispositivo e il rilevamento delle intrusioni in senso stretto richiedono i contatori del router o una porta mirror, che è un passo successivo.

---

## 🎯 Panoramica

* **Cosa c'è in rete:** la tabella dei vicini della macchina, un tocco a ogni indirizzo perché si riempia, un'eco a ogni dispositivo trovato (latenza e TTL) e ciò che i dispositivi annunciano di sé (mDNS, UPnP, NetBIOS, DNS inverso). Per ciascuno: indirizzo, MAC, produttore (dal registro IEEE, 40.000 blocchi), nome, tipo, sistema, porte aperte con ciò che dice ognuna e quando è stato visto la prima e l'ultima volta.
* **Porte:** una connessione TCP a 17 (o 44) porte di ogni dispositivo, dodici alla volta, leggendo al più poche centinaia di byte della risposta; mai un accesso, mai un exploit. Un dispositivo nuovo si guarda subito, gli altri ogni quarto d'ora.
* **Cosa cambia:** un dispositivo che compare (la prima scansione impara soltanto), tace o torna, cambia indirizzo, una porta che si apre o si chiude, e due macchine che rispondono per lo stesso indirizzo (soprattutto quello del router). Ogni evento ha un id, quindi si dice una volta sola.
* **Internet:** ogni pochi secondi un'eco al router, una connessione TCP, due domande DNS a risolutori scelti e una pagina web. Un'interruzione richiede tre giri per chiamarsi così e due per dirsi finita, si data dal primo giro fallito e si conta fino al primo buono, e dice di chi è la colpa: del gestore (il router risponde e nulla oltre) o di questa parte (anche il router non risponde). Latenza, perdita e le interruzioni delle ultime 24 ore.
* **Guarda solo la tua rete:** rifiuta ogni indirizzo non privato (10/8, 172.16/12, 192.168/16) e ogni intervallo più grande di un /22; un elenco di esclusione lo tiene lontano da ciò che è fragile; a un dispositivo non si invia nulla che non sia una domanda.
* **Il messaggio** `armor/network/<nodo>/state`: l'interfaccia, internet, ogni dispositivo e gli ultimi eventi; è nel contratto condiviso (330 vettori) e porta rilevazioni, mai comandi. `python -m armor_network scan` lo stampa come tabella, `watch` informa ARMOR-SERVER, `demo` recita una casa inventata (si unisce un dispositivo nuovo, una telecamera apre Telnet, internet cade e torna, qualcuno risponde per il router) senza toccare alcuna rete.
* **Dove si vede:** il menu Rete di ARMOR-STUDIO (i dispositivi, internet con le sue interruzioni e la latenza, il traffico e gli eventi; un amministratore dà un nome ai dispositivi e segna quelli noti, ciò che spegne l'allarme di un dispositivo nuovo), il Progettista di rete (il disegno della rete di casa, confrontato con ciò che è stato trovato e capace di disegnarlo) e la schermata Rete dell'app Android. ARMOR-SERVER genera gli allarmi.
* **Non ancora:** i contatori del router stesso (traffico per dispositivo), la cattura dei pacchetti, controllare qualcosa (bloccare un dispositivo, chiudere una porta, cambiare il router) e settimane su una rete reale.

## 📂 Struttura del repository

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

## 🛠️ Ambiente di sviluppo

```bash
python -m unittest discover -s tests                  # 53 tests: the parsers with real samples, the guard on what may be probed, the inventory, the internet, the whole agent against a scripted house
python -m armor_network scan                          # look at the network once and print it (only the private network of this machine)
python -m armor_network watch --server-url http://127.0.0.1:8080 --ingest-token ...    # keep watching and tell ARMOR-SERVER
python -m armor_network demo --count 3                # a made-up house: nothing on any network is touched
python tools/fetch_oui.py                             # refresh the table of makers from the IEEE register (run by a person, now and then)
```

See the [usage](docs/USAGE.md) and the [design](docs/DESIGN.md).

Vedi il [progetto](docs/DESIGN.md), le [note di sicurezza](docs/SAFETY.md), l'[uso](docs/USAGE.md) e i [messaggi](docs/MESSAGES.md).

## 🔗 Progetti correlati

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) è un sistema di sicurezza perimetrale fatto di repository indipendenti. Ognuno ha la propria versione, i propri test e il proprio README; ecco la famiglia:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratti dei messaggi, validatori, vettori di conformità e tipi generati
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - Firmware del nodo di campo per ESP32-S3 con tre radar e un proprio pannello web
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - Protocolli di inverter e batterie solari e messaggi di un nodo gateway
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - Nodo elettrico: contatori, il messaggio delle letture della rete e le regole di manovra
* **[ARMOR-HMI](https://github.com/JuanenRac/ARMOR-HMI)** - Pannello touch: lo stato del sistema su uno schermo a parete, attivare e riconoscere gli allarmi, e la casa dell'assistente vocale
* **ARMOR-NETWORK** (questo repository) - La rete locale: i suoi dispositivi, internet e ciò che cambia
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinatore centrale: telemetria, allarmi, dispositivi, letture solari e telecamere
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Console web: telecamere, radar, allarmi, energia solare e progettista del sito 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Client Android dell'operatore con radar 2D/3D in tempo reale
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Politica di inferenza visiva che spiega le sue decisioni e non agisce mai
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenti vocali offline con una conferma impossibile da falsificare
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Contenitori, elettronica e matrice di accettazione da banco
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Distribuzione, banco di prova CM5, backup e TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulatore di telemetria offline con guasti ripetibili
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Rileva, installa e aggiorna i repository stessi dell'ecosistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architettura, base di sicurezza e matrice delle capacità

## 📚 Documentazione e comunità

Dove leggere di più:

* [Matrice delle capacità: cosa è provato e cosa no](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catalogo dei progetti: versioni e dipendenze tra i repository](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Cronologia delle modifiche di questo repository](CHANGELOG.md)
* [Licenza (GPL-3.0-or-later)](LICENSE)
* Domande, idee e segnalazioni: electrohobby3d@gmail.com

## 👤 AUTORE

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENZA

GPL-3.0-or-later - vedi [LICENSE](LICENSE).
