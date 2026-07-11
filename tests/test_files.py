from discord_username_checker import cli


def test_load_usernames_filters_and_dedupes(tmp_path):
    f = tmp_path / "names.txt"
    f.write_text(
        "\n".join(
            [
                "cool",
                "COOL",        # same as cool after lowercasing -> deduped
                ".bad",        # leading dot -> dropped
                "a",           # too short -> dropped
                "with space",  # space stripped -> "withspace"
                "nice_1",
                "",            # blank -> skipped
            ]
        )
    )
    names = cli.load_usernames(str(f))
    assert names == ["cool", "withspace", "nice_1"]
