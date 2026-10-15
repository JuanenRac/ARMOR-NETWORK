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
  🇯🇵 <b>日本語</b>
</p>

### ローカルネットワークを監視：どんな機器があるか、インターネットがつながっているか、何が変わったか、何が新しいか（依存ライブラリなしの Python プログラム、読み取り専用。ネットワーク上のマシンで動作し、ARMOR-SERVER に報告します）

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-53-00E5FF.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Maturity-scaffolding-ff9800.svg" alt="Maturity">
</p>

---

**正直さのチェック - 今日動いているもの:** **成熟度：足場段階。** スキャナー、変化を伝えるインベントリ、インターネット確認、メッセージは、台本どおりのネットワークを相手にコンピューター上でテスト済みです（53 件のテスト。すべてのメッセージを ARMOR-COMMON が受理）。実ネットワークで 1 回だけ実行しており、ルーターとスマートフォンが 1 台ありました。家全体を何日も監視したことはなく、ルーターには問い合わせるだけで設定は一切せず、機器の種類・OS・メーカーは推測です。パケットは取得しません。誰が誰と通信しているかは見えず、機器ごとのトラフィックや厳密な意味での侵入検知にはルーターのカウンターやミラーポートが必要で、それは後の段階です。

---

## 🎯 概要

* **ネットワーク上にあるもの：** マシンの近隣テーブル、それを満たすための各アドレスへの呼びかけ、見つかった各機器へのエコー（遅延と TTL）、機器自身の告知（mDNS、UPnP、NetBIOS、逆引き DNS）。機器ごとに、アドレス、MAC、メーカー（IEEE の 40,000 ブロックの登録簿から）、名前、種類、OS、開いているポートとその応答内容、初回と最終の確認時刻を持ちます。
* **ポート：** 各機器の 17（または 44）ポートに TCP 接続を 12 本ずつ行い、応答は数百バイトまでしか読みません。ログインも攻撃も行いません。新しい機器はすぐに、他は 15 分ごとに調べます。
* **変化：** 機器の出現（最初のスキャンは学習のみ）、沈黙、復帰、アドレスの変更、ポートの開閉、1 つのアドレスに 2 台が応答（特にルーターのアドレス）。各イベントには ID があり、一度だけ通知されます。
* **インターネット：** 数秒ごとにルーターへのエコー、TCP 接続、選んだリゾルバーへの DNS 問い合わせ 2 件、ウェブページ 1 件。停止と判定するには 3 回、復旧と判定するには 2 回の連続が必要で、最初の失敗の回から起算し最初の成功の回まで数え、原因がどちら側かも示します：プロバイダー側（ルーターは応答し、その先は応答しない）か、こちら側（ルーターも応答しない）。遅延、損失、過去 24 時間の停止。
* **自分のネットワークだけを見ます：** プライベートでないアドレス（10/8、172.16/12、192.168/16 以外）と /22 より大きい範囲は拒否します。除外リストでデリケートな機器には触れず、機器には質問以外を送りません。
* **メッセージ** `armor/network/<ノード>/state`：インターフェース、インターネット、全機器、最新のイベント。共有コントラクト（330 ベクター）にあり、発見だけを運び、命令は運びません。`python -m armor_network scan` は表で表示、`watch` は ARMOR-SERVER に通知、`demo` は架空の家（新しい機器の参加、カメラが Telnet を開く、インターネットの断と復旧、ルーターになりすます応答）を、ネットワークに触れずに再生します。
* **表示場所：** ARMOR-STUDIO のネットワークメニュー（機器、停止と遅延のあるインターネット、トラフィック、イベント。管理者が機器に名前を付け既知として印を付けると、新しい機器の警報が静まります）、ネットワーク設計（家のネットワークの図面を、検出結果と比較し、描くこともできます）、Android アプリのネットワーク画面。警報は ARMOR-SERVER が発します。
* **まだ：** ルーター自身のカウンター（機器ごとのトラフィック）、パケットキャプチャ、何かを制御すること（機器のブロック、ポートを閉じる、ルーターの変更）、実ネットワークでの数週間の運用。

## 📂 リポジトリの構成

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

## 🛠️ 開発環境

```bash
python -m unittest discover -s tests                  # 53 tests: the parsers with real samples, the guard on what may be probed, the inventory, the internet, the whole agent against a scripted house
python -m armor_network scan                          # look at the network once and print it (only the private network of this machine)
python -m armor_network watch --server-url http://127.0.0.1:8080 --ingest-token ...    # keep watching and tell ARMOR-SERVER
python -m armor_network demo --count 3                # a made-up house: nothing on any network is touched
python tools/fetch_oui.py                             # refresh the table of makers from the IEEE register (run by a person, now and then)
```

See the [usage](docs/USAGE.md) and the [design](docs/DESIGN.md).

[設計](docs/DESIGN.md)、[安全性のメモ](docs/SAFETY.md)、[使い方](docs/USAGE.md)、[メッセージ](docs/MESSAGES.md)を参照してください。

## 🔗 関連プロジェクト

**A.R.M.O.R.**（Autonomous Radar & Multimodal Observation Range）は、独立したリポジトリで構成される周辺警備システムです。それぞれに独自のバージョン、テスト、README があります。ファミリーは次のとおりです：

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - メッセージ契約、検証器、適合性ベクトル、生成された型
* **[ARMOR-RADAR](https://github.com/JuanenRac/ARMOR-RADAR)** - ESP32-S3 用フィールドノードのファームウェア。レーダー 3 基と独自の Web パネル付き
* **[ARMOR-SOLAR](https://github.com/JuanenRac/ARMOR-SOLAR)** - 太陽光インバーターとバッテリーのプロトコル、およびゲートウェイノードのメッセージ
* **[ARMOR-ELECTRICAL](https://github.com/JuanenRac/ARMOR-ELECTRICAL)** - 電気ノード：電力量計、電力網の計測メッセージ、開閉のルール
* **[ARMOR-HMI](https://github.com/JuanenRac/ARMOR-HMI)** - タッチパネル：壁面ディスプレイでのシステム状態表示、警戒・確認操作、音声アシスタントの拠点
* **ARMOR-NETWORK** (このリポジトリ) - ローカルネットワーク：機器、インターネット、そして変化
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - 中央コーディネーター：テレメトリ、アラーム、デバイス、太陽光の測定値、カメラ
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - Web コンソール：カメラ、レーダー、アラーム、太陽光発電、2D/3D サイト設計
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - リアルタイム 2D/3D レーダー付きの Android オペレータークライアント
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - 判断を説明し、決して動作しない視覚推論ポリシー
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - 偽造できない確認を備えたオフライン音声インテント
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - 筐体、電子部品、ベンチ受け入れマトリクス
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - デプロイ、CM5 テストベンチ、バックアップ、TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - 再現可能な故障を備えたオフラインのテレメトリシミュレーター
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - エコシステム自身のリポジトリを検出し、インストールし、更新する
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - アーキテクチャ、セキュリティ基準、機能マトリクス

## 📚 ドキュメントとコミュニティ

詳しくは：

* [機能マトリクス：実証済みのものとそうでないもの](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [プロジェクト一覧：バージョンとリポジトリ間の依存関係](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [このリポジトリの変更履歴](CHANGELOG.md)
* [ライセンス（GPL-3.0-or-later）](LICENSE)
* 質問・提案・報告：electrohobby3d@gmail.com

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 ライセンス

GPL-3.0-or-later - [LICENSE](LICENSE) を参照。
