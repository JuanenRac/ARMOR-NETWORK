<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-NETWORK banner" width="100%">
</p>

# 🛰️ ARMOR-NETWORK

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>


### Vigia a rede local: os dispositivos que nela estão, se a internet está lá, o que muda e o que é novo (um programa Python sem dependências, só de leitura; corre numa máquina da rede e reporta ao ARMOR-SERVER)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-53-00E5FF.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-ff9800.svg" alt="Maturity">
</p>

---

**Verificação de honestidade - o que funciona hoje:** **Maturidade: andaime.** O analisador, o inventário que diz o que mudou, a verificação da internet e a mensagem estão testados num computador contra uma rede com guião (53 testes; cada mensagem é aceite pelo contrato do ARMOR-COMMON), e o programa foi executado uma vez numa rede real, que tinha um router e um telemóvel. Não vigiou uma casa inteira durante dias, só pergunta ao router e nunca o configura, e o que um dispositivo é (o seu tipo, o seu sistema, o seu fabricante) é um palpite. Não captura pacotes: não pode ver quem fala com quem, e o tráfego por dispositivo e a deteção de intrusões em sentido estrito precisam dos contadores do router ou de uma porta espelho, o que é um passo posterior.

---

## 🎯 Visão geral

* **O que há na rede:** a tabela de vizinhos da máquina, um toque a cada endereço para que se preencha, um eco a cada dispositivo encontrado (latência e TTL) e o que os dispositivos anunciam sobre si (mDNS, UPnP, NetBIOS, DNS inverso). Para cada dispositivo: endereço, MAC, fabricante (do registo IEEE de 40 000 blocos), nome, tipo, sistema, portas abertas com o que cada uma diz, e quando foi visto pela primeira e última vez.
* **Portas:** uma ligação TCP a 17 (ou 44) portas de cada dispositivo, doze de cada vez, lendo no máximo algumas centenas de bytes do que responde; nunca um início de sessão, nunca uma exploração. Um dispositivo novo observa-se de imediato, os outros a cada quarto de hora.
* **O que muda:** um dispositivo que aparece (a primeira pesquisa só aprende), fica em silêncio ou volta, muda de endereço, uma porta que abre ou fecha, e duas máquinas a responder por um endereço (sobretudo o do router). Cada evento tem um id, por isso diz-se uma só vez.
* **A internet:** a cada poucos segundos um eco ao router, uma ligação TCP, duas perguntas DNS a resolvedores escolhidos e uma página web. Uma queda precisa de três rondas para se considerar queda e duas para terminar, datada desde a sua primeira ronda falhada e contada até à primeira boa, e diz de quem é a culpa: do operador (o router responde e nada para além dele) ou deste lado (o router também não responde). Latência, perda e as quedas das últimas 24 horas.
* **Só olha para a sua própria rede:** recusa qualquer endereço que não seja privado (10/8, 172.16/12, 192.168/16) e qualquer intervalo maior que um /22; uma lista de exclusão mantém-no longe do que é frágil; nada se envia a um dispositivo que não seja uma pergunta.
* **A mensagem** `armor/network/<node>/state`: a interface, a internet, cada dispositivo e os últimos eventos; está no contrato partilhado (330 vetores) e leva constatações, nunca comandos. `python -m armor_network scan` imprime-a como tabela, `watch` informa o ARMOR-SERVER, `demo` representa uma casa inventada (entra um dispositivo novo, uma câmara abre Telnet, a internet cai e volta, alguém responde pelo router) sem tocar em nenhuma rede.
* **Onde se mostra:** o menu Rede do ARMOR-STUDIO (os dispositivos, a internet com as suas quedas e latência, o tráfego e os eventos; um administrador dá nome aos dispositivos e marca os conhecidos, o que silencia o alarme de dispositivo novo), o Desenhador de rede (o desenho da rede da casa, comparado com o que foi encontrado, e capaz de o desenhar) e o ecrã Rede da aplicação Android. O ARMOR-SERVER dispara os alarmes.
* **Ainda não:** os contadores do próprio router (tráfego por dispositivo), captura de pacotes, controlar o que quer que seja (bloquear um dispositivo, fechar uma porta, alterar o router) e semanas numa rede real.

## 📂 Estrutura do repositório

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

## 🛠️ Ambiente de desenvolvimento

```bash
python -m unittest discover -s tests                  # 53 tests: the parsers with real samples, the guard on what may be probed, the inventory, the internet, the whole agent against a scripted house
python -m armor_network scan                          # look at the network once and print it (only the private network of this machine)
python -m armor_network watch --server-url http://127.0.0.1:8080 --ingest-token ...    # keep watching and tell ARMOR-SERVER
python -m armor_network demo --count 3                # a made-up house: nothing on any network is touched
python tools/fetch_oui.py                             # refresh the table of makers from the IEEE register (run by a person, now and then)
```

Veja a [utilização](docs/USAGE.md) e o [desenho](docs/DESIGN.md).

Veja o [desenho](docs/DESIGN.md), as [notas de segurança](docs/SAFETY.md), a [utilização](docs/USAGE.md) e as [mensagens](docs/MESSAGES.md).

## 🔗 Projetos relacionados

O **A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) é um sistema de segurança perimetral feito de repositórios independentes. Cada um tem a sua própria versão, os seus próprios testes e o seu próprio README; esta é a família:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratos de mensagens, validadores, vetores de conformidade e tipos gerados
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - Firmware de nó de campo para ESP32-S3 com três radares e o seu próprio painel web
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - Protocolos de inversores e baterias solares e as mensagens de um nó de ligação
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - Nó elétrico: contadores, a mensagem das leituras da rede e as regras de comutação
* **[ARMOR-HMI](https://github.com/JuanenRac/ARMOR-HMI)** - Painel tátil: o estado do sistema num ecrã de parede, armar e reconhecer, e a casa do assistente de voz
* **ARMOR-NETWORK** (este repositório) - A rede local: os seus dispositivos, a internet e o que muda
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordenador central: telemetria, alarmes, dispositivos, leituras solares e câmaras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Consola web: câmaras, radar, alarmes, energia solar e o desenhador de local 2D/3D
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Cliente Android de operador com um radar 2D/3D em direto
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Política de inferência visual que explica as suas decisões e nunca atua
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenções de voz offline com uma confirmação que não se pode falsificar
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Caixas, eletrónica e a matriz de aceitação de bancada
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Implementação, a bancada de testes CM5, cópias de segurança e TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulador de telemetria offline com falhas repetíveis
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Deteta, instala e atualiza os próprios repositórios do ecossistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Arquitetura, linha de base de segurança e a matriz de capacidades

## 📚 Documentação e comunidade

Onde ler mais:

* [Matriz de capacidades: o que está provado e o que não](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catálogo de projetos: versões e como os repositórios dependem uns dos outros](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Registo de alterações deste repositório](CHANGELOG.md)
* [Licença (GPL-3.0-or-later)](LICENSE)
* Perguntas, ideias e relatórios: electrohobby3d@gmail.com

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENÇA

GPL-3.0-or-later - veja [LICENSE](LICENSE).
