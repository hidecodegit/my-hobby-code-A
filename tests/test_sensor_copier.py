import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import os
import sys
import tempfile
import shutil

# プロジェクトルートをパスに追加（CIでimport可能にする）
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensor_copier_v5_20251228 import (
    needs_full_sync,
    get_jst_now,
    build_rclone_cmd,
    read_sensor_data,
    restore_ram_from_persistent,
    get_monthly_filepath,
    LATEST_FILENAME,
)

# === モックデータ定数（モックうっかり防止）===
MOCK_I2C_NORMAL = [0x18, 0x80, 0x00, 0x06, 0x00, 0x00, 0x00]      # ≈25℃, 50%（正常値代表）
MOCK_I2C_ABNORMAL_TEMP = [0x18, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]  # ≈-50℃（異常値専用）

JST = timezone(timedelta(hours=9))


class TestSensorCopier(unittest.TestCase):

    def test_needs_full_sync_only_in_first_15_minutes_of_4hour_slots(self):
        """4時間ごとの同期枠で、最初の15分間のみ同期（教訓: REQ-01遵守 + 4回連続防止）"""
        # 同期すべき時間帯（代表例で汎用的に検証）
        sync_cases = [(0, 10), (4, 5), (8, 14), (12, 0), (16, 10), (20, 14)]
        for hour, minute in sync_cases:
            with self.subTest(hour=hour, minute=minute):
                fake_now = datetime(2025, 12, 29, hour, minute, tzinfo=JST)
                with patch('sensor_copier_v5_20251228.get_jst_now', return_value=fake_now):
                    self.assertTrue(needs_full_sync()[0])

        # 同期すべきでない代表ケース
        no_sync_cases = [(20, 15), (20, 59), (1, 0), (21, 14)]
        for hour, minute in no_sync_cases:
            with self.subTest(hour=hour, minute=minute):
                fake_now = datetime(2025, 12, 29, hour, minute, tzinfo=JST)
                with patch('sensor_copier_v5_20251228.get_jst_now', return_value=fake_now):
                    self.assertFalse(needs_full_sync()[0])

    def test_build_rclone_cmd_always_uses_copy_never_sync(self):
        """rcloneコマンドは常にcopyのみ使用（教訓: INC-001 データ消失防止）"""
        cmd_file = build_rclone_cmd("src/file.txt", "remote:/dest/", is_file=True)
        cmd_dir  = build_rclone_cmd("src/dir/", "remote:/dest/", is_file=False)

        for cmd in [cmd_file, cmd_dir]:
            with self.subTest(cmd=cmd):
                self.assertIn("copy", cmd)
                self.assertNotIn("sync", cmd)

    def test_read_sensor_data_normal_path(self):
        """正常値は正しいフォーマットの文字列を返す（教訓: INC-005 データ形式統一）"""
        mock_bus = MagicMock()
        mock_bus.read_i2c_block_data.return_value = MOCK_I2C_NORMAL

        fake_now = datetime(2025, 7, 28, 12, 34, 56, tzinfo=JST)
        with patch('sensor_copier_v5_20251228.get_jst_now', return_value=fake_now):
            result = read_sensor_data(mock_bus)

        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith("2025-07-28 12:34:56,"))
        self.assertIn("tmp=", result)
        self.assertIn("hum=", result)

    def test_read_sensor_data_abnormal_values_return_none(self):
        """範囲外値はNoneを返して欠損を防ぐ（教訓: 異常値によるデータ破損防止）"""
        mock_bus = MagicMock()
        mock_bus.read_i2c_block_data.return_value = MOCK_I2C_ABNORMAL_TEMP

        result = read_sensor_data(mock_bus)
        self.assertIsNone(result)

    def test_data_restorer_handles_missing_and_empty_files(self):
        """再起動耐性: 欠如ファイル・空ファイルを永続領域から復元（教訓: INC-006）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistent_dir = os.path.join(tmpdir, "persistent")
            ram_dir = os.path.join(tmpdir, "ram")
            os.makedirs(persistent_dir)
            os.makedirs(ram_dir)

            # 永続側にダミーデータ準備
            monthly_p = get_monthly_filepath(persistent_dir)
            latest_p = os.path.join(persistent_dir, LATEST_FILENAME)
            with open(monthly_p, "w") as f: f.write("persistent monthly data\n")
            with open(latest_p, "w") as f: f.write("persistent latest data\n")

            # RAM側: 月次欠如、latestは空ファイル
            latest_r = os.path.join(ram_dir, LATEST_FILENAME)
            open(latest_r, "w").close()  # 0byteファイル

            # 復元実行
            with patch('sensor_copier_v5_20251228.RAM_DATA_DIR', ram_dir), \
                 patch('sensor_copier_v5_20251228.PERSISTENT_DATA_DIR', persistent_dir):
                restore_ram_from_persistent()

            # 復元確認
            monthly_r = get_monthly_filepath(ram_dir)
            self.assertTrue(os.path.exists(monthly_r))
            self.assertGreater(os.path.getsize(monthly_r), 0)
            self.assertGreater(os.path.getsize(latest_r), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)