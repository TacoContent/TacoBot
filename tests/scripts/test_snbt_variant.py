import json
from pathlib import Path

import pytest

from bot.lib.minecraft.item import calculate_variant_id, calculate_variant_id_from_snbt
from scripts.snbt_variant import main


def test_default_variant_raw_outputs_digest(capsys):
    ret = main(["minecraft:stone", "--raw"])
    assert ret == 0
    captured = capsys.readouterr()
    out = captured.out.strip()
    assert len(out) == 64
    # Confirm it matches the library function for default (no NBT)
    expected = calculate_variant_id("minecraft:stone", None)
    assert out == expected


def test_snbt_string_matches_library(capsys):
    snbt = '{id:"minecraft:stone",count:1}'
    ret = main(["minecraft:stone", "--snbt", snbt, "--raw"])
    assert ret == 0
    captured = capsys.readouterr()
    out = captured.out.strip()
    expected = calculate_variant_id_from_snbt("minecraft:stone", snbt)
    assert out == expected


def test_nbt_json_matches_library(capsys):
    nbt = {"display": {"Name": '{"text":"My Stone"}'}}
    nbt_json = json.dumps(nbt)
    ret = main(["minecraft:stone", "--nbt-json", nbt_json, "--raw"])
    assert ret == 0
    captured = capsys.readouterr()
    out = captured.out.strip()
    expected = calculate_variant_id("minecraft:stone", nbt)
    assert out == expected


def test_snbt_file_and_nbt_json_file(tmp_path, capsys):
    snbt = '{id:"minecraft:diamond",count:1}'
    snbt_file = tmp_path / "snbt.txt"
    snbt_file.write_text(snbt, encoding="utf-8")

    ret = main(["minecraft:diamond", "--snbt-file", str(snbt_file), "--raw"])
    assert ret == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == calculate_variant_id_from_snbt("minecraft:diamond", snbt)

    nbt = {"display": {"Name": '"Diamond"'}}
    nbt_file = tmp_path / "nbt.json"
    nbt_file.write_text(json.dumps(nbt), encoding="utf-8")

    ret2 = main(["minecraft:diamond", "--nbt-json-file", str(nbt_file), "--raw"])
    assert ret2 == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == calculate_variant_id("minecraft:diamond", nbt)


def test_missing_files_return_error(capsys):
    ret = main(["minecraft:stone", "--snbt-file", "no-such-file.txt"])
    assert ret == 2
    captured = capsys.readouterr()
    assert "SNBT file not found" in captured.err


def test_invalid_nbt_json_returns_error(capsys):
    ret = main(["minecraft:stone", "--nbt-json", "{invalid json"])
    assert ret == 2
    captured = capsys.readouterr()
    assert "Failed to parse NBT JSON" in captured.err
