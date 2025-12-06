# PiPulse Pipeline: V-Model Master Guideline
**最終更新**: 2025-12-06（Hideo, Grok & Gemini 共同リファイン）

### 改訂履歴
| 日付         | 変更者           | 変更内容                                           |
|--------------|------------------|----------------------------------------------------|
| 2025-12-06   | Hideo, Grok, Gemini | 国際標準名称に完全統一、章立て・SUPサブセクション化、ドキュメントマップ追加 |
| 2025-10-31   | Hideo & Grok     | トレーサビリティ教訓追記                           |
| 2025-10-27   | Hideo & Grok     | Mermaid修正、SYS.2整合性向上                       |
| 2025-10-26   | Hideo (Gemini)   | バージョン番号削除                                 |
| 2025-10-22   | Hideo (Gemini)   | 初版作成                                           |

### 用語集（プロジェクト全体共通）
- **7月データ**：192件の過去センサーデータ（秒なし `%Y-%m-%d %H:%M`）。後方互換性テストのベースライン。
- **Drive**：Google Drive（rclone同期先）
- **FR / NFR**：Functional / Non-Functional Requirements
- **INC-xxx**：教訓番号（lessons-learned.md参照）

### V字プロセス全体像
```mermaid
graph LR
    classDef design fill:#e1f5fe,stroke:#22577a,stroke-width:2px;
    classDef test fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;
    subgraph left ["設計フェーズ"]
        A[SYS.1 システム要件分析] --&gt; B[SYS.2 システムアーキテクチャ設計]
        B --&gt; C[SYS.3 システム詳細設計]
        C --&gt; D[SWE.1 ソフトウェア要件分析]
        D --&gt; E[SWE.2 ソフトウェアアーキテクチャ設計]
    end
    subgraph right ["検証フェーズ"]
        F[SWE.3 ソフトウェア実装] --&gt; G[単体テスト]
        G --&gt; H[統合テスト]
        H --&gt; I[システムテスト]
        I --&gt; J[受入テスト]
    end
    class A,B,C,D,E design
    class F,G,H,I,J test
    E --&gt; F
    A --- J
    B --- I
    C --- H
    E --- G
```

## 1. システム定義プロセス（System Definition - SYS）

|プロセスID|正式名称         |優先度   |ステータス|成果物ファイル名              |主要な活動・目標        |
|------|-------------|------|-----|----------------------|--------------------|
|SYS.1 |システム要件分析     |High  |[x]  |system_requirements.md|2025-12-06確定        |
|SYS.2 |システムアーキテクチャ設計|Medium|[p]  |system_architecture.md|旧system-design.md統合中|
|SYS.3 |システム詳細設計     |Medium|[p]  |detailed-design.md    |将来MySQLスキーマ等        |

## 2. ソフトウェア開発プロセス（Software Development - SWE）

|プロセスID|正式名称           |優先度   |ステータス|成果物ファイル名          |主要な活動・目標               |
|------|---------------|------|-----|------------------|-----------------------------|
|SWE.1 |ソフトウェア要件分析     |Low   |[ ]  |sw-requirements.md|REQ派生5件以上                    |
|SWE.2 |ソフトウェアアーキテクチャ設計|Medium|[p]  |sw-architecture.md|関数図・シーケンス図                   |
|SWE.3 |ソフトウェア実装       |High  |[p]  |implementation.md |Python + rclone + Apps Script|

## 3. 検証＆妥当性確認プロセス（Verification & Validation）

|プロセスID|名称     |優先度   |ステータス|成果物ファイル名            |主要な活動・目標            |
|------|-------|------|-----|--------------------|--------------------|
|V&V.1 |単体テスト  |Medium|[ ]  |unit-tests.md       |pytest カバレッジ80%以上   |
|V&V.2 |統合テスト  |Medium|[ ]  |integration-tests.md|E2E（Docker + iPhone）|
|V&V.3 |システムテスト|Medium|[p]  |system-tests.md     |スケジュール時間・欠測チェック     |
|V&V.4 |受入テスト  |Low   |[p]  |acceptance-tests.md |7月データグラフ比較          |

## 4. サポートプロセス（Support Process - SUP）

