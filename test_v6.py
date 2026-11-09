"""Invented V6 regression cases; no competition files or outputs are read."""

from pathlib import Path
import subprocess
import sys
import tempfile

from test_v5 import main as check_control
from versions.v5_control import possession as v5
from versions.v6_control import possession as v6


def main():
    check_control(v6)
    assert v6.DEFAULTS == v5.DEFAULTS  # No new or match-tuned thresholds.
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "invented.txt"

        def run(balls, visible=0, **kwargs):
            def group(point):
                return "NaN,NaN,NaN" if point is None else f"{point[0] / 100},{point[1] / 60},NaN"

            path.write_text("".join(
                f"{i + 1}:{group((10, 20) if i < visible else None)};"
                f"{group((50, 20) if i < visible else None)}:{group(ball)}\n"
                for i, ball in enumerate(balls)
            ), encoding="utf-8")
            return list(v6.observations(
                path, ["H", "A"], len(balls), (100, 60),
                tagging="A" * len(balls), **kwargs,
            ))

        balls = [(10, 20)] * 6 + [(10 + 0.2 * (i + 1), 20) for i in range(55)]
        evidence = run(balls, visible=6)
        assert all(item.source == "flight" for item in evidence[6:])
        assert v6.segment(evidence) == ["X"] + ["H"] * 60
        # The frozen old algorithm reproduces the unintended tag-driven switch.
        old = list(v5.observations(
            path, ["H", "A"], len(balls), (100, 60), tagging="A" * len(balls),
        ))
        assert v5.segment(old)[6:] == ["A"] * 55
        assert all(item.source == "flight" for item in run(balls, visible=6, use_tags=False)[6:])
        assert v6.segment(run(balls, visible=6, use_motion=False))[6:] == ["A"] * 55
        # With no motion evidence, the existing weak fallback is still available.
        stationary = run([(10, 20)] * 50)
        assert all(item.source == "tag" for item in stationary)
        assert v6.segment(stationary) == ["A"] * 50
        gap = run([(10, 20), None, (11, 20), (11.2, 20)])
        assert [item.source for item in gap] == ["tag", "tag", "tag", "flight"]
        assert run([(10, 20), (1000, 20)])[1].source == "rejected"
        assert run([(10, 20), (10.2, 20)], play_blocks=((0, 0), (1, 1)))[1].source == "tag"
        assert run([(-0.1, 20)])[0].source == "ambiguous"
        assert run([(-1, 20)])[0].source == "boundary"
        # Reject dangerous output paths before any dataset is read.
        for output in (
            Path(directory) / "source.py",
            Path(directory) / ".git" / "result.csv",
            Path(directory) / ".venv" / "result.csv",
            Path(directory) / "node_modules" / "result.csv",
            Path(directory) / "result.csv",  # Inside the requested input folder.
        ):
            failed = subprocess.run([
                sys.executable, str(Path(v6.__file__).resolve()),
                "--data-dir", directory, "--out", str(output),
            ], capture_output=True)
            assert failed.returncode == 2 and not output.exists()
        protected = Path(directory) / "source.py"
        protected.write_text("# invented source\n", encoding="utf-8")
        subprocess.run([
            sys.executable, str(Path(v6.__file__).resolve()),
            "--data-dir", directory, "--out", str(protected),
        ], capture_output=True, check=False)
        assert protected.read_text(encoding="utf-8") == "# invented source\n"
    print("PASS: V6 missing-player flight veto, fallback, motion resets, and frozen-default regression.")


if __name__ == "__main__":
    main()
