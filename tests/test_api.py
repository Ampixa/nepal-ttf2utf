"""Public package API tests."""

import hashlib
import json
from types import MappingProxyType

import pytest

import nepal_ttf2utf as package_module
from nepal_ttf2utf import __version__, convert, convert_devanagari, supported_fonts

_EXPECTED_ROUTE_GROUPS = {
    "brahmi-unicode": ("Brahmi", 4, True),
    "devanagari-legacy": ("Devanagari", 7, False),
    "devanagari-unicode": ("Devanagari", 19, True),
    "gurung-khema-unicode": ("Gurung Khema", 6, True),
    "jg-lepcha": ("Lepcha", 3, False),
    "kirat-rai-canonical": ("Kirat Rai", 5, False),
    "kirat-rai-herald": ("Kirat Rai", 3, False),
    "kirat-rai-unicode": ("Kirat Rai", 5, True),
    "lepcha-herald": ("Lepcha", 3, False),
    "lepcha-unicode": ("Lepcha", 8, True),
    "limbu-legacy": ("Limbu", 4, False),
    "limbu-unicode": ("Limbu", 13, True),
    "newa-unicode": ("Newa", 12, True),
    "ol-chiki-latic": ("Ol Chiki", 6, False),
    "ol-chiki-optimum": ("Ol Chiki", 6, False),
    "ol-chiki-unicode": ("Ol Chiki", 7, True),
    "sunuwar-legacy": ("Sunuwar", 4, False),
    "sunuwar-unicode": ("Sunuwar", 6, True),
    "tibetan-machine": ("Tibetan", 2, False),
    "tibetan-unicode": ("Tibetan", 14, True),
    "tirhuta-legacy": ("Tirhuta", 3, False),
    "tirhuta-unicode": ("Tirhuta", 6, True),
}


def test_version_matches_release():
    assert __version__ == "0.3.0"


@pytest.mark.parametrize(
    ("font", "script"),
    [
        ("preeti", "Devanagari"),
        ("namdhinggo", "Limbu"),
        ("kiratraifont", "Kirat Rai"),
        ("kiratraifontnew", "Kirat Rai"),
        ("koits", "Sunuwar"),
        ("tibetanmachine", "Tibetan"),
        ("lepcha-sikkimherald", "Lepcha"),
        ("jg-lepcha", "Lepcha"),
        ("olck-optimum", "Ol Chiki"),
        ("olcklatic-normal", "Ol Chiki"),
        ("janaki", "Tirhuta"),
        ("annapurnasilnepal", "Devanagari"),
        ("nithyaranjanadu", "Devanagari"),
        ("nithyaranjananu", "Newa"),
        ("magar-akkha-brahmi", "Brahmi"),
        ("namdhinggo-regular", "Limbu"),
        ("kanchenjunga-regular", "Kirat Rai"),
        ("notosanssunuwar-regular", "Sunuwar"),
        ("notosansgurungkhema", "Gurung Khema"),
    ],
)
def test_supported_fonts_covers_every_converter_family(font, script):
    assert supported_fonts()[font] == script


def test_font_alias_registry_is_complete_normalized_and_globally_disjoint():
    route_groups = package_module._FONT_ROUTE_GROUPS
    assert type(route_groups) is MappingProxyType
    assert {
        route_name: (script, len(aliases), is_unicode)
        for route_name, (script, aliases, is_unicode) in route_groups.items()
    } == _EXPECTED_ROUTE_GROUPS

    supported: dict[str, str] = {}
    unicode_routes: dict[str, str] = {}
    owners: dict[str, str] = {}
    aliases_by_group: list[str] = []
    legacy_alias_count = 0
    unicode_alias_count = 0
    for route_name, (script, aliases, is_unicode) in route_groups.items():
        assert type(aliases) is frozenset
        assert type(is_unicode) is bool
        aliases_by_group.extend(aliases)
        if is_unicode:
            unicode_alias_count += len(aliases)
        else:
            legacy_alias_count += len(aliases)
        for alias in aliases:
            assert package_module._normalize_font_key(alias) == alias
            assert alias not in owners
            supported[alias] = script
            owners[alias] = route_name
            if is_unicode:
                unicode_routes[alias] = script

    assert len(route_groups) == 22
    assert legacy_alias_count == 46
    assert unicode_alias_count == 100
    assert len(aliases_by_group) == 146
    assert len(set(aliases_by_group)) == 146
    assert dict(package_module._SUPPORTED_FONT_SCRIPTS) == supported
    assert dict(package_module._UNICODE_FONT_SCRIPTS) == unicode_routes
    assert dict(package_module._FONT_ALIAS_ROUTES) == owners
    assert supported_fonts() == supported


def test_font_alias_collections_and_registry_snapshots_are_immutable():
    registries = (
        package_module._FONT_ROUTE_GROUPS,
        package_module._SUPPORTED_FONT_SCRIPTS,
        package_module._UNICODE_FONT_SCRIPTS,
        package_module._FONT_ALIAS_ROUTES,
    )
    for registry in registries:
        assert type(registry) is MappingProxyType
        with pytest.raises(TypeError):
            registry["forged"] = "forged"

    for _script, aliases, _is_unicode in package_module._FONT_ROUTE_GROUPS.values():
        assert type(aliases) is frozenset
        with pytest.raises(AttributeError):
            aliases.add("forged")


