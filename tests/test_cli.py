"""Command-line interface tests."""

import io

import pytest

from nepal_ttf2utf.cli import main


def test_cli_converts_positional_text(capsys):
    assert main(["--font", "preeti", "g]kfn"]) == 0
    assert capsys.readouterr().out == "नेपाल"


def test_cli_validates_madan2_unicode_text(capsys):
    assert main(["--font", "Madan2", "--strict", "नेपाल"]) == 0
    assert capsys.readouterr().out == "नेपाल"


def test_cli_lists_fonts(capsys):
    assert main(["--list-fonts"]) == 0
    output = capsys.readouterr().out
    assert "janaki\tTirhuta\n" in output
    assert "jg-lepcha\tLepcha\n" in output
    assert "olck-optimum\tOl Chiki\n" in output
    assert "olcklatic-normal\tOl Chiki\n" in output
    assert "nithyaranjananu\tNewa\n" in output
    assert "magar-akkha-brahmi\tBrahmi\n" in output
    assert "madan2\tDevanagari\n" in output
    assert "namdhinggo-regular\tLimbu\n" in output
    assert "notosansgurungkhema\tGurung Khema\n" in output


def test_cli_reads_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("k"))
    assert main(["--font", "jg-lepcha"]) == 0
    assert capsys.readouterr().out == "ᰀ"


def test_cli_preserves_multiline_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("g]kfn\n\tdu/"))
    assert main(["--font", "preeti", "--strict"]) == 0
    assert capsys.readouterr().out == "नेपाल\n\tमगर"


def test_cli_reads_legacy_file_encoding_and_preserves_exact_line_endings(tmp_path):
    source = tmp_path / "legacy.txt"
    target = tmp_path / "unicode.txt"
    source.write_bytes(b"\xc0\r\n\xc0\r\xc0")

    assert (
        main(
            [
                "--font",
                "jg-lepcha",
                "--input-file",
                str(source),
                "--input-encoding",
                "cp1252",
                "--output-file",
                str(target),
                "--strict",
            ]
        )
        == 0
    )
    assert target.read_bytes() == "ᰀᰤ\r\nᰀᰤ\rᰀᰤ".encode()


def test_cli_strict_mode_has_clean_error(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--font", "jg-lepcha", "--strict", "~"])
    assert error.value.code == 2
    assert "U+007E" in capsys.readouterr().err


def test_cli_strict_mode_reports_jg_lepcha_placeholder_source_and_output(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--font", "jg-lepcha", "--strict", "="])
    assert error.value.code == 2
    message = capsys.readouterr().err
    assert "U+003D" in message
    assert "U+25CC" in message


def test_cli_strict_mode_rejects_a_pinned_reserved_output_position(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--font", "kiratraifontnew", "--strict", "\U00016d7a"])
    assert error.value.code == 2
    assert "U+16D7A" in capsys.readouterr().err


def test_cli_strict_devanagari_reports_dependency_deletion(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--font", "preeti", "--strict", r"\f"])
    assert error.value.code == 2
    message = capsys.readouterr().err
    assert "U+005C" in message
    assert "U+0066" in message


def test_cli_devanagari_uses_the_pinned_assigned_repertoire(capsys):
    assert main(["--font", "preeti", "--strict", "\U00011b00"]) == 0
    assert capsys.readouterr().out == "\U00011b00"

    with pytest.raises(SystemExit) as error:
        main(["--font", "preeti", "--strict", "\U00011b0a"])
    assert error.value.code == 2
    assert "U+11B0A" in capsys.readouterr().err


def test_cli_requires_font(capsys):
    with pytest.raises(SystemExit) as error:
        main(["g]kfn"])
    assert error.value.code == 2
    assert "--font is required" in capsys.readouterr().err


def test_cli_unknown_font_reports_package_key_and_discovery_hint(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--font", "ABCDEF+Does_Not_Exist", "text"])
    assert error.value.code == 2

    streams = capsys.readouterr()
    assert streams.out == ""
    message = streams.err
    assert "unsupported font key 'does-not-exist'" in message
    assert "--list-fonts" in message
    assert "Devanagari" not in message


def test_cli_rejects_two_input_sources(tmp_path, capsys):
    source = tmp_path / "legacy.txt"
    source.write_text("k", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main(["--font", "jg-lepcha", "text", "--input-file", str(source)])
    assert error.value.code == 2
    assert "cannot be used together" in capsys.readouterr().err
