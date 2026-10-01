<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-NETWORK banner" width="100%">
</p>

# 🛰️ ARMOR-NETWORK

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  🇫🇷 <b>Français</b> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>

### Surveille le réseau local : les appareils qui y sont, si internet est là, ce qui change et ce qui est nouveau (un programme Python sans dépendances, en lecture seule ; il tourne sur une machine du réseau et rapporte à ARMOR-SERVER)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-53-00E5FF.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-ff9800.svg" alt="Maturity">
</p>

---

**Vérification d'honnêteté - ce qui fonctionne aujourd'hui:** **Maturité : scaffolding.** Le scanner, l'inventaire qui dit ce qui a changé, la vérification d'internet et le message sont testés sur un ordinateur contre un réseau scénarisé (53 tests ; ARMOR-COMMON accepte tous les messages), et le programme a tourné une fois sur un vrai réseau, avec un routeur et un téléphone. Il n'a pas surveillé une maison entière pendant des jours, il ne fait qu'interroger le routeur et ne le configure jamais, et ce qu'est un appareil (son type, son système, son fabricant) est une supposition. Il ne capture pas de paquets : il ne voit pas qui parle à qui, et le trafic par appareil et la détection d'intrusion au sens strict demandent les compteurs du routeur ou un port miroir, ce qui est une étape ultérieure.

---

## 🎯 Présentation

* **Ce qu'il y a sur le réseau :** la table de voisins de la machine, un coup sur chaque adresse pour qu'elle se remplisse, un écho à chaque appareil trouvé (latence et TTL) et ce que les appareils annoncent d'eux-mêmes (mDNS, UPnP, NetBIOS, DNS inverse). Pour chacun : adresse, MAC, fabricant (du registre de l'IEEE, 40 000 blocs), nom, type, système, ports ouverts avec ce que dit chacun, et quand il a été vu pour la première et la dernière fois.
* **Ports :** une connexion TCP à 17 (ou 44) ports de chaque appareil, douze à la fois, en lisant au plus quelques centaines d'octets de la réponse ; jamais de connexion, jamais d'exploit. Un nouvel appareil est examiné aussitôt, les autres tous les quarts d'heure.
* **Ce qui change :** un appareil qui apparaît (le premier balayage ne fait qu'apprendre), se tait ou revient, change d'adresse, un port qui s'ouvre ou se ferme, et deux machines qui répondent pour une même adresse (surtout celle du routeur). Chaque événement a un id, il n'est donc dit qu'une fois.
* **Internet :** toutes les quelques secondes un écho au routeur, une connexion TCP, deux questions DNS à des résolveurs choisis et une page web. Une coupure demande trois tours pour être déclarée et deux pour être finie, est datée du premier tour raté et comptée jusqu'au premier bon, et dit à qui est la faute : au fournisseur (le routeur répond et rien au-delà) ou à ce côté-ci (le routeur ne répond pas non plus). Latence, perte et les coupures des dernières 24 heures.
* **Il ne regarde que votre propre réseau :** il refuse toute adresse non privée (10/8, 172.16/12, 192.168/16) et toute plage plus grande qu'un /22 ; une liste d'exclusion le tient éloigné de ce qui est fragile ; rien n'est envoyé à un appareil qui ne soit une question.
* **Le message** `armor/network/<nœud>/state` : l'interface, internet, chaque appareil et les derniers événements ; il est dans le contrat partagé (330 vecteurs) et porte des constats, jamais des ordres. `python -m armor_network scan` l'imprime en tableau, `watch` informe ARMOR-SERVER, `demo` joue une maison inventée (un nouvel appareil arrive, une caméra ouvre Telnet, internet tombe et revient, quelqu'un répond pour le routeur) sans toucher aucun réseau.
* **Où on le voit :** le menu Réseau d'ARMOR-STUDIO (les appareils, internet avec ses coupures et sa latence, le trafic et les événements ; un administrateur nomme les appareils et marque les connus, ce qui apaise l'alarme d'un nouvel appareil), le Concepteur de réseau (le dessin du réseau de la maison, comparé à ce qui a été trouvé et capable de le dessiner) et l'écran Réseau de l'app Android. ARMOR-SERVER déclenche les alarmes.
* **Pas encore :** les compteurs du routeur lui-même (trafic par appareil), la capture de paquets, contrôler quoi que ce soit (bloquer un appareil, fermer un port, changer le routeur) et des semaines sur un vrai réseau.

## 📂 Structure du dépôt

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

## 🛠️ Environnement de développement

```bash
python -m unittest discover -s tests                  # 53 tests: the parsers with real samples, the guard on what may be probed, the inventory, the internet, the whole agent against a scripted house
python -m armor_network scan                          # look at the network once and print it (only the private network of this machine)
python -m armor_network watch --server-url http://127.0.0.1:8080 --ingest-token ...    # keep watching and tell ARMOR-SERVER
python -m armor_network demo --count 3                # a made-up house: nothing on any network is touched
python tools/fetch_oui.py                             # refresh the table of makers from the IEEE register (run by a person, now and then)
```

See the [usage](docs/USAGE.md) and the [design](docs/DESIGN.md).

Voir la [conception](docs/DESIGN.md), les [notes de sécurité](docs/SAFETY.md), l'[usage](docs/USAGE.md) et les [messages](docs/MESSAGES.md).

## 🔗 Projets liés

**A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) est un système de sécurité périmétrique composé de dépôts indépendants. Chacun a sa propre version, ses propres tests et son propre README ; voici la famille :

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contrats de messages, validateurs, vecteurs de conformité et types générés
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - Firmware du nœud de terrain pour ESP32-S3 avec trois radars et son propre panneau web
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - Protocoles des onduleurs et batteries solaires et messages d'un nœud passerelle
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - Nœud électrique : compteurs, le message des mesures du réseau et les règles de commutation
* **[ARMOR-HMI](https://github.com/JuanenRac/ARMOR-HMI)** - Panneau tactile : l'état du système sur un écran mural, armer et acquitter, et la maison de l'assistant vocal
* **ARMOR-NETWORK** (ce dépôt) - Le réseau local : ses appareils, internet et ce qui change
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordinateur central : télémétrie, alarmes, appareils, relevés solaires et caméras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Console web : caméras, radar, alarmes, énergie solaire et concepteur de site 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Client Android de l'opérateur avec radar 2D/3D en direct
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Politique d'inférence visuelle qui explique ses décisions et n'agit jamais
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intentions vocales hors ligne avec une confirmation impossible à falsifier
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Boîtiers, électronique et matrice d'acceptation sur banc
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Déploiement, banc d'essai CM5, sauvegarde et TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulateur de télémétrie hors ligne avec des pannes reproductibles
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Détecte, installe et met à jour les propres dépôts de l'écosystème
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Architecture, base de sécurité et matrice des capacités

## 📚 Documentation et communauté

Pour en savoir plus :

* [Matrice des capacités : ce qui est prouvé et ce qui ne l'est pas](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catalogue des projets : versions et dépendances entre les dépôts](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Historique des modifications de ce dépôt](CHANGELOG.md)
* [Licence (GPL-3.0-or-later)](LICENSE)
* Questions, idées et rapports : electrohobby3d@gmail.com

## 👤 AUTEUR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENCE

GPL-3.0-or-later - voir [LICENSE](LICENSE).
