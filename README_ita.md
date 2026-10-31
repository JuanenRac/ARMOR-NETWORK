<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="Banner di ARMOR-NETWORK" width="100%">
</p>

# 🛰️ ARMOR-NETWORK

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  🇮🇹 <b>Italiano</b> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Sorveglia la rete locale: i dispositivi presenti, se internet c'è, cosa cambia e cosa è nuovo (un programma Python senza dipendenze; gira su una macchina della rete e riferisce ad ARMOR-SERVER)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 o successiva">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Linguaggio">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-187%20passing-2ea44f.svg" alt="Test">
  <img src="https://img.shields.io/badge/Version-0.1.6-0f6cbd.svg" alt="Versione">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturità">
</p>

---

**Controllo di onestà - cosa funziona oggi:** Lo scanner, l'inventario che dice cosa è cambiato, il controllo di internet, la ricerca dell'indirizzo pubblico, gli ordini da Studio e gli accessi sigillati sono provati su un computer contro una rete scriptata (187 test; ogni messaggio è accettato dal contratto di ARMOR-COMMON), e il programma gira come servizio sul banco di prova CM5, sorvegliando la rete reale su cui si trova il banco (un router, i telefoni e i nodi della casa). Non ha sorvegliato una casa intera per settimane, chiede solo al router e non lo configura mai, e cosa sia un dispositivo (il tipo, il sistema, il produttore) è una supposizione. Non cattura pacchetti: non può vedere chi parla con chi, e il traffico per dispositivo e il rilevamento delle intrusioni in senso stretto richiedono i contatori del router o una porta mirror, che è un passo successivo.

---

## 📋 In breve

| | |
|---|---|
| Versione | `0.1.6` |
| Maturità | Consolidato |
| Ruolo | Nodo della rete locale: cosa c'è in rete, cosa è cambiato, internet, ordini da Studio |
| Tecnologia | Python 3.11+, solo libreria standard |
| Test | 187 (`python -m unittest discover -s tests`) |
| Contratto | Messaggio `armor/network/<nodo>/state`, 111 vettori di conformità (messaggi e ordini) |
| Gira su | Una macchina della rete da sorvegliare (Linux, Windows o macOS); il banco di prova CM5 come servizio |
| Su hardware reale | Gira come servizio sul banco di prova CM5, sorvegliando la sua rete reale (un router, i telefoni e i nodi della casa) |
| Licenza | GPL-3.0-or-later |

