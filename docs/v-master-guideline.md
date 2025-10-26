## PiPulse Pipeline: V-Model Master Guideline

---

### 改訂履歴
| 日付 | 変更者 | 変更内容 | 関連 |
|---|---|---|---|
| 2025-10-26 | Hideo (assisted by Gemini) | バージョン管理一元化のため、バージョン番号を削除。 | - |
| 2025-10-23 | Hideo (Gemini assist) | 用語集/テーブル/Mermaid改善、SUP/MAN全展開による網羅性向上。 | PR #12, #13<br>(v1.2.3参照) |
| 2025-10-22 | Hideo (Gemini assist) | 初期バージョン作成。 | - |

---

**最終更新:** 2025-10-26

### 用語集
- **[REQ-02]**: 主要横断要件「リアルタイム更新（処理時間<1min目標）」。センサーデータ取得からGoogle Driveへのアップロードまでの一連の処理を指す。
- **7月データ**: 過去のセンサーデータ（192件）。テストや要件定義のベースラインとして使用。
- **SYS**: System Definition (システム定義)
- **SWE**: Software Development (ソフトウェア開発)
- **V&V**: Verification & Validation (検証と妥当性確認)
- **SUP**: Support Process (サポートプロセス)
- **MAN**: Management Process (マネジメントプロセス)
- **Drive/Sheets**: Google Drive / Google Sheets。

### V字プロセス全体像

```mermaid
graph TD
    subgraph 設計フェーズ (左側)
        A(SYS.1 要件定義) --> B(SYS.2 システム設計);
        B --> C(SYS.3 詳細設計);
        C --> D(SWE.1 SW要件分析);
        D --> E(SWE.2 SW設計);
    end
    subgraph 実装・テストフェーズ (右側)
        F(SWE.3 実装) --> G(ユニットテスト);
        G --> H(統合テスト);
        H --> I(システムテスト);
        I --> J(受け入れテスト);
    end
    E --> F;
    A --- J;
    B --- I;
    C --- H;
    E --- G;
end
```<br>**※SUP/MANプロセスは横断的な性質を持つため、図中では明示的なV字の線としては示していません。**
```<br>※SUP/MANプロセスは横断的な性質を持つため、図中では明示的なV字の線としては示していません。
```

### システム設計 (System Definition - SYS)
| プロセスID | 優先度 | ステータス | TODO | 完了基準 | Notes (成果物) |
|---|---|---|---|---|---|
| SYS.1 | High | [x] | [REQ-02] 要件の具体化 | 要件リストにID追加、Gemini評価OK | [requirements.md](docs/requirements.md) |
| SYS.2 | Medium | [ ] | データフロー図更新 (Drive→Sheets sync) | テキスト図で[REQ-02]レイヤー記述 | [system-design.md](docs/system-design.md) |
| SYS.3 | Medium | [p] | [REQ-02] グラフ仕様追加 (折れ線, 異常値ハイライト) | I/F定義書にフォーマット記述 | [detailed-design.md](docs/detailed-design.md) |

### ソフトウェア開発 (Software Development - SWE)
| プロセスID | 優先度 | ステータス | TODO | 完了基準 | Notes (成果物) |
|---|---|---|---|---|---|
| SWE.1 | Low | [ ] | [REQ-02] トレーサビリティ表拡張 | SYS.1とリンク、派生要件5件以上 | [sw-requirements.md](docs/sw-requirements.md) |
| SWE.2 | Medium | [p] | [REQ-02] 関数図追加 (main → plot_data) | テキストUMLでフロー描画 | [sw-design.md](docs/sw-design.md) |
| SWE.3 | High | [p] | [REQ-02] Sheets Apps Script作成 | スクリプト実行でSheetsに同期 | [implementation.md](docs/implementation.md) |

### テスト & 検証 (Verification & Validation)
| プロセスID | 優先度 | ステータス | TODO | 完了基準 | Notes (成果物) |
|---|---|---|---|---|---|
| V&V.1 | Medium | [ ] | [REQ-02] 異常値抽出テスト (pytest) | カバレッジ80%超え | [unit-tests.md](docs/unit-tests.md) |
| V&V.2 | Medium | [ ] | [REQ-02] E2Eテスト (Docker, iPhone表示) | テスト実行でグラフ表示成功 | [integration-tests.md](docs/integration-tests.md) |
| V&V.3 | Low | [p] | [REQ-02] スケジュールテスト (処理時間<10s) | ログで平均8s以内 | [system-tests.md](docs/system-tests.md) |
| V&V.4 | Low | [p] | [REQ-02] グラフ比較 (7月データ) | Sheetsで192件推移表示OK | [acceptance-tests.md](docs/acceptance-tests.md) |

### サポートプロセス (Support Process - SUP)
| プロセスID | 優先度 | ステータス | TODO | 完了基準 | Notes (成果物) |
|---|---|---|---|---|---|
| SUP.1 | High | [ ] | Actions ci.ymlでpytest追加 ([REQ-02]含む) | GitHub ActionsでSuccessバッジ | [qa-plan.md](docs/qa-plan.md) |
| SUP.2 | Low | [ ] | PRでCodeQLスキャン | PRマージでセキュリティクリア | [verification.md](docs/verification.md) |
| SUP.3 | Medium | [ ] | [REQ-02] Sheets共有リンクテスト | iPhoneアプリでリアルタイムグラフ表示 | [validation.md](docs/validation.md) |
| SUP.4 | Low | [ ] | [REQ-02] 改善案をGemini評価 | フィードバック3つ以上反映 | [joint-review.md](docs/joint-review.md) |
| SUP.5 | Medium | [ ] | Slackアラート追加 ([REQ-02]グラフ失敗) | テストエラーでSlack通知到着 | [audit.md](docs/audit.md) |
| SUP.6 | High | [ ] | deploy.yml作成 (SSH + systemd, [REQ-02]同期) | mainプッシュでラズパイ再起動 | [product-acceptance.md](docs/product-acceptance.md) |
| SUP.7 | Low | [p] | Dependabot PR設定 | 自動PR生成、ライブラリ更新1件適用 | [configuration.md](docs/configuration.md) |
| SUP.8 | Low | [ ] | Issuesテンプレートで[REQ-02]リクエスト | Issue作成&クローズ、変更履歴トレース | [change-request.md](docs/change-request.md) |
| SUP.9 | Medium | [p] | 自動Issue作成 (テスト失敗) | テスト失敗でIssue生成、解決後クローズ | [problem-resolution.md](docs/problem-resolution.md) |
| SUP.10 | Low | [ ] | Insightsで[REQ-02]処理時間レビュー | ダッシュボードで平均時間表示 | [process-improvement.md](docs/process-improvement.md) |

### マネジメントプロセス (Management Process - MAN)
| プロセスID | 優先度 | ステータス | TODO | 完了基準 | Notes (成果物) |
|---|---|---|---|---|---|
| MAN.1 | Medium | [ ] | RISKS.md作成 ([REQ-02]: Sheets制限→代替) | リスト5件以上、対応策記述 | [project-management.md](docs/project-management.md) |

---
*凡例: ステータス [x]=完了, [p]=一部完了, [ ]=未着手*
