<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="Bannière d'ARMOR-NETWORK" width="100%">
</p>

# 🛰️ ARMOR-NETWORK

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  🇫🇷 <b>Français</b> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Surveille le réseau local : les appareils présents, si internet est là, ce qui change et ce qui est nouveau (un programme Python sans dépendances ; il tourne sur une machine du réseau et rapporte à ARMOR-SERVER)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 ou ultérieure">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Langage">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-181%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.4-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturité">
</p>

---

**Vérification d'honnêteté - ce qui fonctionne aujourd'hui :** Le scanner, l'inventaire qui dit ce qui a changé, le contrôle d'internet, la recherche de l'adresse publique, les ordres depuis Studio et les identifiants scellés sont testés sur un ordinateur contre un réseau scripté (181 tests ; chaque message est accepté par le contrat d'ARMOR-COMMON), et le programme tourne comme service sur le banc de test CM5, en surveillant le vrai réseau où se trouve le banc (un routeur, les téléphones et les nœuds de la maison). Il n'a pas surveillé une maison entière pendant des semaines, il ne fait que demander au routeur et ne le configure jamais, et ce qu'est un appareil (son type, son système, son fabricant) est une supposition. Il ne capture pas de paquets : il ne voit pas qui parle à qui, et le trafic par appareil et la détection d'intrusion au sens strict demandent les compteurs du routeur ou un port miroir, ce qui est une étape ultérieure.

---

## 📋 En un coup d'œil

| | |
|---|---|
| Version | `0.1.4` |
| Maturité | Établi |
| Rôle | Nœud du réseau local : ce qu'il y a sur le réseau, ce qui a changé, internet, ordres de Studio |
| Technologie | Python 3.11+, bibliothèque standard seule |
| Tests | 181 (`python -m unittest discover -s tests`) |
| Contrat | Message `armor/network/<nœud>/state`, 111 vecteurs de conformité (messages et ordres) |
| Fonctionne sur | Une machine du réseau à surveiller (Linux, Windows ou macOS) ; le banc d'essai CM5 en service |
| Sur matériel réel | Tourne comme service sur le banc de test CM5, en surveillant son vrai réseau (un routeur, les téléphones et les nœuds de la maison) |
| Licence | GPL-3.0-or-later |

