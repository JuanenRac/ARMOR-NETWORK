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
  🇵🇹 <b>Português</b>
</p>

### Vigia a rede local: os dispositivos que nela estão, se há internet, o que muda e o que é novo (um programa Python sem dependências; corre numa máquina da rede e reporta ao ARMOR-SERVER)

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-187%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.5-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**Verificação de honestidade - o que funciona hoje:** O scanner, o inventário que diz o que mudou, a verificação da internet, a consulta do endereço público, as ordens do Studio e os acessos selados são testados num computador contra uma rede guionizada (187 testes; cada mensagem é aceite pelo contrato do ARMOR-COMMON), e o programa corre como serviço na bancada de testes do CM5, vigiando a rede real em que a bancada está (um router, os telemóveis e os nós da casa). Não vigiou uma casa inteira durante semanas, só pergunta ao router e nunca o configura, e o que é um dispositivo (o tipo, o sistema, o fabricante) é um palpite. Não captura pacotes: não pode ver quem fala com quem, e o tráfego por dispositivo e a deteção de intrusos em sentido estrito precisam dos contadores do router ou de uma porta espelho, que é um passo posterior.

---

## 📋 Num relance

| | |
|---|---|
| Versão | `0.1.5` |
| Maturidade | Estabelecido |
| Função | Nó da rede local: o que há na rede, o que mudou, a internet, ordens do Studio |
| Tecnologia | Python 3.11+, só biblioteca padrão |
| Testes | 187 (`python -m unittest discover -s tests`) |
| Contrato | Mensagem `armor/network/<nó>/state`, 111 vetores de conformidade (mensagens e ordens) |
| Funciona em | Uma máquina da rede a vigiar (Linux, Windows ou macOS); a bancada do CM5 como serviço |
| Em hardware real | Corre como serviço na bancada de testes do CM5, vigiando a sua rede real (um router, os telemóveis e os nós da casa) |
| Licença | GPL-3.0-or-later |