def test_supported_font_catalog_has_exact_snapshot_digest():
    payload = json.dumps(supported_fonts(), sort_keys=True, separators=(",", ":")).encode()
    assert len(supported_fonts()) == 146
    assert len(payload) == 4_196
    assert hashlib.sha256(payload).hexdigest() == (
        "dd2adfacfed5310d843363fac313fe2e52f7c20a66a2fa788af953904c2221ca"
    )


def test_supported_fonts_returns_an_isolated_mutable_copy():
    first = supported_fonts()
    original = supported_fonts()
    assert first is not original

    first["forged"] = "Newa"
    del first["preeti"]

    assert supported_fonts() == original
    assert "forged" not in package_module._SUPPORTED_FONT_SCRIPTS
    assert "preeti" in package_module._SUPPORTED_FONT_SCRIPTS


@pytest.mark.parametrize("marker", [None, 0, 1, "yes"])
def test_font_alias_contract_rejects_non_boolean_unicode_markers(marker):
    with pytest.raises(ValueError, match="Unicode marker must be Boolean"):
        package_module._build_font_alias_contract(
            {"test-route": ("Limbu", frozenset({"test-font"}), marker)}
        )


@pytest.mark.parametrize(
    ("route_groups", "message"),
    [
        (
            {"test-route": ("Limbu", {"test-font"}, False)},
            "aliases must be a frozenset",
        ),
        (
            {"test-route": ("Unsupported", frozenset({"test-font"}), False)},
            "has unsupported script",
        ),
        (
            {"test-route": ("Limbu", frozenset(), False)},
            "has no aliases",
        ),
    ],
)
def test_font_alias_contract_rejects_malformed_route_groups(route_groups, message):
    with pytest.raises(ValueError, match=message):
        package_module._build_font_alias_contract(route_groups)


@pytest.mark.parametrize(
    "alias",
    ["Test-Font", "test_font", " test-font ", "ABCDEF+test-font"],
)
def test_font_alias_contract_rejects_unnormalized_aliases(alias):
    with pytest.raises(ValueError, match="has unnormalized alias"):
        package_module._build_font_alias_contract(
            {"test-route": ("Limbu", frozenset({alias}), False)}
        )


def test_font_alias_contract_rejects_cross_route_duplicates():
    with pytest.raises(
        ValueError,
        match=r"font alias 'shared' overlaps routes 'first' and 'second'",
    ):
        package_module._build_font_alias_contract(
            {
                "first": ("Limbu", frozenset({"shared"}), False),
                "second": ("Sunuwar", frozenset({"shared"}), True),
            }
        )


def test_every_advertised_font_key_reaches_a_dispatch_route():
    for font in supported_fonts():
        assert convert("", font=font) == "", font


@pytest.mark.parametrize(
    ("font", "source", "expected"),
    [
        ("  JG-LEPCHA  ", "k", "ᰀ"),
        ("AbCdEf+JG_LEPCHA", "k", "ᰀ"),
        ("ABCDEF+PREETI", "g]kfn", "नेपाल"),
    ],
)
def test_font_key_normalization_preserves_supported_routes(font, source, expected):
    assert convert(source, font=font, strict=True) == expected


def test_pdf_subset_font_prefix_is_ignored():
    assert convert("𑑅", font="ABCDEF+NithyaRanjanaNU-Regular", strict=True) == "𑑅"


@pytest.mark.parametrize(
    ("font", "source", "mapped"),
    [
        ("preeti", "g]kfn", "नेपाल"),
        ("namdhinggo", "k", "ᤐ"),
        ("kiratraifontnew", "N", "𖵈"),
        ("kiratraifont", "f", "𖵈"),
        ("sunuwar", "o", "𑯀"),
        ("lepcha-sikkimherald", "A", "ᰀ"),
        ("jg-lepcha", "k", "ᰀ"),
        ("olck-optimum", "a", "ᱟ"),
        ("olcklatic-normal", "a", "ᱟ"),
        ("janaki", "क", "𑒏"),
        ("tibetanmachine", "!", "ཀ"),
    ],
)
def test_every_legacy_route_preserves_structural_whitespace(font, source, mapped):
    separators = " \t\r\n"
    assert convert(source + separators + source, font=font, strict=True) == (
        mapped + separators + mapped
    )


@pytest.mark.parametrize(
    ("font", "normalized_key"),
    [
        ("does-not-exist", "does-not-exist"),
        ("  Does_Not_Exist  ", "does-not-exist"),
        ("ABCDEF+Unknown_Font", "unknown-font"),
        ("ABCDE+Madan2", "abcde+madan2"),
        ("   ", ""),
    ],
)
def test_unknown_font_reports_normalized_package_key(font, normalized_key):
    with pytest.raises(ValueError) as error:
        convert("text", font=font)

    message = str(error.value)
    assert f"unsupported font key {normalized_key!r}" in message
    assert "supported_fonts()" in message
    assert "--list-fonts" in message
    assert "Devanagari" not in message
    assert "supported: [" not in message


def test_direct_devanagari_api_retains_its_specialized_unknown_font_error():
    with pytest.raises(ValueError, match="unsupported Devanagari font"):
        convert_devanagari("text", font="does-not-exist")


@pytest.mark.parametrize("font", [None, 123, b"preeti"])
def test_non_string_font_key_has_an_explicit_type_error(font):
    with pytest.raises(TypeError, match="font must be a string"):
        convert("text", font=font)
