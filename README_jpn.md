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
  🇯🇵 <b>日本語</b> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### ローカルネットワークを見張ります：接続されているデバイス、インターネットがあるか、何が変わり何が新しいか（依存ライブラリなしの Python プログラム。ネットワーク上のマシンで動き、ARMOR-SERVER に報告）

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-181%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.5-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**正直さのチェック - 今日動いているもの:** スキャナー、何が変わったかを伝えるインベントリ、インターネットの検査、公開アドレスの問い合わせ、Studio からの指示、封印されたログインは、スクリプト化したネットワークに対してコンピューター上でテストされ（181 件。すべてのメッセージが ARMOR-COMMON のコントラクトに受け付けられる）、プログラムは CM5 テストベンチ上でサービスとして動き、ベンチがつながる実際のネットワーク（ルーター、家のスマートフォンとノード）を見張っています。家全体を数週間見張ったことはなく、ルーターに尋ねるだけで設定は一切せず、デバイスが何か（種類、システム、メーカー）は推測です。パケットは取得しません。誰が誰と話しているかは見えず、デバイスごとのトラフィックや厳密な意味での侵入検知にはルーターのカウンターかミラーポートが必要で、それは今後の段階です。

---

## 📋 ひと目で

| | |
|---|---|
| バージョン | `0.1.5` |
| 成熟度 | 確立 |
| 役割 | ローカルネットワークのノード：ネットワーク上の機器、変化、インターネット、Studio からのオーダー |
| 技術 | Python 3.11+（標準ライブラリのみ） |
| テスト | 181 件（`python -m unittest discover -s tests`） |
| 契約 | メッセージ `armor/network/<ノード>/state`、適合ベクター 111 件（メッセージとオーダー） |
| 動作環境 | 監視対象ネットワーク上のマシン（Linux、Windows、macOS）。CM5 テストベンチではサービスとして |
| 実機での確認 | CM5 テストベンチ上でサービスとして動き、実際のネットワーク（ルーター、家のスマートフォンとノード）を見張っています |
| ライセンス | GPL-3.0-or-later |