**Ir para:** [Visão geral](#-visão-geral) · [Arquitetura](#-arquitetura) · [Segurança](#-segurança-e-proteção) · [Interfaces](#-interfaces) · [Configuração](#-configuração) · [Início rápido](#-início-rápido) · [Testes](#-testes) · [Problemas](#-resolução-de-problemas) · [Estrutura](#-estrutura-do-repositório) · [Relacionados](#-projetos-relacionados)

## 🚦 Estado do projeto

Cada linha é uma parte deste repositório e a luz diz até onde chega hoje. É escrita com o que o repositório consegue demonstrar (testes, compilações, execuções), não com o que está previsto.

🟢 Feito e verificado · 🟡 Funciona, com limites conhecidos · 🟠 Feito a meio ou ainda por verificar · 🔴 Por fazer ou a não funcionar

| Área | Estado | O que significa aqui |
|---|---|---|
| Software | 🟢 | O leitor da rede, o inventário que diz o que mudou, a verificação da internet, a consulta do endereço público e as ordens do Studio funcionam como serviço na bancada de testes CM5. |
| Testes | 🟢 | Passam 187 testes contra uma rede com guião, e cada mensagem é aceite pelo contrato do ARMOR-COMMON. |
| Protocolos e dados | 🟡 | O que um dispositivo é (o tipo, o sistema, o fabricante) é um palpite, e nada captura pacotes: o tráfego por dispositivo e a deteção de intrusões em sentido estrito não estão feitos. |
| Hardware | 🟡 | Vigia a rede real da bancada de testes CM5 (um router, os telemóveis e os nós da casa), mas não vigiou uma casa inteira durante semanas. |
| Segurança | 🟡 | Só pergunta ao router e nunca o configura; os acessos selados estão testados no anfitrião e não houve revisão independente. |
| Integração | 🟡 | As suas mensagens chegam ao servidor da bancada de testes CM5 e ao Studio; as ordens do Studio são testadas contra uma rede com guião. |
| Documentação | 🟢 | Oito idiomas e o registo de alterações estão atualizados. |

## 🎯 Visão geral

* **O que há na rede:** a tabela de vizinhos da máquina, um toque a cada endereço para que se preencha, um eco a cada dispositivo encontrado (latência e TTL) e o que os dispositivos anunciam sobre si (mDNS, UPnP, NetBIOS, DNS inverso). Para cada dispositivo: endereço, MAC, fabricante (do registo IEEE de 40 000 blocos), nome, tipo, sistema, portas abertas com o que cada uma diz, e quando foi visto pela primeira e última vez.
* **Portas:** uma ligação TCP a 17 (ou 44) portas de cada dispositivo, doze de cada vez, lendo no máximo algumas centenas de bytes do que responde; nunca um início de sessão, nunca uma exploração. Um dispositivo novo observa-se de imediato, os outros a cada quarto de hora.
* **O que muda:** um dispositivo que aparece (as três primeiras pesquisas só aprendem), fica em silêncio ou volta, muda de endereço, uma porta que abre ou fecha, e duas máquinas a responder por um endereço (sobretudo o do router). Cada evento tem um id, por isso diz-se uma só vez.
* **A internet:** a cada poucos segundos um eco ao router, uma ligação TCP, duas perguntas DNS a resolvedores escolhidos e uma página web. Uma queda precisa de três rondas para se considerar queda e duas para terminar, datada desde a sua primeira ronda falhada e contada até à primeira boa, e diz de quem é a culpa: do operador (o router responde e nada para além dele) ou deste lado (o router também não responde). Latência, perda e as quedas das últimas 24 horas.
* **Só olha para a sua própria rede:** recusa qualquer endereço que não seja privado (10/8, 172.16/12, 192.168/16) e qualquer intervalo maior que um /22; uma lista de exclusão mantém-no longe do que é frágil; nada se envia a um dispositivo que não seja uma pergunta.
* **A mensagem** `armor/network/<node>/state`: a interface, a internet, cada dispositivo e os últimos eventos; está no contrato partilhado (111 vetores) e leva constatações, nunca comandos. `python -m armor_network scan` imprime-a como tabela, `watch` informa o ARMOR-SERVER, `demo` representa uma casa inventada (entra um dispositivo novo, uma câmara abre Telnet, a internet cai e volta, alguém responde pelo router) sem tocar em nenhuma rede.
* **Onde se mostra:** o menu Rede do ARMOR-STUDIO (os dispositivos, a internet com as suas quedas e latência, o tráfego e os eventos; um administrador dá nome aos dispositivos e marca os conhecidos, o que silencia o alarme de dispositivo novo), o Desenhador de rede (o desenho da rede da casa, comparado com o que foi encontrado, e capaz de o desenhar) e o ecrã Rede da aplicação Android. O ARMOR-SERVER dispara os alarmes.
* **Ordens do Studio:** um varrimento já, um ping, um traceroute, um acordar, as portas ou a página web de um dispositivo e uma inspeção com um acesso que der; as ordens chegam na resposta à própria mensagem do nó (nunca como uma ligação feita ao nó), cada uma é verificada antes de se fazer algo e nada é executado por uma shell.
* **Acessos que se mantêm seguros:** o acesso de uma inspeção viaja selado só para este nó, é enviado só por Digest ou HTTPS (nunca Basic por HTTP simples), só ao dispositivo cujo certificado HTTPS foi visto da primeira vez, e nunca é devolvido em eco.
* **O lado público:** o endereço público da casa, quem o dá e onde está (um pedido HTTPS a um serviço público fixo de poucos em poucos minutos; `--no-public-info` desliga-o). Com `--dns-name` resolve também o nome com que se chega a casa a partir do exterior e diz se aponta para esse endereço.
* **Um serviço:** corre como unidade systemd na bancada de testes do CM5 (escrita à mão, veja o guia de uso) e guarda os seus dados na sua própria pasta.
* **Ainda não:** os contadores do próprio router (tráfego por dispositivo), captura de pacotes, controlar o que quer que seja (bloquear um dispositivo, fechar uma porta, alterar o router) e semanas numa rede real.

## 🧩 Papel no A.R.M.O.R.

O ARMOR-NETWORK é o olho da família sobre a rede local. Corre numa máquina da rede (o CM5 na bancada), olha o que lá está sem lhe tocar e reporta ao [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER), que guarda os nomes, os dispositivos ocultos e vigiados e as falhas; o menu *Rede* e o *Desenhador de rede* do [ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) e o ecrã Rede do [ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL) mostram-no, e o Studio pode dar-lhe ordens. Nunca configura o router nem nenhum dispositivo.

| Fala com | Como | Para quê |
|---|---|---|
| ARMOR-SERVER | `POST` HTTP com o token de ingestão (`--server-url`) | entra o estado; as ordens voltam na resposta |
| MQTT | `--mqtt-url` (`mqtt://` ou `mqtts://`) | a mesma mensagem também no broker; as ordens manuais não viajam assim |
| ARMOR-STUDIO | através do servidor | o menu Rede e o desenhador de rede mostram-no e dão-lhe ordens |
| ARMOR-ANDROID-CONTROL | através do servidor | o ecrã Rede |
| ARMOR-COMMON | o contrato da mensagem e das ordens | `--validate` verifica cada mensagem com ele |

## 🏛️ Arquitetura

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-NETWORK architecture: the local network it looks at, the modules of the node and what it tells the server, Studio and the broker" width="100%">
</p>

## 🔒 Segurança e proteção

| Ameaça | Defesa |
|---|---|
| Varrer fora de casa ou uma rede alheia | Só intervalos privados (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) e nunca mais de 1024 endereços (um /22); `--cidr` é sempre privado; a guarda é `check_scan_range`, não uma opção |
| Estragar algo frágil | Uma lista de exclusão (`--skip IP`, repetível); nada é enviado a um equipamento que não seja uma pergunta; nunca um login, nunca um exploit; 12 ligações de cada vez a ler umas centenas de bytes |
| Portas abertas de risco passam despercebidas | São assinaladas: 21, 23, 3389, 5900, 6379, 3306, 5432, 7547 e 445 |
| Ordens do servidor que injetam comandos | Uma lista fechada: `scan_now`, `ping`, `traceroute`, `wake`, `ports`, `http`, `inspect`; no máximo 4 de cada vez; um id de ordem de letras, dígitos, `_` e `-` (32 no máximo); saída cortada em 2000; MAC verificado; nada passa por uma shell; as ordens chegam na resposta à mensagem do próprio nó, nunca como uma ligação feita ao nó |
| O login de uma inspeção vaza | Viaja selado só para este nó, apenas por Digest ou HTTPS (nunca Basic em HTTP simples), só para o equipamento cujo certificado HTTPS foi visto da primeira vez, e nunca se repete numa resposta; os logins de fábrica que tenta vêm de uma lista fixa |
| Um pedido que sai de casa | Um pedido HTTPS a um serviço público fixo (`https://ipinfo.io/json` por predefinição) a cada poucos minutos, para o endereço público; `--no-public-info` desliga-o; `--dns-name` verifica ainda que o nome pelo qual se chega à casa aponta para ele |

**O que nunca faz:** configurar o router, capturar pacotes, bloquear um equipamento nem fechar uma porta. O que um equipamento é (o seu tipo, o seu sistema, o seu fabricante) é uma suposição. As notas de segurança estão em [docs/SAFETY.md](docs/SAFETY.md); não houve revisão independente.

## 🔌 Interfaces

| Rota | Autenticação | O que faz |
|---|---|---|
| `armor/network/<node>/state` | mensagem | a interface, a internet, cada equipamento e os últimos eventos; leva constatações, nunca ordens |
| `python -m armor_network scan [--json]` | - | olha para a rede uma vez e imprime-a como tabela (ou como a mensagem) |
| `python -m armor_network watch` | - | continua a vigiar; com `--server-url` e `--ingest-token` informa o ARMOR-SERVER, com `--mqtt-url` também o broker |
| `python -m armor_network demo [--count N]` | - | uma casa inventada (entra um equipamento, uma câmara abre Telnet, cai a internet): nenhuma rede é tocada |
| `python -m armor_network internet`  `oui <mac>` | - | uma ronda da verificação da internet; quem fabricou uma placa de rede |

As ordens do Studio (`scan_now`, `ping`, `traceroute`, `wake`, `ports`, `http`, `inspect`) são postas em fila pelas rotas `/api/v1/network/...` do ARMOR-SERVER e chegam ao nó na resposta à sua mensagem; o contrato da mensagem e das ordens está no ARMOR-COMMON (111 vetores de conformidade). Veja [docs/MESSAGES.md](docs/MESSAGES.md) e [docs/USAGE.md](docs/USAGE.md).

## ⚙️ Configuração

| Definição | Predefinição | O que faz |
|---|---|---|
| `--node-id` | network-1 | o nome deste nó nas mensagens (minúsculas, dígitos, `-` e `_`) |
| `--profile {quick,standard}` | quick | 17 ou 44 portas por equipamento; um equipamento novo olha-se logo, os outros a cada quarto de hora |
| `--no-ports`  `--skip IP`  `--cidr` | - | sem portas; um endereço a nunca sondar; a rede a varrer (privada, no máximo 1024 endereços) |
| `--scan-every`  `--internet-every` | 60 s  5 s | segundos entre varrimentos e verificações da internet |
| `--server-url`  `--ingest-token`  `--mqtt-url`  `--mqtt-user` | - | para onde informa; o token deste nó (o Studio mostra-o) ou o token de ingestão partilhado, nunca escrito num ficheiro |
| `--data-dir` | armor-network-data | onde o inventário e as quedas ficam entre execuções |
| `--validate`  `--no-public-info`  `--public-info-url`  `--dns-name` | - | verifica cada mensagem com o ARMOR-COMMON; a consulta do endereço público (desligá-la, o seu endereço, o nome a verificar) |

Tudo se define com opções da linha de comandos (veja [docs/USAGE.md](docs/USAGE.md), que mostra também a unidade systemd que o mantém a correr). Uma queda declara-se após três rondas falhadas e termina após duas boas; os três primeiros varrimentos só aprendem o que lá está.

## 🚀 Início rápido

**Requisitos:** Python 3.11+ (só biblioteca padrão) e uma máquina na rede a vigiar (Linux, Windows ou macOS).

```powershell
python -m unittest discover -s tests                                                 # 187 testes: analisadores com amostras reais, a guarda do que se pode sondar, o inventário, a internet, o agente completo contra uma casa com guião
python -m armor_network scan                                                         # olha para a rede uma vez e imprime-a (só a rede privada desta máquina)
python -m armor_network watch --server-url http://127.0.0.1:8080 --ingest-token ...  # continua a vigiar e informa o ARMOR-SERVER
python -m armor_network demo --count 3                                               # uma casa inventada: nenhuma rede é tocada
python tools/fetch_oui.py                                                            # renova a tabela de fabricantes a partir do registo IEEE (uma pessoa executa-o, de vez em quando)
```

Consulte a [utilização](docs/USAGE.md) e o [desenho](docs/DESIGN.md).

## 🧪 Testes

```powershell
python -m unittest discover -s tests  # 187 testes
python -I tools/armor_ci_validate.py
```

| Ficheiro de testes | Testes | O que cobre |
|---|---|---|
| `test_network.py` | 56 | os analisadores com amostras reais, a guarda do que se pode sondar, o inventário, a internet e o agente contra uma casa com guião |
| `test_system_io_layer.py`  `test_system_io.py` | 39 | a camada da rede real: vizinhos, ecos, TCP, DNS |
| `test_orders.py`  `test_orders_edges.py` | 56 | as ordens do Studio e os seus limites |
| `test_cli_commands.py` | 20 | a linha de comandos |
| `test_mqtt_out.py`  `test_seal.py` | 10 | a saída MQTT e as credenciais seladas |
| `test_typing_behaviour.py` | 6 | o comportamento que as anotações de tipos mantêm: a guarda da varredura, o analisador de ordens e as tabelas de fabricantes |

O GitHub Actions executa a base do A.R.M.O.R. em cada push e pull request: a validação do manifesto, da versão, do registo de alterações e da paridade dos README, e depois a compilação e os testes do próprio projeto. As fontes também passam o verificador de tipos: `python -m mypy` (configurado em `pyproject.toml`) não reporta nada, e `test_typing_behaviour.py` fixa o comportamento que as anotações mantêm.

## 🏗️ Compilação e publicação

É Python puro: não há nada para compilar. A versão está em `pyproject.toml`, em `armor.project.json` e no emblema do README (lido do manifesto); cada versão tem a sua entrada em [CHANGELOG.md](CHANGELOG.md). As versões são publicadas no GitHub.

## 🩺 Resolução de problemas

| Vê | Porque | Faça |
|---|---|---|
| `... is not a private network` ou `... has N addresses; at most 1024` | `--cidr` indica um intervalo público ou maior que um /22 | use um intervalo privado de no máximo 1024 endereços |
| Poucos ou nenhuns equipamentos encontrados | a tabela de vizinhos do sistema enche-se sondando cada endereço, o que precisa de permissão para ping ou leitura | execute-o com as permissões de um utilizador que possa fazer ping e ler a tabela de vizinhos |
| Um equipamento frágil porta-se mal ao ser varrido | não gosta que se experimentem portas | acrescente `--skip <endereço>` (repetível) ou `--no-ports` |
| O Studio nunca recebe uma mensagem | o servidor não é alcançável ou recusa o token (o problema conta-se como qualquer outro: `unreachable`, `unauthorized`) | verifique `--server-url` e o token (o deste nó que o Studio mostra, ou o token de ingestão partilhado) |

## 📂 Estrutura do repositório

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-NETWORK" width="100%">
</p>

<details>
<summary>Versão em texto da árvore</summary>

```text
ARMOR-NETWORK/
├── src/armor_network/
│   ├── ipnet.py oui.py                      o que se pode sondar; os fabricantes
│   ├── system_io.py sim_io.py               a rede real; uma com guião
│   ├── neighbors.py parsers.py dnswire.py   o que dizem o sistema e os equipamentos
│   ├── services.py                          portas e suposições
│   ├── inventory.py internet.py             equipamentos e eventos; a máquina de quedas
│   ├── agent.py publisher.py mqtt_out.py    o que olhar; como reporta
│   ├── orders.py seal.py                    ordens do Studio; credenciais seladas
│   ├── cli.py __main__.py                   scan, watch e demo
│   └── data/                                oui.tsv.gz, o registo IEEE
├── tests/                                   187 testes em 9 módulos
├── docs/                                    DESIGN, SAFETY, USAGE, MESSAGES
├── tools/                                   fetch_oui.py renova o registo de fabricantes; as verificações de CI e o lançador
├── images/                                  faixa, ícone e as imagens do README
├── .github/                                 fluxo de CI, aviso ao painel, modelos de issues e pull requests
├── armor.project.json                       manifesto: versão, função, maturidade
├── pyproject.toml                           metadados do pacote, entradas
├── CHANGELOG.md                             o que mudou em cada versão
├── run.sh run.bat                           arrancar, fluxo partilhado
├── build.sh build.bat                       compilar e testar, fluxo partilhado
├── build-test.sh build-test.bat             compilar, testar e empacotar
├── test.sh test.bat                         só os testes, nunca a versão
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ Roteiro e limites conhecidos

**Limites conhecidos hoje**

* Nunca vigiou uma casa inteira durante semanas.
* Só pergunta ao router e nunca o configura; o que um equipamento é (tipo, sistema, fabricante) é uma suposição.
* Não captura pacotes, por isso não vê quem fala com quem; o tráfego por equipamento e a deteção de intrusão em sentido estrito precisam dos contadores do router ou de uma porta espelho.
* Sem revisão de segurança independente.

**A seguir**

* Os contadores do próprio router (tráfego por equipamento), a captura de pacotes e semanas numa rede real.
* Controlar algo (bloquear um equipamento, fechar uma porta, mudar o router) não está previsto sem uma revisão de riscos documentada.

## 🌍 Idiomas

O README e os textos existem em inglês, espanhol, francês, italiano, alemão, chinês, japonês e português europeu.

## 🔗 Projetos relacionados

O **A.R.M.O.R.** (Autonomous Radar & Multimodal Observation Range) é um sistema de segurança perimetral feito de repositórios independentes. Cada um tem a sua própria versão, os seus próprios testes e o seu próprio README; esta é a família:

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - Contratos de mensagens, validadores, vetores de conformidade e tipos gerados
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - Firmware de nó de campo para ESP32-S3 com três radares e o seu próprio painel web
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - Protocolos de inversores e baterias solares e as mensagens de um nó porta de ligação
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - Nó elétrico: contadores, a mensagem das leituras da rede e as regras de comutação
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - Nó e painel de alarme: zonas, armar, atrasos, sirene e PIN, com o servidor ou sem ele
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - Painel tátil: o estado do sistema num ecrã de parede, armar e reconhecer, e a casa do assistente de voz
* **ARMOR-NETWORK** (este repositório) - A rede local: os seus dispositivos, a internet e o que muda
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - Coordenador central: telemetria, alarmes, dispositivos, leituras solares e câmaras
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Consola web: câmaras, radar, alarmes, energia solar e o desenhador 2D/3D do local
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - Cliente de operador Android com radar 2D/3D em direto
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - Cliente de operador para iPhone
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - Política de inferência visual que explica as suas decisões e nunca atua
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Zonas de câmara, máscaras e regras de deteção para o Jetson Orin NX
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - Intenções de voz offline com uma confirmação que não pode ser falsificada
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - Caixas, eletrónica e a matriz de aceitação em bancada
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - Implantação, a bancada de testes do CM5, cópias de segurança e TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - Simulador de telemetria offline com falhas repetíveis
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - Deteta, instala e atualiza os repositórios do próprio ecossistema
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Arquitetura, base de segurança e a matriz de capacidades

## 📚 Documentação

* [Desenho](docs/DESIGN.md): como o nó olha, recorda e decide
* [Segurança](docs/SAFETY.md): o que pode tocar e o que nunca faz
* [Utilização](docs/USAGE.md): os comandos, as opções e a unidade systemd
* [Mensagens](docs/MESSAGES.md): a mensagem do nó e as suas ordens
* [Matriz de capacidades: o que está demonstrado e o que não está](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [Catálogo de projetos: versões e como os repositórios dependem uns dos outros](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [Registo de alterações deste repositório](CHANGELOG.md)

## 🤝 Contribuir e comunidade

* Antes de um pull request execute `python -I tools/armor_ci_validate.py` e os testes: ambos têm de passar. Consulte [CONTRIBUTING.md](CONTRIBUTING.md) e o [código de conduta](CODE_OF_CONDUCT.md).
* O README existe em oito idiomas e é gerado a partir das fontes do ARMOR-DOCS: uma alteração ao texto faz-se lá.
* Uma alteração a uma mensagem entre componentes começa no ARMOR-COMMON.
* Não descreva como a funcionar numa placa aquilo que só foi compilado.
* Comunique uma vulnerabilidade em privado: [SECURITY.md](SECURITY.md). Perguntas, ideias e relatórios: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENÇA

GPL-3.0-or-later - consulte [LICENSE](LICENSE).
