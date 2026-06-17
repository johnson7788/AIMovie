import os
import sqlite3
import tempfile
import unittest

import user_works as user_works_service


class TestUserWorks(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_user_works_")
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE tasks (
                task_id TEXT PRIMARY KEY,
                mode TEXT,
                status TEXT,
                result TEXT,
                error TEXT,
                working_dir TEXT,
                user_id TEXT,
                title TEXT,
                prompt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        user_works_service.init_works_tables(self.conn)

    def test_create_and_list_work(self):
        shot_dir = os.path.join(self.tmpdir, "shots", "0")
        os.makedirs(shot_dir, exist_ok=True)
        with open(os.path.join(shot_dir, "first_frame.png"), "wb") as handle:
            handle.write(b"png")
        final_video = os.path.join(self.tmpdir, "final_video.mp4")
        with open(final_video, "wb") as handle:
            handle.write(b"mp4")

        work = user_works_service.create_work_from_task(
            self.conn,
            user_id="user-1",
            task_id="task-1",
            title="测试作品",
            prompt="一只猫",
            mode="idea2video",
            result_path=final_video,
            working_dir=self.tmpdir,
        )
        self.assertEqual(work["title"], "测试作品")
        self.assertIn("/api/tasks/task-1/files/shots/0/first_frame.png", work["cover"])

        items, total = user_works_service.list_user_works(self.conn, "user-1")
        self.assertEqual(total, 1)
        self.assertEqual(items[0]["task_id"], "task-1")

    def test_delete_work(self):
        user_works_service.create_work_from_task(
            self.conn,
            user_id="user-1",
            task_id="task-2",
            title="待删除",
            prompt="",
            mode="script2video",
            result_path="final_video.mp4",
            working_dir=self.tmpdir,
        )
        row = self.conn.execute(
            "SELECT id FROM user_works WHERE task_id = ?", ("task-2",)
        ).fetchone()
        deleted = user_works_service.delete_user_work(self.conn, "user-1", row["id"])
        self.assertTrue(deleted)


if __name__ == "__main__":
    unittest.main()