**移動先：** [概要](#-概要) · [アーキテクチャ](#-アーキテクチャ) · [セキュリティ](#-セキュリティと安全) · [インターフェース](#-インターフェース) · [設定](#-設定) · [クイックスタート](#-クイックスタート) · [テスト](#-テスト) · [トラブルシューティング](#-トラブルシューティング) · [構成](#-リポジトリの構成) · [関連](#-関連プロジェクト)

## 🚦 プロジェクトの状況

各行はこのリポジトリの一部分で、信号は今日どこまで進んでいるかを示します。計画ではなく、リポジトリが示せるもの（テスト、ビルド、実行）に基づいて書かれています。

🟢 完了・検証済み · 🟡 動作する（既知の制限あり） · 🟠 一部のみ、または未検証 · 🔴 未実装または動作しない

| 領域 | 状態 | ここでの意味 |
|---|---|---|
| ソフトウェア | 🟢 | スキャナー、変更点を示すインベントリ、インターネット確認、公開アドレスの取得、Studio からの命令は、CM5 テストベンチ上でサービスとして動いています。 |
| テスト | 🟢 | 181 件のテストがスクリプト化したネットワークに対して通り、すべてのメッセージが ARMOR-COMMON の契約に受理されます。 |
| プロトコルとデータ | 🟡 | 機器の種類・システム・メーカーは推測で、パケットは取得しません。機器ごとのトラフィックと厳密な意味での侵入検知は未実装です。 |
| ハードウェア | 🟡 | CM5 テストベンチの実際のネットワーク（ルーター、家の電話機とノード）を監視していますが、家全体を数週間監視したことはありません。 |
| セキュリティ | 🟡 | ルーターに問い合わせるだけで設定は一切しません。封印されたログイン情報はホストでテスト済みで、独立したレビューはありません。 |
| 連携 | 🟡 | メッセージは CM5 テストベンチのサーバーと Studio に届きます。Studio からの命令はスクリプト化したネットワークに対してテストしています。 |
| ドキュメント | 🟢 | 8 言語と変更履歴は最新です。 |

## 🎯 概要

* **ネットワーク上にあるもの：** マシンの近隣テーブル、それを満たすための各アドレスへの呼びかけ、見つかった各機器へのエコー（遅延と TTL）、機器自身の告知（mDNS、UPnP、NetBIOS、逆引き DNS）。機器ごとに、アドレス、MAC、メーカー（IEEE の 40,000 ブロックの登録簿から）、名前、種類、OS、開いているポートとその応答内容、初回と最終の確認時刻を持ちます。
* **ポート：** 各機器の 17（または 44）ポートに TCP 接続を 12 本ずつ行い、応答は数百バイトまでしか読みません。ログインも攻撃も行いません。新しい機器はすぐに、他は 15 分ごとに調べます。
* **変化：** 機器の出現（最初の 3 回のスキャンは学習のみ）、沈黙、復帰、アドレスの変更、ポートの開閉、1 つのアドレスに 2 台が応答（特にルーターのアドレス）。各イベントには ID があり、一度だけ通知されます。
* **インターネット：** 数秒ごとにルーターへのエコー、TCP 接続、選んだリゾルバーへの DNS 問い合わせ 2 件、ウェブページ 1 件。停止と判定するには 3 回、復旧と判定するには 2 回の連続が必要で、最初の失敗の回から起算し最初の成功の回まで数え、原因がどちら側かも示します：プロバイダー側（ルーターは応答し、その先は応答しない）か、こちら側（ルーターも応答しない）。遅延、損失、過去 24 時間の停止。
* **自分のネットワークだけを見ます：** プライベートでないアドレス（10/8、172.16/12、192.168/16 以外）と /22 より大きい範囲は拒否します。除外リストでデリケートな機器には触れず、機器には質問以外を送りません。
* **メッセージ** `armor/network/<ノード>/state`：インターフェース、インターネット、全機器、最新のイベント。共有コントラクト（111 ベクター）にあり、発見だけを運び、命令は運びません。`python -m armor_network scan` は表で表示、`watch` は ARMOR-SERVER に通知、`demo` は架空の家（新しい機器の参加、カメラが Telnet を開く、インターネットの断と復旧、ルーターになりすます応答）を、ネットワークに触れずに再生します。
* **表示場所：** ARMOR-STUDIO のネットワークメニュー（機器、停止と遅延のあるインターネット、トラフィック、イベント。管理者が機器に名前を付け既知として印を付けると、新しい機器の警報が静まります）、ネットワーク設計（家のネットワークの図面を、検出結果と比較し、描くこともできます）、Android アプリのネットワーク画面。警報は ARMOR-SERVER が発します。
* **Studio からの指示：**今すぐのスキャン、ping、traceroute、ウェイクアップ、1 台のデバイスのポートや Web ページ、あなたが渡したログインでの検査。指示はノード自身のメッセージへの応答として届き（ノードへの接続としては決して来ません）、実行前にそれぞれ検査され、シェルを通して何かを実行することはありません。
* **安全なままのログイン：**検査のログインはそのノードだけに封印されて届き、Digest または HTTPS でのみ送られ（平文 HTTP の Basic は決して使わない）、最初に HTTPS 証明書を見たデバイスにだけ送られ、エコーバックされません。
* **公開側：**家の公開アドレス、その提供元と場所（数分ごとに固定の公開サービスへ HTTPS リクエストを 1 回。`--no-public-info` でオフ）。`--dns-name` を使うと、外から家に接続するための名前も解決し、そのアドレスを指しているかどうかを伝えます。
* **サービス：**CM5 テストベンチで systemd ユニットとして動き（手書き、使い方ガイドを参照）、データは専用のフォルダーに保存します。
* **まだ：** ルーター自身のカウンター（機器ごとのトラフィック）、パケットキャプチャ、何かを制御すること（機器のブロック、ポートを閉じる、ルーターの変更）、実ネットワークでの数週間の運用。

## 🧩 A.R.M.O.R. での役割

ARMOR-NETWORK はファミリーのローカルネットワークを見る目です。ネットワーク上のマシン（ベンチの CM5）で動き、そこにあるものに触れずに見て、[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER) に報告します。サーバーが名前、非表示・監視デバイス、停止を保持し、[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) の*ネットワーク*メニューと*ネットワークデザイナー*、[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL) のネットワーク画面が表示し、Studio から指示も出せます。ルーターやデバイスを設定することはありません。

| 連携先 | 方法 | 目的 |
|---|---|---|
| ARMOR-SERVER | 取り込みトークン付きの HTTP `POST`（`--server-url`） | 状態を送り、オーダーは応答で戻る |
| MQTT | `--mqtt-url`（`mqtt://` または `mqtts://`） | 同じメッセージをブローカーにも送る（手動オーダーはこの経路では届かない） |
| ARMOR-STUDIO | サーバー経由 | ネットワークメニューとネットワークデザイナーが表示し、オーダーを渡す |
| ARMOR-ANDROID-CONTROL | サーバー経由 | ネットワーク画面 |
| ARMOR-COMMON | メッセージとオーダーの契約 | `--validate` で各メッセージを検査 |

## 🏛️ アーキテクチャ

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-NETWORK architecture: the local network it looks at, the modules of the node and what it tells the server, Studio and the broker" width="100%">
</p>

## 🔒 セキュリティと安全

| 脅威 | 防御 |
|---|---|
| 家の外や他人のネットワークのスキャン | プライベート範囲（10.0.0.0/8、172.16.0.0/12、192.168.0.0/16）のみで、1024 アドレス（/22）を超えません。`--cidr` も常にプライベート。ガードは `check_scan_range` で、オプションではありません |
| 壊れやすい機器への悪影響 | スキップリスト（`--skip IP`、複数可）。質問でないものは機器に送らず、ログインも攻撃コードも使いません。同時 12 接続で数百バイトだけ読みます |
| 危険な開放ポートに気付かない | 21、23、3389、5900、6379、3306、5432、7547、445 を印付けします |
| コマンドを注入するサーバーからのオーダー | 固定のリスト：`scan_now`、`ping`、`traceroute`、`wake`、`ports`、`http`、`inspect`。同時 4 件まで、オーダー ID は英数字と `_` `-`（最大 32 文字）、出力は 2000 で切り詰め、MAC は検証、シェルは経由しません。オーダーはノード自身のメッセージへの応答で届き、ノードへ接続することはありません |
| 検査用ログインの漏えい | このノードだけ向けに封印され、Digest か HTTPS でのみ送られ（平文 HTTP の Basic は不可）、HTTPS 証明書を最初に確認した機器にだけ送られ、応答には決して繰り返されません。試す工場出荷時ログインは固定リストです |
| 家の外へ出るリクエスト | 公開アドレスのために、数分ごとに固定の公開サービス（既定 `https://ipinfo.io/json`）へ HTTPS リクエストを 1 回送ります。`--no-public-info` で無効化。`--dns-name` は外から家に届く名前がそのアドレスを指すかも確認します |

**決してしないこと：** ルーターの設定、パケットキャプチャ、機器のブロック、ポートの閉鎖。機器が何であるか（種類、システム、メーカー）は推測です。安全上の注意は [docs/SAFETY.md](docs/SAFETY.md) にあります。第三者によるレビューはありません。

## 🔌 インターフェース

| ルート | 認証 | 内容 |
|---|---|---|
| `armor/network/<node>/state` | メッセージ | インターフェース、インターネット、全機器、最新イベント。所見のみで、コマンドは載せません |
| `python -m armor_network scan [--json]` | - | ネットワークを 1 回調べて表（またはメッセージ）で表示 |
| `python -m armor_network watch` | - | 監視を続け、`--server-url` と `--ingest-token` で ARMOR-SERVER に、`--mqtt-url` でブローカーにも通知 |
| `python -m armor_network demo [--count N]` | - | 架空の家（機器の参加、カメラの Telnet 開放、インターネット断）。実ネットワークには触れません |
| `python -m armor_network internet`  `oui <mac>` | - | インターネット確認を 1 回、ネットワークカードのメーカー照会 |

Studio からのオーダー（`scan_now`、`ping`、`traceroute`、`wake`、`ports`、`http`、`inspect`）は ARMOR-SERVER の `/api/v1/network/...` ルートがキューに入れ、ノードのメッセージへの応答で届きます。メッセージとオーダーの契約は ARMOR-COMMON（適合ベクター 111 件）にあります。[docs/MESSAGES.md](docs/MESSAGES.md) と [docs/USAGE.md](docs/USAGE.md) を参照。

## ⚙️ 設定

| 設定 | 既定値 | 内容 |
|---|---|---|
| `--node-id` | network-1 | メッセージ中のこのノードの名前（小文字、数字、`-`、`_`） |
| `--profile {quick,standard}` | quick | 機器ごとに 17 または 44 ポート。新しい機器はすぐ、他は 15 分ごと |
| `--no-ports`  `--skip IP`  `--cidr` | - | ポートを見ない、決して調べないアドレス、スキャン対象ネットワーク（プライベートで 1024 アドレス以下） |
| `--scan-every`  `--internet-every` | 60 s  5 s | スイープとインターネット確認の間隔（秒） |
| `--server-url`  `--ingest-token`  `--mqtt-url`  `--mqtt-user` | - | 通知先、このノードのトークン（Studio に表示）または共有の取り込みトークン（ファイルには書かない） |
| `--data-dir` | armor-network-data | 実行間でインベントリと障害を保持する場所 |
| `--validate`  `--no-public-info`  `--public-info-url`  `--dns-name` | - | 各メッセージを ARMOR-COMMON で検査、公開アドレスの照会（無効化、そのアドレス、確認する名前） |

設定はすべてコマンドラインオプションで行います（常駐させる systemd ユニットも示す [docs/USAGE.md](docs/USAGE.md) を参照）。障害は 3 回連続の失敗で判定し、2 回の成功で終了とします。最初の 3 回のスイープは何があるかを学ぶだけです。

## 🚀 クイックスタート

**要件：** Python 3.11+（標準ライブラリのみ）と、監視対象ネットワーク上のマシン（Linux、Windows、macOS）。

```powershell
python -m unittest discover -s tests                                                 # 181 件：実サンプルのパーサ、調べてよい範囲のガード、インベントリ、インターネット、スクリプト版の家に対するエージェント全体
python -m armor_network scan                                                         # ネットワークを 1 回調べて表示（このマシンのプライベートネットワークのみ）
python -m armor_network watch --server-url http://127.0.0.1:8080 --ingest-token ...  # 監視を続けて ARMOR-SERVER に通知
python -m armor_network demo --count 3                                               # 架空の家：実ネットワークには触れない
python tools/fetch_oui.py                                                            # IEEE 登録簿からメーカー表を更新（人が時々実行）
```

[使い方](docs/USAGE.md)と[設計](docs/DESIGN.md)を参照してください。

## 🧪 テスト

```powershell
python -m unittest discover -s tests  # 181 件
python -I tools/armor_ci_validate.py
```

| テストファイル | テスト数 | 対象 |
|---|---|---|
| `test_network.py` | 56 | 実サンプルのパーサ、調べてよい範囲のガード、インベントリ、インターネット、スクリプト版の家に対するエージェント |
| `test_system_io_layer.py`  `test_system_io.py` | 39 | 実ネットワーク層：近隣、エコー、TCP、DNS |
| `test_orders.py`  `test_orders_edges.py` | 56 | Studio からのオーダーとその上限 |
| `test_cli_commands.py` | 20 | コマンドライン |
| `test_mqtt_out.py`  `test_seal.py` | 10 | MQTT 出力と封印した認証情報 |

GitHub Actions は push と pull request のたびに A.R.M.O.R. の基本検査（マニフェスト、バージョン、変更履歴、README の一致）と、プロジェクト自身のビルドとテストを実行します。

## 🏗️ ビルドとリリース

純粋な Python なので、コンパイルするものはありません。バージョンは `pyproject.toml`、`armor.project.json`、README のバッジ（マニフェストから読み取り）にあり、各バージョンには [CHANGELOG.md](CHANGELOG.md) にエントリーがあります。リリースは GitHub で公開されます。

## 🩺 トラブルシューティング

| 表示 | 原因 | 対処 |
|---|---|---|
| `... is not a private network` または `... has N addresses; at most 1024` | `--cidr` が公開範囲または /22 より大きい範囲を指している | 1024 アドレス以下のプライベート範囲を使う |
| 機器がほとんど、または全く見つからない | システムの近隣テーブルは全アドレスへの呼びかけで埋まり、ping や読み取りの権限が必要 | ping と近隣テーブルの読み取りができるユーザー権限で実行 |
| 壊れやすい機器がスキャンで不調になる | ポートへの接続を嫌う | `--skip <アドレス>`（複数可）または `--no-ports` を追加 |
| Studio にメッセージが届かない | サーバーに届かない、またはトークンを拒否（他と同様に問題として数える：`unreachable`、`unauthorized`） | `--server-url` とトークン（Studio が示すこのノードのもの、または共有の取り込みトークン）を確認 |

## 📂 リポジトリの構成

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-NETWORK" width="100%">
</p>

<details>
<summary>ツリーのテキスト版</summary>

```text
ARMOR-NETWORK/
├── src/armor_network/
│   ├── ipnet.py oui.py                      調べてよい範囲、メーカー
│   ├── system_io.py sim_io.py               実ネットワークとスクリプト版
│   ├── neighbors.py parsers.py dnswire.py   システムと機器の応答
│   ├── services.py                          ポートと推測
│   ├── inventory.py internet.py             機器とイベント、障害の状態機械
│   ├── agent.py publisher.py mqtt_out.py    見る対象、報告方法
│   ├── orders.py seal.py                    Studio からのオーダーと封印した認証情報
│   ├── cli.py __main__.py                   scan・watch・demo
│   └── data/                                oui.tsv.gz（IEEE 登録簿）
├── tests/                                   8 モジュール 181 件
├── docs/                                    DESIGN、SAFETY、USAGE、MESSAGES
├── tools/                                   fetch_oui.py がメーカー登録簿を更新、共通の CI 検査とランチャー
├── images/                                  バナー、アイコン、README の画像
├── .github/                                 CI ワークフロー、ダッシュボード通知、Issue と Pull Request のテンプレート
├── armor.project.json                       マニフェスト：版・役割・成熟度
├── pyproject.toml                           パッケージ情報とエントリー
├── CHANGELOG.md                             各バージョンの変更点
├── run.sh run.bat                           起動（共通フロー）
├── build.sh build.bat                       ビルドとテスト（共通フロー）
├── build-test.sh build-test.bat             ビルド、テスト、パッケージ化
├── test.sh test.bat                         テストのみ（版は変えません）
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ ロードマップと既知の制限

**現時点の既知の制限**

* 家全体を何週間も監視したことはありません。
* ルーターに問い合わせるだけで設定は一切せず、機器が何か（種類、システム、メーカー）は推測です。
* パケットを取得しないので誰が誰と通信しているかは見えません。機器ごとの通信量や厳密な侵入検知にはルーターのカウンターかミラーポートが必要です。
* 第三者によるセキュリティレビューはありません。

**今後**

* ルーター自身のカウンター（機器ごとの通信量）、パケット取得、実ネットワークでの数週間の運用。
* 何かを制御する（機器のブロック、ポートの閉鎖、ルーターの変更）ことは、文書化したリスクレビューなしには予定していません。

## 🌍 言語

README とテキストは、英語、スペイン語、フランス語、イタリア語、ドイツ語、中国語、日本語、ヨーロッパポルトガル語で提供されています。

## 🔗 関連プロジェクト

**A.R.M.O.R.**（Autonomous Radar & Multimodal Observation Range）は、独立したリポジトリで構成される境界セキュリティシステムです。各リポジトリは独自のバージョン、テスト、README を持ちます。ファミリーは次のとおりです：

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - メッセージのコントラクト、バリデーター、適合ベクトル、生成された型
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - 3 つのレーダーと独自の Web パネルを備えた ESP32-S3 向けフィールドノードのファームウェア
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - ソーラーインバーターとバッテリーのプロトコル、ゲートウェイノードのメッセージ
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - 電気ノード：メーター、系統の読み取り値のメッセージ、切り替えのルール
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - 警報ノードとパネル：ゾーン、警戒、遅延、サイレン、PIN。サーバーありでもなしでも動作
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - タッチパネル：壁面画面でのシステムの状態、警戒と確認応答、そして音声アシスタントの置き場
* **ARMOR-NETWORK**（このリポジトリ） - ローカルネットワーク：そのデバイス、インターネット、そして変化
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - 中央コーディネーター：テレメトリ、警報、デバイス、ソーラーの読み取り値、カメラ
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Web コンソール：カメラ、レーダー、警報、太陽光エネルギー、2D/3D のサイトデザイナー
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - ライブの 2D/3D レーダーを備えた Android オペレータークライアント
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - iPhone オペレータークライアント
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - 判断を説明し、決して作動させない視覚推論ポリシー
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - Jetson Orin NX 向けのカメラゾーン、マスク、検出ルール
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - 偽造できない確認つきのオフライン音声インテント
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - 筐体、電子回路、ベンチ受け入れマトリクス
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - デプロイ、CM5 テストベンチ、バックアップ、TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - 再現可能な障害を持つオフラインのテレメトリシミュレーター
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - エコシステム自身のリポジトリを検出、インストール、更新
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - アーキテクチャ、セキュリティのベースライン、機能マトリクス

## 📚 ドキュメント

* [設計](docs/DESIGN.md)：ノードの観察、記憶、判断の仕組み
* [安全](docs/SAFETY.md)：触れてよいものと決してしないこと
* [使い方](docs/USAGE.md)：コマンド、オプション、systemd ユニット
* [メッセージ](docs/MESSAGES.md)：ノードのメッセージとオーダー
* [機能マトリクス：何が証明され、何が証明されていないか](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [プロジェクトカタログ：バージョンと、リポジトリ同士の依存関係](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [このリポジトリの変更履歴](CHANGELOG.md)

## 🤝 コントリビュートとコミュニティ

* Pull Request の前に `python -I tools/armor_ci_validate.py` とテストを実行してください。どちらも通る必要があります。[CONTRIBUTING.md](CONTRIBUTING.md) と[行動規範](CODE_OF_CONDUCT.md)を参照してください。
* README は 8 言語で提供され、ARMOR-DOCS のソースから生成されます。文面の変更はそちらで行います。
* コンポーネント間のメッセージの変更は ARMOR-COMMON から始めます。
* ビルドしただけのものを、ボード上で動いているかのように書かないでください。
* 脆弱性は非公開で報告してください：[SECURITY.md](SECURITY.md)。質問、アイデア、報告：electrohobby3d@gmail.com（[SUPPORT.md](SUPPORT.md)）。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 ライセンス

GPL-3.0-or-later - [LICENSE](LICENSE) を参照してください。
