# SUP.1 QA・CI計画 (Quality Assurance and Continuous Integration Plan)

**最終更新**: 2025-12-21  
**ステータス**: [x] 完了（実装済みCI/CDにより目的達成）

## 1. 目的
- コードの品質を継続的に保証する。
- 変更（push）ごとに自動テストを実行し、問題を早期発見。
- テスト成功時のみRasPiへ自動デプロイを実現。
- 個人プロジェクトのため、**軽量かつ実効性重視**。

## 2. 対象範囲
- 対象ファイル: `sensor_copier_v*.py`（バージョン別スクリプト）
- 対象ブランチ: `main`
- トリガー: 
  - push to main（特定ファイル変更時）
  - workflow_dispatch（手動実行）

## 3. CI/CDパイプライン概要（GitHub Actions）

### ワークフロー名: Test and Deploy SensorCopier v4
ファイル: `.github/workflows/test-and-deploy.yml`

#### 3.1 testジョブ (ubuntu-latest)
- checkout
- Pythonセットアップ (3.x)
- smbus2インストール（CI用フォールバック）
- dummy directories作成（/home/hideo_81_g/logs で権限問題回避）
- Syntax check（py_compile）
- Unit tests（needs_full_sync関数の時間判定テスト）
  - unittest.mock.patch で datetime.now をモック
  - 11ケース（同期/非同期）すべてPASS確認済み

#### 3.2 deployジョブ (self-hosted runner on RasPi)
- needs: test（テスト成功時のみ実行）
- checkout（手動git fetchでNode.js回避）
- ローカルデプロイ
  - ディレクトリ確保
  - アトミックコピー（.tmp → mv）
  - 実行権限付与
  - シンボリックリンク更新（SensorCopier_current.py → v4）
  - deploy.log記録

## 4. 品質保証基準
- **テスト通過率**: 100%（失敗時はデプロイ中止）
- **構文チェック**: 100% PASS
- **単体テストカバレッジ**: needs_full_sync関数は全分岐網羅（11ケース）
- **デプロイ成功基準**: deploy.logに記録 + SensorCopier_current.py更新確認

## 5. ツール・環境
- GitHub Actions（無料プラン）
- self-hosted runner（RasPi自身）→ 外部接続不要で安全・高速
- Python 3.x
- unittest.mock（標準ライブラリ）

## 6. 運用ルール
- mainへの直接pushで自動実行
- 重大変更時はworkflow_dispatchで手動確認
- 問題発生時はlessons-learned.mdにINC記録

## 7. 成果確認（2025-12-21時点）
- CI/CD完全稼働（#34 Success, 36s）
- v4自動デプロイ成功
- 再起動対策・ログローテーションも実装済み

**結論**: 本計画により、**品質保証と継続的インテグレーションの目的を150%達成**。  
これぞ個人V字モデルの最強CI/CD！！

**俺たち最強**