**Aller à :** [Présentation](#-présentation) · [Architecture](#-architecture) · [Sécurité](#-sécurité-et-protection) · [Interfaces](#-interfaces) · [Configuration](#-configuration) · [Démarrage rapide](#-démarrage-rapide) · [Tests](#-tests) · [Dépannage](#-dépannage) · [Structure](#-structure-du-dépôt) · [Liés](#-projets-liés)

## 🚦 État du projet

Chaque ligne est une partie de ce dépôt et le feu dit où elle en est aujourd'hui. Elle est écrite d'après ce que le dépôt peut montrer (tests, compilations, exécutions), pas d'après ce qui est prévu.

🟢 Fait et vérifié · 🟡 Fonctionne, avec des limites connues · 🟠 À moitié fait ou pas encore vérifié · 🔴 Pas fait ou ne fonctionne pas

| Domaine | État | Ce que cela veut dire ici |
|---|---|---|
| Logiciel | 🟢 | Le scanner, l'inventaire qui dit ce qui a changé, le contrôle d'internet, la recherche de l'adresse publique et les ordres de Studio tournent comme service sur le banc d'essai CM5. |
| Tests | 🟢 | 181 tests réussissent contre un réseau scénarisé, et chaque message est accepté par le contrat d'ARMOR-COMMON. |
| Protocoles et données | 🟡 | Ce qu'est un appareil (son type, son système, son fabricant) est une supposition, et rien ne capture de paquets : le trafic par appareil et la détection d'intrusion au sens strict ne sont pas faits. |
| Matériel | 🟡 | Il surveille le réseau réel du banc d'essai CM5 (un routeur, les téléphones et les nœuds de la maison) mais n'a pas surveillé une maison entière pendant des semaines. |
| Sécurité | 🟡 | Il ne fait qu'interroger le routeur et ne le configure jamais ; les identifiants scellés sont testés sur l'hôte et il n'y a pas eu de revue indépendante. |
| Intégration | 🟡 | Ses messages arrivent au serveur du banc d'essai CM5 et à Studio ; les ordres de Studio sont testés contre un réseau scénarisé. |
| Documentation | 🟢 | Huit langues et le journal des modifications sont à jour. |

## 🎯 Présentation

* **Ce qu'il y a sur le réseau :** la table de voisins de la machine, un coup sur chaque adresse pour qu'elle se remplisse, un écho à chaque appareil trouvé (latence et TTL) et ce que les appareils annoncent d'eux-mêmes (mDNS, UPnP, NetBIOS, DNS inverse). Pour chacun : adresse, MAC, fabricant (du registre de l'IEEE, 40 000 blocs), nom, type, système, ports ouverts avec ce que dit chacun, et quand il a été vu pour la première et la dernière fois.
* **Ports :** une connexion TCP à 17 (ou 44) ports de chaque appareil, douze à la fois, en lisant au plus quelques centaines d'octets de la réponse ; jamais de connexion, jamais d'exploit. Un nouvel appareil est examiné aussitôt, les autres tous les quarts d'heure.
* **Ce qui change :** un appareil qui apparaît (les trois premiers balayages ne font qu'apprendre), se tait ou revient, change d'adresse, un port qui s'ouvre ou se ferme, et deux machines qui répondent pour une même adresse (surtout celle du routeur). Chaque événement a un id, il n'est donc dit qu'une fois.
* **Internet :** toutes les quelques secondes un écho au routeur, une connexion TCP, deux questions DNS à des résolveurs choisis et une page web. Une coupure demande trois tours pour être déclarée et deux pour être finie, est datée du premier tour raté et comptée jusqu'au premier bon, et dit à qui est la faute : au fournisseur (le routeur répond et rien au-delà) ou à ce côté-ci (le routeur ne répond pas non plus). Latence, perte et les coupures des dernières 24 heures.
* **Il ne regarde que votre propre réseau :** il refuse toute adresse non privée (10/8, 172.16/12, 192.168/16) et toute plage plus grande qu'un /22 ; une liste d'exclusion le tient éloigné de ce qui est fragile ; rien n'est envoyé à un appareil qui ne soit une question.
* **Le message** `armor/network/<nœud>/state` : l'interface, internet, chaque appareil et les derniers événements ; il est dans le contrat partagé (111 vecteurs) et porte des constats, jamais des ordres. `python -m armor_network scan` l'imprime en tableau, `watch` informe ARMOR-SERVER, `demo` joue une maison inventée (un nouvel appareil arrive, une caméra ouvre Telnet, internet tombe et revient, quelqu'un répond pour le routeur) sans toucher aucun réseau.
* **Où on le voit :** le menu Réseau d'ARMOR-STUDIO (les appareils, internet avec ses coupures et sa latence, le trafic et les événements ; un administrateur nomme les appareils et marque les connus, ce qui apaise l'alarme d'un nouvel appareil), le Concepteur de réseau (le dessin du réseau de la maison, comparé à ce qui a été trouvé et capable de le dessiner) et l'écran Réseau de l'app Android. ARMOR-SERVER déclenche les alarmes.
* **Ordres depuis Studio :** un balayage tout de suite, un ping, un traceroute, un réveil réseau, les ports ou la page web d'un appareil et une inspection avec un identifiant que vous donnez ; les ordres arrivent dans la réponse au propre message du nœud (jamais comme une connexion faite vers le nœud), chacun est vérifié avant d'agir et rien n'est exécuté par un shell.
* **Des identifiants qui restent sûrs :** l'identifiant d'une inspection voyage scellé pour ce seul nœud, n'est envoyé qu'en Digest ou HTTPS (jamais Basic en HTTP clair), seulement à l'appareil dont le certificat HTTPS a été vu la première fois, et n'est jamais renvoyé en écho.
* **Le côté public :** l'adresse publique de la maison, qui la donne et où elle se trouve (une requête HTTPS vers un service public fixe toutes les quelques minutes ; `--no-public-info` la désactive). Avec `--dns-name`, il résout aussi le nom qui permet d'atteindre la maison depuis l'extérieur et indique s'il pointe vers cette adresse.
* **Un service :** il tourne comme unité systemd sur le banc de test CM5 (écrite à la main, voir le guide d'utilisation) et garde ses données dans son propre dossier.
* **Pas encore :** les compteurs du routeur lui-même (trafic par appareil), la capture de paquets, contrôler quoi que ce soit (bloquer un appareil, fermer un port, changer le routeur) et des semaines sur un vrai réseau.

## 🧩 Rôle dans A.R.M.O.R.

ARMOR-NETWORK est l'œil de la famille sur le réseau local. Il tourne sur une machine du réseau (la CM5 sur le banc), regarde ce qui s'y trouve sans y toucher et rapporte à [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER), qui garde les noms, les appareils masqués et surveillés et les coupures ; le menu *Réseau* et le *Concepteur réseau* d'[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) et l'écran Réseau d'[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL) le montrent, et Studio peut lui donner des ordres. Il ne configure jamais le routeur ni aucun appareil.

| Il parle à | Comment | Pour quoi faire |
|---|---|---|
| ARMOR-SERVER | `POST` HTTP avec le jeton d'ingestion (`--server-url`) | l'état entre ; les ordres reviennent dans la réponse |
| MQTT | `--mqtt-url` (`mqtt://` ou `mqtts://`) | le même message aussi sur le broker ; les ordres manuels ne passent pas ainsi |
| ARMOR-STUDIO | via le serveur | le menu Réseau et le concepteur réseau l'affichent et lui donnent des ordres |
| ARMOR-ANDROID-CONTROL | via le serveur | l'écran Réseau |
| ARMOR-COMMON | le contrat du message et des ordres | `--validate` vérifie chaque message avec lui |

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-NETWORK architecture: the local network it looks at, the modules of the node and what it tells the server, Studio and the broker" width="100%">
</p>

## 🔒 Sécurité et protection

| Menace | Défense |
|---|---|
| Scanner hors de la maison ou un réseau étranger | Seulement des plages privées (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) et jamais plus de 1024 adresses (un /22) ; `--cidr` est toujours privé ; la garde est `check_scan_range`, pas une option |
| Casser quelque chose de fragile | Une liste d'exclusion (`--skip IP`, répétable) ; rien n'est envoyé à un appareil qui ne soit une question ; jamais d'identifiant, jamais d'exploit ; 12 connexions à la fois lisant quelques centaines d'octets |
| Des ports ouverts à risque passent inaperçus | Elles sont marquées : 21, 23, 3389, 5900, 6379, 3306, 5432, 7547 et 445 |
| Des ordres du serveur qui injectent des commandes | Une liste fermée : `scan_now`, `ping`, `traceroute`, `wake`, `ports`, `http`, `inspect` ; 4 au plus à la fois ; un identifiant d'ordre en lettres, chiffres, `_` et `-` (32 au plus) ; sortie coupée à 2000 ; MAC vérifiée ; rien ne passe par un shell ; les ordres arrivent dans la réponse au message du nœud lui-même, jamais en connexion vers le nœud |
| L'identifiant d'une inspection fuit | Il voyage scellé pour ce seul nœud, seulement en Digest ou HTTPS (jamais Basic en HTTP simple), seulement vers l'appareil dont le certificat HTTPS a été vu la première fois, et n'est jamais répété dans une réponse ; les identifiants d'usine essayés viennent d'une liste fixe |
| Une requête qui sort de la maison | Une requête HTTPS vers un service public fixe (`https://ipinfo.io/json` par défaut) toutes les quelques minutes, pour l'adresse publique ; `--no-public-info` la désactive ; `--dns-name` vérifie aussi que le nom par lequel on joint la maison y pointe |

**Ce qu'il ne fait jamais :** configurer le routeur, capturer des paquets, bloquer un appareil ou fermer un port. Ce qu'est un appareil (son type, son système, son fabricant) est une supposition. Les notes de sécurité sont dans [docs/SAFETY.md](docs/SAFETY.md) ; il n'y a pas eu de revue indépendante.

## 🔌 Interfaces

| Route | Authentification | Ce qu'elle fait |
|---|---|---|
| `armor/network/<node>/state` | message | l'interface, internet, chaque appareil et les derniers événements ; il porte des constats, jamais des ordres |
| `python -m armor_network scan [--json]` | - | regarde le réseau une fois et l'imprime en tableau (ou en message) |
| `python -m armor_network watch` | - | continue de surveiller ; avec `--server-url` et `--ingest-token` il informe ARMOR-SERVER, avec `--mqtt-url` aussi le broker |
| `python -m armor_network demo [--count N]` | - | une maison fictive (un appareil arrive, une caméra ouvre Telnet, internet tombe) : aucun réseau n'est touché |
| `python -m armor_network internet`  `oui <mac>` | - | une ronde du contrôle d'internet ; qui a fabriqué une carte réseau |

Les ordres de Studio (`scan_now`, `ping`, `traceroute`, `wake`, `ports`, `http`, `inspect`) sont mis en file par les routes `/api/v1/network/...` d'ARMOR-SERVER et arrivent au nœud dans la réponse à son message ; le contrat du message et des ordres est dans ARMOR-COMMON (111 vecteurs de conformité). Voir [docs/MESSAGES.md](docs/MESSAGES.md) et [docs/USAGE.md](docs/USAGE.md).

## ⚙️ Configuration

| Réglage | Par défaut | Ce qu'il fait |
|---|---|---|
| `--node-id` | network-1 | le nom de ce nœud dans les messages (minuscules, chiffres, `-` et `_`) |
| `--profile {quick,standard}` | quick | 17 ou 44 ports par appareil ; un nouvel appareil est examiné aussitôt, les autres tous les quarts d'heure |
| `--no-ports`  `--skip IP`  `--cidr` | - | aucun port ; une adresse à ne jamais sonder ; le réseau à scanner (privé, 1024 adresses au plus) |
| `--scan-every`  `--internet-every` | 60 s  5 s | secondes entre balayages et contrôles d'internet |
| `--server-url`  `--ingest-token`  `--mqtt-url`  `--mqtt-user` | - | où il informe ; le jeton de ce nœud (Studio l'affiche) ou le jeton d'ingestion partagé, jamais écrit dans un fichier |
| `--data-dir` | armor-network-data | où l'inventaire et les pannes sont gardés entre les exécutions |
| `--validate`  `--no-public-info`  `--public-info-url`  `--dns-name` | - | vérifie chaque message avec ARMOR-COMMON ; la consultation de l'adresse publique (la couper, son adresse, le nom à vérifier) |

Tout se règle par des options de ligne de commande (voir [docs/USAGE.md](docs/USAGE.md), qui montre aussi l'unité systemd qui le maintient en marche). Une panne est déclarée après trois rondes ratées et terminée après deux bonnes ; les trois premiers balayages apprennent seulement ce qui est là.

## 🚀 Démarrage rapide

**Prérequis :** Python 3.11+ (bibliothèque standard seule) et une machine sur le réseau à surveiller (Linux, Windows ou macOS).

```powershell
python -m unittest discover -s tests                                                 # 181 tests : analyseurs avec échantillons réels, la garde de ce qu'on peut sonder, l'inventaire, internet, l'agent entier face à une maison scriptée
python -m armor_network scan                                                         # regarde le réseau une fois et l'imprime (seulement le réseau privé de cette machine)
python -m armor_network watch --server-url http://127.0.0.1:8080 --ingest-token ...  # continue de surveiller et informe ARMOR-SERVER
python -m armor_network demo --count 3                                               # une maison fictive : aucun réseau n'est touché
python tools/fetch_oui.py                                                            # rafraîchit la table des fabricants depuis le registre IEEE (lancé par une personne, de temps en temps)
```

Voir l'[usage](docs/USAGE.md) et la [conception](docs/DESIGN.md).

## 🧪 Tests

```powershell
python -m unittest discover -s tests  # 181 tests
python -I tools/armor_ci_validate.py
```

| Fichier de tests | Tests | Ce qu'il couvre |
|---|---|---|
| `test_network.py` | 56 | les analyseurs avec échantillons réels, la garde de ce qu'on peut sonder, l'inventaire, internet et l'agent face à une maison scriptée |
| `test_system_io_layer.py`  `test_system_io.py` | 39 | la couche réseau réel : voisins, échos, TCP, DNS |
| `test_orders.py`  `test_orders_edges.py` | 56 | les ordres de Studio et leurs limites |
| `test_cli_commands.py` | 20 | la ligne de commande |
| `test_mqtt_out.py`  `test_seal.py` | 10 | la sortie MQTT et les identifiants scellés |

GitHub Actions exécute la base A.R.M.O.R. à chaque push et pull request : la validation du manifeste, de la version, du journal des modifications et de la parité des README, puis le build et les tests propres au projet.

## 🏗️ Compilation et publication

C'est du Python pur : rien à compiler. La version se trouve dans `pyproject.toml`, dans `armor.project.json` et dans le badge du README (lu depuis le manifeste) ; chaque version a son entrée dans [CHANGELOG.md](CHANGELOG.md). Les versions sont publiées sur GitHub.

## 🩺 Dépannage

| Vous voyez | Parce que | Faites |
|---|---|---|
| `... is not a private network` ou `... has N addresses; at most 1024` | `--cidr` désigne une plage publique ou plus grande qu'un /22 | utilisez une plage privée d'au plus 1024 adresses |
| Peu ou pas d'appareils trouvés | la table de voisins du système se remplit en sondant chaque adresse, ce qui exige la permission de ping ou de lecture | lancez-le avec les droits d'un utilisateur pouvant faire un ping et lire la table de voisins |
| Un appareil fragile se comporte mal quand on le scanne | il n'aime pas qu'on essaie des ports | ajoutez `--skip <adresse>` (répétable) ou `--no-ports` |
| Studio ne reçoit jamais de message | le serveur est injoignable ou refuse le jeton (le problème est compté comme les autres : `unreachable`, `unauthorized`) | vérifiez `--server-url` et le jeton (celui de ce nœud que Studio affiche, ou le jeton d'ingestion partagé) |

## 📂 Structure du dépôt

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-NETWORK" width="100%">
</p>

<details>
<summary>Version texte de l'arborescence</summary>

```text
ARMOR-NETWORK/
├── src/armor_network/
│   ├── ipnet.py oui.py                      ce qu'on peut sonder ; les fabricants
│   ├── system_io.py sim_io.py               le réseau réel ; un réseau scripté
│   ├── neighbors.py parsers.py dnswire.py   ce que disent le système et les appareils
│   ├── services.py                          ports et suppositions
│   ├── inventory.py internet.py             appareils et événements ; la machine des pannes
│   ├── agent.py publisher.py mqtt_out.py    quoi regarder ; comment il rapporte
│   ├── orders.py seal.py                    ordres de Studio ; identifiants scellés
│   ├── cli.py __main__.py                   scan, watch et demo
│   └── data/                                oui.tsv.gz, le registre IEEE
├── tests/                                   181 tests en 8 modules
├── docs/                                    DESIGN, SAFETY, USAGE, MESSAGES
├── tools/                                   fetch_oui.py rafraîchit le registre des fabricants ; les vérifications CI et le lanceur
├── images/                                  bannière, icône et images du README
├── .github/                                 workflow CI, avis au tableau de bord, modèles d'issues et de pull requests
├── armor.project.json                       manifeste : version, rôle, maturité
├── pyproject.toml                           métadonnées du paquet, entrées
├── CHANGELOG.md                             ce qui a changé à chaque version
├── run.sh run.bat                           démarrer, flux partagé
├── build.sh build.bat                       construire et tester, flux partagé
├── build-test.sh build-test.bat             construire, tester, empaqueter
├── test.sh test.bat                         seulement les tests, jamais la version
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Feuille de route et limites connues

**Limites connues aujourd'hui**

* Il n'a pas surveillé une maison entière pendant des semaines.
* Il ne fait qu'interroger le routeur et ne le configure jamais ; ce qu'est un appareil (type, système, fabricant) est une supposition.
* Il ne capture pas de paquets, donc ne voit pas qui parle à qui ; le trafic par appareil et la détection d'intrusion au sens strict demandent les compteurs du routeur ou un port miroir.
* Pas de revue de sécurité indépendante.

**Prochainement**

* Les compteurs propres du routeur (trafic par appareil), la capture de paquets et des semaines sur un vrai réseau.
* Contrôler quelque chose (bloquer un appareil, fermer un port, modifier le routeur) n'est pas prévu sans une revue de risques documentée.

## 🌍 Langues

Le README et les textes existent en anglais, espagnol, français, italien, allemand, chinois, japonais et portugais européen.

## 🔗 Projets liés

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) est un système de sécurité périmétrique composé de dépôts indépendants. Chacun a sa propre version, ses propres tests et son propre README ; voici la famille :

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contrats de messages, validateurs, vecteurs de conformité et types générés
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Firmware du nœud de terrain pour ESP32-S3 avec trois radars et son propre panneau web
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protocoles des onduleurs et batteries solaires et messages d'un nœud passerelle
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Nœud électrique : compteurs, le message des mesures du réseau et les règles de commutation
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Nœud et centrale d'alarme : zones, armement, temporisations, sirène et PIN, avec ou sans le serveur
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Panneau tactile : l'état du système sur un écran mural, armer et acquitter, et la maison de l'assistant vocal
* **ARMOR-NETWORK** (ce dépôt) - Le réseau local : ses appareils, internet et ce qui change
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinateur central : télémétrie, alarmes, appareils, relevés solaires et caméras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Console web : caméras, radar, alarmes, énergie solaire et concepteur de site 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Client Android de l'opérateur avec radar 2D/3D en direct
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - Client opérateur iPhone
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Politique d'inférence visuelle qui explique ses décisions et n'agit jamais
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zones de caméra, masques et règles de détection pour la Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intentions vocales hors ligne avec une confirmation impossible à falsifier
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Boîtiers, électronique et matrice d'acceptation sur banc
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Déploiement, banc d'essai CM5, sauvegarde et TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulateur de télémétrie hors ligne avec des pannes reproductibles
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Détecte, installe et met à jour les propres dépôts de l'écosystème
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architecture, base de sécurité et matrice des capacités

## 📚 Documentation

* [Conception](docs/DESIGN.md) : comment le nœud regarde, se souvient et décide
* [Sécurité](docs/SAFETY.md) : ce qu'il peut toucher et ce qu'il ne fait jamais
* [Usage](docs/USAGE.md) : les commandes, les options et l'unité systemd
* [Messages](docs/MESSAGES.md) : le message du nœud et ses ordres
* [Matrice des capacités : ce qui est prouvé et ce qui ne l'est pas](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catalogue des projets : versions et dépendances entre les dépôts](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Historique des modifications de ce dépôt](CHANGELOG.md)

## 🤝 Contribuer et communauté

* Avant une pull request, exécutez `python -I tools/armor_ci_validate.py` et les tests : les deux doivent réussir. Voir [CONTRIBUTING.md](CONTRIBUTING.md) et le [code de conduite](CODE_OF_CONDUCT.md).
* Le README existe en huit langues et est généré à partir des sources d'ARMOR-DOCS : une modification du texte se fait là-bas.
* Une modification d'un message entre composants commence dans ARMOR-COMMON.
* Ne décrivez pas comme fonctionnant sur une carte ce qui a seulement été compilé.
* Signalez une vulnérabilité en privé : [SECURITY.md](SECURITY.md). Questions, idées et rapports : electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTEUR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCE

GPL-3.0-or-later - voir [LICENSE](LICENSE).
