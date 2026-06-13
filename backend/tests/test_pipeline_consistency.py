import unittest

from interfaces import ShotDescription
from utils.pipeline_consistency import build_crossfade_schedule


def _shot(idx: int, cam_idx: int) -> ShotDescription:
    return ShotDescription(
        idx=idx,
        is_last=idx == 2,
        cam_idx=cam_idx,
        visual_desc=f"shot {idx}",
        variation_type="small",
        variation_reason="small variation",
        ff_desc="ff",
        ff_vis_char_idxs=[],
        lf_desc="lf",
        lf_vis_char_idxs=[],
        motion_desc="motion",
        audio_desc="audio",
    )


class TestPipelineConsistency(unittest.TestCase):
    def test_same_camera_hard_cut(self):
        shots = [_shot(0, 0), _shot(1, 0), _shot(2, 0)]
        self.assertEqual(build_crossfade_schedule(shots), [0.0, 0.0])

    def test_different_camera_short_fade(self):
        shots = [_shot(0, 0), _shot(1, 1)]
        self.assertEqual(build_crossfade_schedule(shots), [0.12])

    def test_mixed_schedule(self):
        shots = [_shot(0, 0), _shot(1, 0), _shot(2, 1)]
        self.assertEqual(build_crossfade_schedule(shots), [0.0, 0.12])


if __name__ == "__main__":
    unittest.main()