### 4.1 CI/CD・品質保証

|プロセスID|名称              |優先度 |ステータス|成果物ファイル名        |主要な活動・目標|
|------|----------------|----|-----|----------------|----|
|SUP.1 |QA・CI計画         |High|[ ]  |qa-plan.md      |CIワークフロー定義|
|SUP.2 |検証（CodeQL等）     |Low |[ ]  |verification.md |静的解析|
|SUP.7 |構成管理（Dependabot）|Low |[p]  |configuration.md|依存関係の自動更新|

### 4.2 デプロイ・監視

|プロセスID|名称       |優先度   |ステータス|成果物ファイル名             |主要な活動・目標|
|------|---------|------|-----|---------------------|----|
|SUP.5 |Slackアラート|Medium|[ ]  |audit.md             |エラー/失敗通知|
|SUP.6 |製品受入・デプロイ|High  |[ ]  |product-acceptance.md|RPiへの自動デプロイ|

### 4.3 レビュー・改善

|プロセスID|名称       |優先度   |ステータス|成果物ファイル名              |主要な活動・目標|
|------|---------|------|-----|----------------------|----|
|SUP.9 |問題解決・教訓管理|Medium|[p]  |lessons-learned.md    |インシデント管理|
|SUP.10|プロセス改善   |Low   |[ ]  |process-improvement.md|定期的なプロセス見直し|

## 5. マネジメントプロセス（Management Process - MAN）

### 5.1 プロジェクト管理プロセス

|プロセスID|名称      |優先度   |ステータス|成果物ファイル名                     |主要な活動・目標|
|------|--------|------|-----|-----------------------------|----|
|MAN.1 |プロジェクト管理|Medium|[p]  |project-management.md + 本ファイル|リスク管理、進捗追跡|

### 5.2 ドキュメントマップ（全成果物一覧）

|分類      |ファイル名                 |Vモデル階層             |ステータス|最終更新      |概要               |
|--------|----------------------|-------------------|-----|----------|-----------------|
|**管理**  |v-master-guideline.md |MAN.1              |[x]  |2025-12-06|本ファイル（マスターガイド）|
|          |project-management.md |MAN.1              |[p]  |          |リスク・進捗管理ドキュメント|
|          |traceability_matrix.md|MAN.1              |[p]  |2025-12-06|要件トレーサビリティマトリクス|
|**システム**|system_requirements.md|SYS.1              |[x]  |2025-12-06|システム要件定義書|
|          |system_architecture.md|SYS.2              |[p]  |2025-12-06|システムアーキテクチャ設計書|
|          |detailed-design.md    |SYS.3              |[p]  |          |システム詳細設計書|
|**SW**    |sw-requirements.md    |SWE.1              |[ ]  |          |ソフトウェア要件分析書|
|          |sw-architecture.md    |SWE.2              |[p]  |          |ソフトウェアアーキテクチャ設計書|
|          |implementation.md     |SWE.3              |[p]  |          |実装メモ・手順書|
|**テスト**  |unit-tests.md         |V&V.1              |[ ]  |          |単体テスト計画・結果|
|          |integration-tests.md  |V&V.2              |[ ]  |          |統合テスト計画・結果|
|          |system-tests.md       |V&V.3              |[p]  |          |システムテスト計画・結果|
|          |acceptance-tests.md   |V&V.4              |[p]  |          |受入テスト計画・結果|
|**サポート**|qa-plan.md            |SUP.1              |[ ]  |          |品質保証・CI計画書|
|          |verification.md       |SUP.2              |[ ]  |          |静的解析・検証結果|
|          |configuration.md      |SUP.7              |[p]  |          |構成管理計画書（Dependabot等）|
|          |audit.md              |SUP.5              |[ ]  |          |監査・監視ログ仕様|
|          |product-acceptance.md |SUP.6              |[ ]  |          |製品受入・デプロイ計画書|
|          |lessons-learned.md    |SUP.9              |[p]  |2025-10-31|問題解決・教訓集|
|          |process-improvement.md|SUP.10             |[ ]  |          |プロセス改善計画書|

*凡例: [x]=完了, [p]=進行中, [ ]=未着手*