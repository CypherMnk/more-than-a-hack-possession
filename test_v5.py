"""Invented V5 cases only. Never inspect or score supplied-match assets."""

from pathlib import Path
import tempfile

from versions.v2_tagged import possession as v2
from versions.v5_control import possession as v5


def main(v5=v5):
    def point(label="H", source="motion", x=10.0):
        return v5.Evidence(label, 2 if source == "motion" else 0 if source == "tag" else 1, source, (x, 20), True)

    unknown = v5.Evidence("X", 0, "missing")
    dead = v5.Evidence("D", 1, "boundary", (-1, 20), False)
    assert v5.segment([point()] * 5) == list("HHHHH")
    assert v5.segment([point(source="proximity")] * 24) == ["X"] * 24
    assert v5.segment([point(source="proximity")] * 25) == ["H"] * 25
    assert v5.segment([point(source="tag")] * 49) == ["X"] * 49
    assert v5.segment([point(source="tag")] * 50) == ["H"] * 50
    assert v5.segment([point()] * 5, adaptive=False) == ["X"] * 5
    assert v5.segment([point()] * 5 + [point("A")] * 4 + [unknown]) == ["H"] * 10
    assert v5.segment([point()] * 5 + [point("A")] * 5) == list("HHHHHAAAAA")
    assert v5.segment([point(source="tag")] * 4 + [point()] * 5) == list("XXXXHHHHH")
    assert v5.segment([point("A")] * 4 + [unknown] + [point("A")] * 5) == list("XXXXXAAAAA")
    blocks = ((1, 5), (7, 11))
    assert v5.segment([point()] * 12, play_blocks=blocks) == list("XHHHHHXHHHHH")
    # Inclusive public block endpoints and reset of evidence across each half.
    for start, end in v5.PLAY_BLOCKS:
        assert v5.block_at(start - 1, v5.PLAY_BLOCKS) is None
        assert v5.block_at(start, v5.PLAY_BLOCKS) is not None
        assert v5.block_at(end, v5.PLAY_BLOCKS) is not None
        assert v5.block_at(end + 1, v5.PLAY_BLOCKS) is None
    assert v5.segment([dead] * 25 + [point(source="tag")] * 60) == ["D"] * 85
    assert v5.segment([dead] * 25 + [point()] * 20) == ["D"] * 45  # placement is not restart
    restart = [dead] * 25 + [point()] * 5 + [point(x=11.1)] * 5
    assert v5.segment(restart) == ["D"] * 30 + ["H"] * 5
    assert v5.segment(restart, restart_guard=False) == ["D"] * 25 + ["H"] * 10
    assert v5.segment([]) == []
    for duration in (0, -1, True, 1.5):
        try:
            v5.segment([], confirm_frames=duration)
            raise AssertionError("Invalid duration accepted.")
        except ValueError:
            pass
    for item in (
        v5.Evidence("Z", 0, "missing"), v5.Evidence("D", 1, "tag"),
        v5.Evidence("H", 2, "rejected"), v5.Evidence("X", 0, "motion"),
        v5.Evidence("H", True, "motion"), v5.Evidence("H", 2, "motion", (float("nan"), 0), True),
        v5.Evidence("H", 2, "motion"), v5.Evidence("D", 1, "boundary", (0, 0), True),
    ):
        try:
            v5.segment([item])
            raise AssertionError("Invalid evidence accepted.")
        except ValueError:
            pass
    for params in (
        {"unknown": 1}, {"relative_control_speed": 0},
        {"restart_distance": float("inf")}, {"max_ball_speed": "fast"},
    ):
        try:
            v5.settings(params)
            raise AssertionError("Invalid settings accepted.")
        except ValueError:
            pass

    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        raw = directory / "invented_tracking.txt"

        def run(balls, home=None, away=None, tags=None, **kwargs):
            home = home if home is not None else [(10, 20)] * len(balls)
            away = away if away is not None else [(50, 20)] * len(balls)

            def group(p):
                return "NaN,NaN,NaN" if p is None else f"{p[0] / 100},{p[1] / 60},NaN"

            raw.write_text(
                "".join(
                    f"{i + 1}:{group(h)};{group(a)}:{group(ball)}\n"
                    for i, (h, a, ball) in enumerate(zip(home, away, balls))
                ), encoding="utf-8",
            )
            return list(v5.observations(
                raw, ["H", "A"], len(balls), (100, 60), tagging=tags, **kwargs,
            ))

        moving = [(10 + i * 0.1, 20) for i in range(7)]
        observed = run(moving, home=moving)
        assert observed[0].source == "proximity"
        assert all(item.source == "motion" and item.label == "H" for item in observed[1:])
        assert v5.segment(observed) == list("XHHHHHH")
        # A passing ball near the opponent cannot become possession via distance or tags.
        passing = run([(49, 20), (50, 20), (51, 20)], tags="AAA")
        assert [item.source for item in passing] == ["proximity", "flight", "flight"]
        no_motion = run([(49, 20), (50, 20), (51, 20)], use_motion=False)
        assert all(item.label == "A" for item in no_motion)
        assert v5.segment(passing, confirm_frames=2) == ["X"] * 3
        assert v5.segment(no_motion, confirm_frames=2) == ["A"] * 3
        contested = run([(30, 20)], home=[(29.8, 20)], away=[(30.2, 20)], tags="H")
        assert contested[0].label == "X" and contested[0].source == "contested"
        assert run([None] * 50, tags="A" * 50)[0].source == "tag"
        assert v5.segment(run([None] * 50, tags="A" * 50)) == ["A"] * 50
        assert v5.segment(run([None] * 50, tags="A" * 50, use_tags=False)) == ["X"] * 50
        assert run([(10, 20), (1000, 20), (10, 20)], tags="AAA")[1].source == "rejected"
        assert run([(10, 20), (1000, 20)], use_guard=False)[1].label == "D"
        assert run([(10, 20), (50, 20), (50, 20)])[2].label == "A"  # reacquisition
        gap = run([(10, 20), None, (10, 20)])
        assert gap[-1].source == "proximity"  # no derivative across missing frame
        swapped = run([(10, 20), (10, 20)], home=[(99, 20), (10, 20)])
        assert swapped[-1].source == "proximity"  # tracklet jump cannot supply co-motion
        assert run([(-0.1, 20)])[0].label == "X"  # uncertain boundary projection
        assert run([(-1, 20)])[0].label == "D"
        halves = run([(10, 20), (10, 20), (1000, 20), (50, 20)], play_blocks=((0, 1), (3, 3)))
        assert halves[-1].label == "A" and halves[-1].source == "proximity"
        assert halves[2].source == "inactive"
        # Full raw-record flow: return/placement is not enough; controlled movement is.
        moving_restart = [(10 + 0.3 * i, 20) for i in range(1, 10)]
        balls = [(-1, 20)] * 25 + [(10, 20)] * 10 + moving_restart
        homes = [(10, 20)] * 35 + moving_restart
        assert v5.segment(run(balls, home=homes)) == ["D"] * 38 + ["H"] * 6
        # Preserve the established team during observed flight, then confirm the receiver.
        flight = [(10 + i, 20) for i in range(1, 11)]
        balls = [(10, 20)] * 6 + flight + [(20, 20)] * 6
        labels = v5.segment(run(balls, away=[(20, 20)] * len(balls), tags="A" * len(balls)))
        assert labels[1:16] == ["H"] * 15 and labels[16:] == ["A"] * 6
        assert run([]) == []
        for tags in ("H", "HHH", "HD"):
            try:
                run([(10, 20)] * 2, tags=tags)
                raise AssertionError("Invalid tags accepted.")
            except ValueError:
                pass
        for record, n in (
            ("2:0.1,0.5,0;0.9,0.5,0:0.1,0.5,0\n", 1),
            ("1:0.1,0.5,0:0.1,0.5,0\n", 1),
            ("1:bad,0.5,0;0.9,0.5,0:0.1,0.5,0\n", 1),
            ("1:0.1,0.5,0;0.9,0.5,0:inf,0.5,0\n", 1),
            ("1:0.1,0.5,0;0.9,0.5,0:0.1,0.5,0\n", 2),
        ):
            raw.write_text(record, encoding="utf-8")
            try:
                list(v5.observations(raw, ["H", "A"], n, (100, 60)))
                raise AssertionError("Invalid tracking accepted.")
            except ValueError:
                pass
        output = directory / "invented_output.csv"
        for iteration in range(2):
            labels = v5.segment(run(moving, home=moving))
            v5.write_csv(output, labels, len(moving))
            v2.validate_csv(output, len(moving))
            if iteration == 0:
                saved = output.read_bytes()
            else:
                assert output.read_bytes() == saved
        try:
            v5.write_csv(output, ["H"], len(moving))
            raise AssertionError("Short output accepted.")
        except ValueError:
            assert output.read_bytes() == saved
    print(f"PASS: {v5.__name__.split('.')[-2]} synthetic control, flight, confidence, restart guard, timeline, validation, and determinism.")


if __name__ == "__main__":
    main()