**Vai a:** [Panoramica](#-panoramica) · [Architettura](#-architettura) · [Sicurezza](#-sicurezza-e-protezione) · [Interfacce](#-interfacce) · [Configurazione](#-configurazione) · [Avvio rapido](#-avvio-rapido) · [Test](#-test) · [Problemi](#-risoluzione-dei-problemi) · [Struttura](#-struttura-del-repository) · [Correlati](#-progetti-correlati)

## 🚦 Stato del progetto

Ogni riga è una parte di questo repository e il semaforo dice a che punto è oggi. È scritta in base a ciò che il repository può mostrare (test, compilazioni, esecuzioni), non a ciò che è previsto.

🟢 Fatto e verificato · 🟡 Funziona, con limiti noti · 🟠 Fatto a metà o non ancora verificato · 🔴 Non fatto o non funzionante

| Area | Stato | Cosa significa qui |
|---|---|---|
| Software | 🟢 | Lo scanner, l'inventario che dice cosa è cambiato, il controllo di internet, la ricerca dell'indirizzo pubblico e gli ordini di Studio girano come servizio sul banco di prova CM5. |
| Test | 🟢 | Superano 187 test contro una rete simulata da script, e ogni messaggio è accettato dal contratto di ARMOR-COMMON. |
| Protocolli e dati | 🟡 | Cosa sia un dispositivo (tipo, sistema, produttore) è un'ipotesi, e nulla cattura pacchetti: il traffico per dispositivo e il rilevamento di intrusioni in senso stretto non sono fatti. |
| Hardware | 🟡 | Sorveglia la rete reale del banco di prova CM5 (un router, i telefoni e i nodi di casa) ma non ha sorvegliato un'intera casa per settimane. |
| Sicurezza | 🟡 | Interroga soltanto il router e non lo configura mai; gli accessi sigillati sono testati sull'host e non c'è stata una revisione indipendente. |
| Integrazione | 🟡 | I suoi messaggi arrivano al server del banco di prova CM5 e a Studio; gli ordini di Studio sono provati contro una rete simulata da script. |
| Documentazione | 🟢 | Otto lingue e il registro delle modifiche sono aggiornati. |

## 🎯 Panoramica

* **Cosa c'è in rete:** la tabella dei vicini della macchina, un tocco a ogni indirizzo perché si riempia, un'eco a ogni dispositivo trovato (latenza e TTL) e ciò che i dispositivi annunciano di sé (mDNS, UPnP, NetBIOS, DNS inverso). Per ciascuno: indirizzo, MAC, produttore (dal registro IEEE, 40.000 blocchi), nome, tipo, sistema, porte aperte con ciò che dice ognuna e quando è stato visto la prima e l'ultima volta.
* **Porte:** una connessione TCP a 17 (o 44) porte di ogni dispositivo, dodici alla volta, leggendo al più poche centinaia di byte della risposta; mai un accesso, mai un exploit. Un dispositivo nuovo si guarda subito, gli altri ogni quarto d'ora.
* **Cosa cambia:** un dispositivo che compare (le prime tre scansioni imparano soltanto), tace o torna, cambia indirizzo, una porta che si apre o si chiude, e due macchine che rispondono per lo stesso indirizzo (soprattutto quello del router). Ogni evento ha un id, quindi si dice una volta sola.
* **Internet:** ogni pochi secondi un'eco al router, una connessione TCP, due domande DNS a risolutori scelti e una pagina web. Un'interruzione richiede tre giri per chiamarsi così e due per dirsi finita, si data dal primo giro fallito e si conta fino al primo buono, e dice di chi è la colpa: del gestore (il router risponde e nulla oltre) o di questa parte (anche il router non risponde). Latenza, perdita e le interruzioni delle ultime 24 ore.
* **Guarda solo la tua rete:** rifiuta ogni indirizzo non privato (10/8, 172.16/12, 192.168/16) e ogni intervallo più grande di un /22; un elenco di esclusione lo tiene lontano da ciò che è fragile; a un dispositivo non si invia nulla che non sia una domanda.
* **Il messaggio** `armor/network/<nodo>/state`: l'interfaccia, internet, ogni dispositivo e gli ultimi eventi; è nel contratto condiviso (111 vettori) e porta rilevazioni, mai comandi. `python -m armor_network scan` lo stampa come tabella, `watch` informa ARMOR-SERVER, `demo` recita una casa inventata (si unisce un dispositivo nuovo, una telecamera apre Telnet, internet cade e torna, qualcuno risponde per il router) senza toccare alcuna rete.
* **Dove si vede:** il menu Rete di ARMOR-STUDIO (i dispositivi, internet con le sue interruzioni e la latenza, il traffico e gli eventi; un amministratore dà un nome ai dispositivi e segna quelli noti, ciò che spegne l'allarme di un dispositivo nuovo), il Progettista di rete (il disegno della rete di casa, confrontato con ciò che è stato trovato e capace di disegnarlo) e la schermata Rete dell'app Android. ARMOR-SERVER genera gli allarmi.
* **Ordini da Studio:** una scansione subito, un ping, un traceroute, un wake-up, le porte o la pagina web di un dispositivo e un'ispezione con un accesso che dai; gli ordini arrivano nella risposta al messaggio del nodo stesso (mai come una connessione fatta verso il nodo), ognuno è controllato prima di fare qualcosa e nulla è eseguito tramite una shell.
* **Accessi che restano sicuri:** l'accesso di un'ispezione viaggia sigillato per questo solo nodo, è inviato solo via Digest o HTTPS (mai Basic su HTTP in chiaro), solo al dispositivo il cui certificato HTTPS è stato visto la prima volta, e non è mai rimandato in eco.
* **Il lato pubblico:** l'indirizzo pubblico della casa, chi lo dà e dove si trova (una richiesta HTTPS a un servizio pubblico fisso ogni pochi minuti; `--no-public-info` la spegne). Con `--dns-name` risolve anche il nome con cui si raggiunge la casa dall'esterno e dice se punta a quell'indirizzo.
* **Un servizio:** gira come unità systemd sul banco di prova CM5 (scritta a mano, vedi la guida all'uso) e tiene i suoi dati nella propria cartella.
* **Non ancora:** i contatori del router stesso (traffico per dispositivo), la cattura dei pacchetti, controllare qualcosa (bloccare un dispositivo, chiudere una porta, cambiare il router) e settimane su una rete reale.

## 🧩 Ruolo in A.R.M.O.R.

ARMOR-NETWORK è l'occhio della famiglia sulla rete locale. Gira su una macchina della rete (la CM5 sul banco), guarda cosa c'è senza toccarlo e riferisce ad [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER), che conserva i nomi, i dispositivi nascosti e sorvegliati e le interruzioni; il menu *Rete* e il *Progettista di rete* di [ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) e la schermata Rete di [ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL) lo mostrano, e Studio può dargli ordini. Non configura mai il router né alcun dispositivo.

| Parla con | Come | A che scopo |
|---|---|---|
| ARMOR-SERVER | `POST` HTTP con il token di ingestione (`--server-url`) | entra lo stato; gli ordini tornano nella risposta |
| MQTT | `--mqtt-url` (`mqtt://` o `mqtts://`) | lo stesso messaggio anche sul broker; gli ordini manuali non viaggiano così |
| ARMOR-STUDIO | tramite il server | il menu Rete e il progettista di rete lo mostrano e gli danno ordini |
| ARMOR-ANDROID-CONTROL | tramite il server | la schermata Rete |
| ARMOR-COMMON | il contratto del messaggio e degli ordini | `--validate` verifica ogni messaggio con esso |

## 🏛️ Architettura

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-NETWORK architecture: the local network it looks at, the modules of the node and what it tells the server, Studio and the broker" width="100%">
</p>

## 🔒 Sicurezza e protezione

| Minaccia | Difesa |
|---|---|
| Scansionare fuori casa o una rete altrui | Solo intervalli privati (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) e mai più di 1024 indirizzi (un /22); `--cidr` è sempre privato; la guardia è `check_scan_range`, non un'opzione |
| Rompere qualcosa di fragile | Una lista di esclusione (`--skip IP`, ripetibile); a un dispositivo non si manda nulla che non sia una domanda; mai un login, mai un exploit; 12 connessioni alla volta che leggono poche centinaia di byte |
| Porte aperte a rischio passano inosservate | Sono segnalate: 21, 23, 3389, 5900, 6379, 3306, 5432, 7547 e 445 |
| Ordini dal server che iniettano comandi | Un elenco chiuso: `scan_now`, `ping`, `traceroute`, `wake`, `ports`, `http`, `inspect`; al massimo 4 alla volta; un id d'ordine di lettere, cifre, `_` e `-` (32 al massimo); output tagliato a 2000; MAC verificato; nulla passa da una shell; gli ordini arrivano nella risposta al messaggio del nodo stesso, mai come connessione verso il nodo |
| Il login di un'ispezione trapela | Viaggia sigillato per questo solo nodo, solo con Digest o HTTPS (mai Basic su HTTP semplice), solo verso il dispositivo il cui certificato HTTPS è stato visto la prima volta, e non si ripete mai in una risposta; i login di fabbrica provati vengono da un elenco fisso |
| Una richiesta che esce di casa | Una richiesta HTTPS a un servizio pubblico fisso (`https://ipinfo.io/json` di default) ogni pochi minuti, per l'indirizzo pubblico; `--no-public-info` la spegne; `--dns-name` verifica anche che il nome con cui si raggiunge la casa punti a quell'indirizzo |

**Cosa non fa mai:** configurare il router, catturare pacchetti, bloccare un dispositivo o chiudere una porta. Ciò che è un dispositivo (tipo, sistema, produttore) è una supposizione. Le note di sicurezza sono in [docs/SAFETY.md](docs/SAFETY.md); non c'è stata una revisione indipendente.

## 🔌 Interfacce

| Rotta | Autenticazione | Cosa fa |
|---|---|---|
| `armor/network/<node>/state` | messaggio | l'interfaccia, internet, ogni dispositivo e gli ultimi eventi; porta rilievi, mai comandi |
| `python -m armor_network scan [--json]` | - | guarda la rete una volta e la stampa come tabella (o come messaggio) |
| `python -m armor_network watch` | - | continua a sorvegliare; con `--server-url` e `--ingest-token` informa ARMOR-SERVER, con `--mqtt-url` anche il broker |
| `python -m armor_network demo [--count N]` | - | una casa inventata (entra un dispositivo, una telecamera apre Telnet, cade internet): nessuna rete viene toccata |
| `python -m armor_network internet`  `oui <mac>` | - | un giro del controllo di internet; chi ha prodotto una scheda di rete |

Gli ordini da Studio (`scan_now`, `ping`, `traceroute`, `wake`, `ports`, `http`, `inspect`) sono messi in coda dalle rotte `/api/v1/network/...` di ARMOR-SERVER e arrivano al nodo nella risposta al suo messaggio; il contratto del messaggio e degli ordini è in ARMOR-COMMON (111 vettori di conformità). Vedi [docs/MESSAGES.md](docs/MESSAGES.md) e [docs/USAGE.md](docs/USAGE.md).

## ⚙️ Configurazione

| Impostazione | Predefinito | Cosa fa |
|---|---|---|
| `--node-id` | network-1 | il nome di questo nodo nei messaggi (minuscole, cifre, `-` e `_`) |
| `--profile {quick,standard}` | quick | 17 o 44 porte per dispositivo; un dispositivo nuovo si guarda subito, gli altri ogni quarto d'ora |
| `--no-ports`  `--skip IP`  `--cidr` | - | nessuna porta; un indirizzo da non sondare mai; la rete da scansionare (privata, al massimo 1024 indirizzi) |
| `--scan-every`  `--internet-every` | 60 s  5 s | secondi tra scansioni e controlli di internet |
| `--server-url`  `--ingest-token`  `--mqtt-url`  `--mqtt-user` | - | dove riferisce; il token di questo nodo (Studio lo mostra) o il token di ingestione condiviso, mai scritto in un file |
| `--data-dir` | armor-network-data | dove restano inventario e interruzioni tra le esecuzioni |
| `--validate`  `--no-public-info`  `--public-info-url`  `--dns-name` | - | verifica ogni messaggio con ARMOR-COMMON; la ricerca dell'indirizzo pubblico (spegnerla, il suo indirizzo, il nome da verificare) |

Tutto si imposta con opzioni da riga di comando (vedi [docs/USAGE.md](docs/USAGE.md), che mostra anche l'unità systemd che lo tiene in funzione). Un'interruzione si dichiara dopo tre giri falliti e termina dopo due buoni; le prime tre scansioni imparano soltanto cosa c'è.

## 🚀 Avvio rapido

**Requisiti:** Python 3.11+ (solo libreria standard) e una macchina nella rete da sorvegliare (Linux, Windows o macOS).

```powershell
python -m unittest discover -s tests                                                 # 187 test: parser con campioni reali, la guardia su cosa si può sondare, l'inventario, internet, l'intero agente contro una casa guidata
python -m armor_network scan                                                         # guarda la rete una volta e la stampa (solo la rete privata di questa macchina)
python -m armor_network watch --server-url http://127.0.0.1:8080 --ingest-token ...  # continua a sorvegliare e informa ARMOR-SERVER
python -m armor_network demo --count 3                                               # una casa inventata: nessuna rete viene toccata
python tools/fetch_oui.py                                                            # aggiorna la tabella dei produttori dal registro IEEE (la lancia una persona, ogni tanto)
```

Vedi l'[uso](docs/USAGE.md) e il [progetto](docs/DESIGN.md).

## 🧪 Test

```powershell
python -m unittest discover -s tests  # 187 test
python -I tools/armor_ci_validate.py
```

| File di test | Test | Cosa copre |
|---|---|---|
| `test_network.py` | 56 | i parser con campioni reali, la guardia su cosa si può sondare, l'inventario, internet e l'agente contro una casa guidata |
| `test_system_io_layer.py`  `test_system_io.py` | 39 | il livello della rete reale: vicini, echi, TCP, DNS |
| `test_orders.py`  `test_orders_edges.py` | 56 | gli ordini da Studio e i loro limiti |
| `test_cli_commands.py` | 20 | la riga di comando |
| `test_mqtt_out.py`  `test_seal.py` | 10 | l'uscita MQTT e gli accessi sigillati |
| `test_typing_behaviour.py` | 6 | il comportamento che le annotazioni di tipo conservano: la guardia della scansione, l'analizzatore degli ordini e le tabelle dei produttori |

GitHub Actions esegue la base A.R.M.O.R. a ogni push e pull request: la validazione di manifesto, versione, registro delle modifiche e parità dei README, poi la compilazione e i test del progetto. Anche i sorgenti superano il controllo dei tipi: `python -m mypy` (configurato in `pyproject.toml`) non segnala nulla, e `test_typing_behaviour.py` fissa il comportamento che le annotazioni conservano.

## 🏗️ Compilazione e rilascio

È Python puro: nulla da compilare. La versione risiede in `pyproject.toml`, in `armor.project.json` e nel badge del README (letto dal manifesto); ogni versione ha la sua voce in [CHANGELOG.md](CHANGELOG.md). Le versioni sono pubblicate su GitHub.

## 🩺 Risoluzione dei problemi

| Vedi | Perché | Fai |
|---|---|---|
| `... is not a private network` o `... has N addresses; at most 1024` | `--cidr` indica un intervallo pubblico o più grande di un /22 | usa un intervallo privato di al massimo 1024 indirizzi |
| Pochi o nessun dispositivo trovato | la tabella dei vicini del sistema si riempie sondando ogni indirizzo, e serve il permesso di ping o di lettura | eseguilo con i permessi di un utente che può fare ping e leggere la tabella dei vicini |
| Un dispositivo fragile si comporta male alla scansione | non gradisce che si provino le porte | aggiungi `--skip <indirizzo>` (ripetibile) o `--no-ports` |
| Studio non riceve mai un messaggio | il server non è raggiungibile o rifiuta il token (il problema si conta come gli altri: `unreachable`, `unauthorized`) | controlla `--server-url` e il token (quello di questo nodo che Studio mostra, o il token di ingestione condiviso) |

## 📂 Struttura del repository

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-NETWORK" width="100%">
</p>

<details>
<summary>Versione testuale dell'albero</summary>

```text
ARMOR-NETWORK/
├── src/armor_network/
│   ├── ipnet.py oui.py                      cosa si può sondare; i produttori
│   ├── system_io.py sim_io.py               la rete reale; una guidata
│   ├── neighbors.py parsers.py dnswire.py   cosa dicono il sistema e i dispositivi
│   ├── services.py                          porte e supposizioni
│   ├── inventory.py internet.py             dispositivi ed eventi; la macchina dei guasti
│   ├── agent.py publisher.py mqtt_out.py    cosa guardare; come riferisce
│   ├── orders.py seal.py                    ordini da Studio; accessi sigillati
│   ├── cli.py __main__.py                   scan, watch e demo
│   └── data/                                oui.tsv.gz, il registro IEEE
├── tests/                                   187 test in 9 moduli
├── docs/                                    DESIGN, SAFETY, USAGE, MESSAGES
├── tools/                                   fetch_oui.py aggiorna il registro dei produttori; i controlli CI e l'avviatore
├── images/                                  banner, icona e immagini del README
├── .github/                                 workflow CI, avviso alla dashboard, modelli per issue e pull request
├── armor.project.json                       manifesto: versione, ruolo, maturità
├── pyproject.toml                           metadati del pacchetto, ingressi
├── CHANGELOG.md                             cosa è cambiato in ogni versione
├── run.sh run.bat                           avvio, flusso condiviso
├── build.sh build.bat                       compila e prova, flusso condiviso
├── build-test.sh build-test.bat             compila, prova e impacchetta
├── test.sh test.bat                         solo i test, mai la versione
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Roadmap e limiti noti

**Limiti noti oggi**

* Non ha sorvegliato una casa intera per settimane.
* Interroga solo il router e non lo configura mai; ciò che è un dispositivo (tipo, sistema, produttore) è una supposizione.
* Non cattura pacchetti, quindi non vede chi parla con chi; il traffico per dispositivo e il rilevamento di intrusioni in senso stretto richiedono i contatori del router o una porta mirror.
* Nessuna revisione di sicurezza indipendente.

**Prossimi passi**

* I contatori propri del router (traffico per dispositivo), la cattura di pacchetti e settimane su una rete reale.
* Controllare qualcosa (bloccare un dispositivo, chiudere una porta, cambiare il router) non è previsto senza una revisione dei rischi documentata.

## 🌍 Lingue

Il README e i testi esistono in inglese, spagnolo, francese, italiano, tedesco, cinese, giapponese e portoghese europeo.

## 🔗 Progetti correlati

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) è un sistema di sicurezza perimetrale fatto di repository indipendenti. Ognuno ha la propria versione, i propri test e il proprio README; ecco la famiglia:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratti dei messaggi, validatori, vettori di conformità e tipi generati
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Firmware del nodo di campo per ESP32-S3 con tre radar e un proprio pannello web
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protocolli di inverter e batterie solari e messaggi di un nodo gateway
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Nodo elettrico: contatori, il messaggio delle letture della rete e le regole di manovra
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Nodo e centrale d'allarme: zone, inserimento, ritardi, sirena e PIN, con il server o senza
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Pannello touch: lo stato del sistema su uno schermo a parete, attivare e riconoscere gli allarmi, e la casa dell'assistente vocale
* **ARMOR-NETWORK** (questo repository) - La rete locale: i suoi dispositivi, internet e ciò che cambia
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinatore centrale: telemetria, allarmi, dispositivi, letture solari e telecamere
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Console web: telecamere, radar, allarmi, energia solare e progettista del sito 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Client Android dell'operatore con radar 2D/3D in tempo reale
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - Client operatore per iPhone
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Politica di inferenza visiva che spiega le sue decisioni e non agisce mai
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zone delle telecamere, maschere e regole di rilevamento per la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenti vocali offline con una conferma impossibile da falsificare
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Contenitori, elettronica e matrice di accettazione da banco
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Distribuzione, banco di prova CM5, backup e TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulatore di telemetria offline con guasti ripetibili
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Rileva, installa e aggiorna i repository stessi dell'ecosistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architettura, base di sicurezza e matrice delle capacità

## 📚 Documentazione

* [Progetto](docs/DESIGN.md): come il nodo guarda, ricorda e decide
* [Sicurezza](docs/SAFETY.md): cosa può toccare e cosa non fa mai
* [Uso](docs/USAGE.md): i comandi, le opzioni e l'unità systemd
* [Messaggi](docs/MESSAGES.md): il messaggio del nodo e i suoi ordini
* [Matrice delle capacità: cosa è provato e cosa no](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catalogo dei progetti: versioni e dipendenze tra i repository](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Cronologia delle modifiche di questo repository](CHANGELOG.md)

## 🤝 Contribuire e comunità

* Prima di una pull request esegui `python -I tools/armor_ci_validate.py` e i test: devono passare entrambi. Vedi [CONTRIBUTING.md](CONTRIBUTING.md) e il [codice di condotta](CODE_OF_CONDUCT.md).
* Il README esiste in otto lingue ed è generato dalle sorgenti in ARMOR-DOCS: una modifica al testo si fa lì.
* Una modifica a un messaggio tra componenti parte da ARMOR-COMMON.
* Non descrivere come funzionante su una scheda ciò che è stato solo compilato.
* Segnala una vulnerabilità in privato: [SECURITY.md](SECURITY.md). Domande, idee e segnalazioni: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTORE

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENZA

GPL-3.0-or-later - vedi [LICENSE](LICENSE).
