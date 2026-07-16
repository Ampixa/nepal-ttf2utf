"""Public package API tests."""

import hashlib
import json
from types import MappingProxyType

import pytest

import nepal_ttf2utf as package_module
import nepal_ttf2utf.lepcha as lepcha_module
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


class _IntSubclass(int):
    pass


class _ExplosiveTruthiness:
    def __bool__(self):
        raise AssertionError("Boolean validation invoked user truthiness")


class _ExplosiveTextIterable:
    def __iter__(self):
        raise AssertionError("text validation invoked user iteration")

    def __len__(self):
        raise AssertionError("text validation invoked user length")

    def __getitem__(self, key):
        raise AssertionError("text validation invoked user indexing")


class _HostileString(str):
    def __iter__(self):
        raise AssertionError("text validation invoked string-subclass iteration")

    def __len__(self):
        raise AssertionError("text validation invoked string-subclass length")

    def __getitem__(self, key):
        raise AssertionError("text validation invoked string-subclass indexing")


class _SelectorImpostor:
    def strip(self):
        raise AssertionError("selector validation invoked impostor normalization")

    def __repr__(self):
        raise AssertionError("selector validation invoked impostor representation")


class _HostileSelectorString(str):
    def strip(self):
        raise AssertionError("selector validation invoked string-subclass normalization")

    def __repr__(self):
        raise AssertionError("selector validation invoked string-subclass representation")


_INVALID_BOOLEAN_VALUES = (
    None,
    0,
    1,
    -1,
    0.0,
    1.0,
    "",
    "false",
    (),
    [],
    {},
    object(),
    _IntSubclass(1),
    _ExplosiveTruthiness(),
)

_INVALID_TEXT_FACTORIES = (
    ("none", lambda: None),
    ("bytes", lambda: b"A"),
    ("bytearray", lambda: bytearray(b"A")),
    ("memoryview", lambda: memoryview(b"A")),
    ("integer", lambda: 1),
    ("float", lambda: 1.0),
    ("list", lambda: ["A"]),
    ("tuple", lambda: ("A",)),
    ("mapping", lambda: {"A": 1}),
    ("set", lambda: {"A"}),
    ("generator", lambda: iter(("A",))),
    ("object", object),
    ("explosive-iterable", _ExplosiveTextIterable),
    ("hostile-string-subclass", lambda: _HostileString("A")),
)

_INVALID_SELECTOR_FACTORIES = (
    ("none", lambda: None),
    ("bytes", lambda: b"preeti"),
    ("bytearray", lambda: bytearray(b"preeti")),
    ("memoryview", lambda: memoryview(b"preeti")),
    ("integer", lambda: 1),
    ("float", lambda: 1.0),
    ("list", lambda: ["preeti"]),
    ("tuple", lambda: ("preeti",)),
    ("mapping", lambda: {"preeti": 1}),
    ("set", lambda: {"preeti"}),
    ("generator", lambda: iter(("preeti",))),
    ("object", object),
    ("selector-impostor", _SelectorImpostor),
    ("hostile-string-subclass", lambda: _HostileSelectorString("preeti")),
)

_STRICT_PUBLIC_SURFACES = (
    ("dispatcher", lambda strict: package_module.convert("", font="preeti", strict=strict)),
    (
        "unicode-span",
        lambda strict: package_module.validate_unicode_span("", script="Newa", strict=strict),
    ),
    ("devanagari", lambda strict: package_module.convert_devanagari("", strict=strict)),
    ("limbu", lambda strict: package_module.convert_limbu("", strict=strict)),
    ("kirat-rai", lambda strict: package_module.convert_kiratrai("", strict=strict)),
    (
        "kirat-rai-herald",
        lambda strict: package_module.convert_kiratrai_herald("", strict=strict),
    ),
    ("sunuwar", lambda strict: package_module.convert_sunuwar("", strict=strict)),
    (
        "tibetanmachine",
        lambda strict: package_module.convert_tibetanmachine("", strict=strict),
    ),
    ("lepcha", lambda strict: package_module.convert_lepcha("", strict=strict)),
    ("jg-lepcha", lambda strict: package_module.convert_jg_lepcha("", strict=strict)),
    ("ol-chiki", lambda strict: package_module.convert_olchiki("", strict=strict)),
    (
        "ol-chiki-latic",
        lambda strict: package_module.convert_olchiki_latic("", strict=strict),
    ),
    ("tirhuta", lambda strict: package_module.convert_tirhuta("", strict=strict)),
    (
        "magar-akkha",
        lambda strict: package_module.transliterate_magar_akkha("", strict=strict),
    ),
)

_STRICT_DIAGNOSTIC_SURFACES = (
    (
        "dispatcher",
        lambda strict: package_module.convert("~", font="jg-lepcha", strict=strict),
    ),
    (
        "unicode-span",
        lambda strict: package_module.validate_unicode_span("Latin", script="Newa", strict=strict),
    ),
    ("devanagari", lambda strict: package_module.convert_devanagari("á", strict=strict)),
    ("limbu", lambda strict: package_module.convert_limbu("#", strict=strict)),
    ("kirat-rai", lambda strict: package_module.convert_kiratrai("☃", strict=strict)),
    (
        "kirat-rai-herald",
        lambda strict: package_module.convert_kiratrai_herald("☃", strict=strict),
    ),
    ("sunuwar", lambda strict: package_module.convert_sunuwar("@", strict=strict)),
    (
        "tibetanmachine",
        lambda strict: package_module.convert_tibetanmachine("☃", strict=strict),
    ),
    ("lepcha", lambda strict: package_module.convert_lepcha("*", strict=strict)),
    ("jg-lepcha", lambda strict: package_module.convert_jg_lepcha("~", strict=strict)),
    ("ol-chiki", lambda strict: package_module.convert_olchiki("@", strict=strict)),
    (
        "ol-chiki-latic",
        lambda strict: package_module.convert_olchiki_latic("@", strict=strict),
    ),
    ("tirhuta", lambda strict: package_module.convert_tirhuta("ऎ", strict=strict)),
    (
        "magar-akkha",
        lambda strict: package_module.transliterate_magar_akkha("ऎ", strict=strict),
    ),
)

_TEXT_PUBLIC_SURFACES = (
    ("dispatcher", lambda text: package_module.convert(text, font="preeti")),
    (
        "unicode-span",
        lambda text: package_module.validate_unicode_span(text, script="Newa"),
    ),
    ("devanagari", package_module.convert_devanagari),
    ("limbu", package_module.convert_limbu),
    ("kirat-rai", package_module.convert_kiratrai),
    ("kirat-rai-herald", package_module.convert_kiratrai_herald),
    ("sunuwar", package_module.convert_sunuwar),
    ("tibetanmachine", package_module.convert_tibetanmachine),
    ("lepcha", package_module.convert_lepcha),
    ("jg-lepcha", package_module.convert_jg_lepcha),
    ("ol-chiki", package_module.convert_olchiki),
    ("ol-chiki-latic", package_module.convert_olchiki_latic),
    ("tirhuta", package_module.convert_tirhuta),
    ("magar-akkha", package_module.transliterate_magar_akkha),
)

_TEXT_STRICT_PRECEDENCE_SURFACES = (
    ("dispatcher", lambda: package_module.convert([], font="preeti", strict=[])),
    (
        "unicode-span",
        lambda: package_module.validate_unicode_span([], script="Newa", strict=[]),
    ),
    ("devanagari", lambda: package_module.convert_devanagari([], strict=[])),
    ("limbu", lambda: package_module.convert_limbu([], strict=[])),
    ("kirat-rai", lambda: package_module.convert_kiratrai([], strict=[])),
    (
        "kirat-rai-herald",
        lambda: package_module.convert_kiratrai_herald([], strict=[]),
    ),
    ("sunuwar", lambda: package_module.convert_sunuwar([], strict=[])),
    (
        "tibetanmachine",
        lambda: package_module.convert_tibetanmachine([], strict=[]),
    ),
    ("lepcha", lambda: package_module.convert_lepcha([], strict=[])),
    ("jg-lepcha", lambda: package_module.convert_jg_lepcha([], strict=[])),
    ("ol-chiki", lambda: package_module.convert_olchiki([], strict=[])),
    (
        "ol-chiki-latic",
        lambda: package_module.convert_olchiki_latic([], strict=[]),
    ),
    ("tirhuta", lambda: package_module.convert_tirhuta([], strict=[])),
    (
        "magar-akkha",
        lambda: package_module.transliterate_magar_akkha([], strict=[]),
    ),
)

_SELECTOR_TYPE_SURFACES = (
    (
        "dispatcher-font",
        "font",
        lambda selector: package_module.convert("", font=selector),
    ),
    (
        "devanagari-font",
        "font",
        lambda selector: package_module.convert_devanagari("", font=selector),
    ),
    (
        "unicode-script",
        "script",
        lambda selector: package_module.validate_unicode_span("", script=selector),
    ),
)


def test_version_matches_release():
    assert __version__ == "0.3.0"


@pytest.fixture(scope="module")
def public_converter_methods():
    converters = (
        ("limbu", package_module.LimbuConverter.default()),
        ("kirat-rai", package_module.KiratRaiConverter.default()),
        ("kirat-rai-herald", package_module.KiratRaiHeraldConverter.default()),
        ("sunuwar", package_module.SunuwarConverter()),
        ("tibetanmachine", package_module.TibetanMachineConverter.default()),
        ("lepcha", package_module.LepchaConverter.default()),
        ("jg-lepcha", package_module.JGLepchaConverter.default()),
        ("ol-chiki", package_module.OLChikiConverter.default()),
        ("ol-chiki-latic", package_module.OLChikiLaticConverter.default()),
        ("tirhuta", package_module.TirhutaConverter()),
    )
    return tuple((surface, converter.convert) for surface, converter in converters)


@pytest.mark.parametrize(("surface", "name", "call"), _SELECTOR_TYPE_SURFACES)
@pytest.mark.parametrize(("value_name", "factory"), _INVALID_SELECTOR_FACTORIES)
def test_general_conversion_selectors_require_exact_builtin_strings(
    surface,
    name,
    call,
    value_name,
    factory,
):
    with pytest.raises(TypeError, match=rf"^{name} must be a string$"):
        call(factory())


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (
            lambda: package_module.convert("", font=[], strict=[]),
            "strict must be a bool",
        ),
        (
            lambda: package_module.convert_devanagari("", font=[], strict=[]),
            "strict must be a bool",
        ),
        (
            lambda: package_module.convert_devanagari("", font=[], normalize_glottal_stop=[]),
            "Devanagari normalize_glottal_stop must be a bool",
        ),
        (
            lambda: package_module.validate_unicode_span("", script=[], strict=[]),
            "strict must be a bool",
        ),
    ],
)
def test_boolean_validation_retains_precedence_over_selector_validation(call, message):
    with pytest.raises(ValueError, match=rf"^{message}$"):
        call()


def test_every_builtin_font_alias_retains_all_normalized_selector_variants():
    for alias in supported_fonts():
        assert type(alias) is str
        assert alias.isascii()
        variants = {
            alias,
            alias.upper(),
            f"\t{alias}\r\n",
            alias.replace("-", "_"),
            f"ABCDEF+{alias}",
        }
        for variant in variants:
            assert package_module._normalize_font_key(variant) == alias
            assert convert("", font=variant) == ""


def test_direct_devanagari_fonts_retain_case_and_outer_whitespace_normalization():
    for font in package_module.supported_devanagari_fonts():
        assert type(font) is str
        for variant in {font, font.upper(), f"\t{font}\r\n"}:
            result = package_module.convert_devanagari("", font=variant)
            assert result.legacy_text == ""
            assert result.unicode_text == ""


@pytest.mark.parametrize(("surface", "call"), _TEXT_PUBLIC_SURFACES)
@pytest.mark.parametrize(("value_name", "factory"), _INVALID_TEXT_FACTORIES)
def test_every_public_text_surface_requires_an_exact_builtin_string(
    surface,
    call,
    value_name,
    factory,
):
    with pytest.raises(TypeError, match=r"^text must be a string$"):
        call(factory())


@pytest.mark.parametrize(("value_name", "factory"), _INVALID_TEXT_FACTORIES)
def test_dispatcher_rejects_invalid_text_before_every_route(value_name, factory):
    for font in supported_fonts():
        with pytest.raises(TypeError, match=r"^text must be a string$"):
            convert(factory(), font=font)


@pytest.mark.parametrize(("value_name", "factory"), _INVALID_TEXT_FACTORIES)
def test_every_exported_converter_method_requires_an_exact_builtin_string(
    public_converter_methods,
    value_name,
    factory,
):
    for _surface, call in public_converter_methods:
        with pytest.raises(TypeError, match=r"^text must be a string$"):
            call(factory())


@pytest.mark.parametrize(("surface", "call"), _TEXT_STRICT_PRECEDENCE_SURFACES)
def test_invalid_strict_retains_precedence_over_invalid_text(surface, call):
    with pytest.raises(ValueError, match=r"^strict must be a bool$"):
        call()


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (
            lambda: package_module.convert_devanagari([], normalize_glottal_stop=[]),
            "Devanagari normalize_glottal_stop",
        ),
        (
            lambda: package_module.convert_sunuwar([], apply_uncertain=[]),
            "Sunuwar apply_uncertain",
        ),
        (
            lambda: package_module.convert_olchiki([], apply_uncertain=[]),
            "Ol Chiki apply_uncertain",
        ),
        (
            lambda: package_module.convert_olchiki_latic([], apply_uncertain=[]),
            "Ol Chiki apply_uncertain",
        ),
        (
            lambda: package_module.transliterate_magar_akkha([], fold_to_minimal_inventory=[]),
            "Magar Akkha fold_to_minimal_inventory",
        ),
    ],
)
def test_invalid_format_boolean_retains_precedence_over_invalid_text(call, message):
    with pytest.raises(ValueError, match=message):
        call()


@pytest.mark.parametrize(
    "call",
    [
        lambda: package_module.convert([], font=object()),
        lambda: package_module.convert_devanagari([], font=object()),
        lambda: package_module.validate_unicode_span([], script=object()),
        lambda: package_module.transliterate_magar_akkha([], target=object()),
    ],
)
def test_invalid_text_precedes_format_selector_validation(call):
    with pytest.raises(TypeError, match=r"^text must be a string$"):
        call()


@pytest.mark.parametrize(("surface", "call"), _STRICT_PUBLIC_SURFACES)
@pytest.mark.parametrize("strict", _INVALID_BOOLEAN_VALUES)
def test_every_public_strict_surface_requires_an_exact_boolean(surface, call, strict):
    with pytest.raises(ValueError, match=r"^strict must be a bool$"):
        call(strict)


@pytest.mark.parametrize(("surface", "call"), _STRICT_PUBLIC_SURFACES)
@pytest.mark.parametrize("strict", [False, True])
def test_every_public_strict_surface_accepts_builtin_booleans(surface, call, strict):
    call(strict)


@pytest.mark.parametrize(("surface", "call"), _STRICT_DIAGNOSTIC_SURFACES)
def test_exact_booleans_retain_lenient_and_strict_semantics(surface, call):
    call(False)
    with pytest.raises(ValueError) as error:
        call(True)
    assert "must be a bool" not in str(error.value)


@pytest.mark.parametrize("strict", _INVALID_BOOLEAN_VALUES)
def test_dispatcher_rejects_invalid_strict_before_every_route(strict):
    for font in supported_fonts():
        with pytest.raises(ValueError, match=r"^strict must be a bool$"):
            convert("", font=font, strict=strict)


def test_dispatcher_validates_strict_before_font_normalization(monkeypatch):
    def unexpected_normalization(_font):
        raise AssertionError("font normalization ran before strict validation")

    monkeypatch.setattr(package_module, "_normalize_font_key", unexpected_normalization)
    with pytest.raises(ValueError, match=r"^strict must be a bool$"):
        convert("", font="preeti", strict=[])


@pytest.mark.parametrize("normalize_glottal_stop", _INVALID_BOOLEAN_VALUES)
def test_devanagari_glottal_stop_option_requires_an_exact_boolean(
    normalize_glottal_stop,
):
    with pytest.raises(
        ValueError,
        match=r"^Devanagari normalize_glottal_stop must be a bool$",
    ):
        convert_devanagari("", normalize_glottal_stop=normalize_glottal_stop)


def test_devanagari_glottal_stop_option_retains_exact_boolean_behavior():
    assert convert_devanagari("ʻ").unicode_text == "ʻ"
    assert convert_devanagari("ʻ", normalize_glottal_stop=False).unicode_text == "ʻ"
    assert convert_devanagari("ʻ", normalize_glottal_stop=True).unicode_text == "ॽ"


def test_devanagari_boolean_options_validate_in_signature_order():
    with pytest.raises(ValueError, match=r"^strict must be a bool$"):
        convert_devanagari("", strict=[], normalize_glottal_stop=[])
    with pytest.raises(
        ValueError,
        match=r"^Devanagari normalize_glottal_stop must be a bool$",
    ):
        convert_devanagari("", strict=False, normalize_glottal_stop=[])


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (
            lambda: package_module.convert_sunuwar("", apply_uncertain=[], strict=[]),
            "Sunuwar apply_uncertain",
        ),
        (
            lambda: package_module.convert_olchiki("", apply_uncertain=[], strict=[]),
            "Ol Chiki apply_uncertain",
        ),
        (
            lambda: package_module.convert_olchiki_latic("", apply_uncertain=[], strict=[]),
            "Ol Chiki apply_uncertain",
        ),
        (
            lambda: package_module.transliterate_magar_akkha(
                "", fold_to_minimal_inventory=[], strict=[]
            ),
            "Magar Akkha fold_to_minimal_inventory",
        ),
    ],
)
def test_multi_boolean_apis_preserve_option_precedence(call, message):
    with pytest.raises(ValueError, match=message):
        call()


def test_direct_converter_validates_strict_before_default_resource_loading(monkeypatch):
    monkeypatch.setattr(lepcha_module, "_DEFAULT", None)

    def unexpected_default():
        raise AssertionError("default resource loaded before strict validation")

    monkeypatch.setattr(
        lepcha_module.LepchaConverter,
        "default",
        staticmethod(unexpected_default),
    )
    with pytest.raises(ValueError, match=r"^strict must be a bool$"):
        lepcha_module.convert_lepcha("", strict=[])


def test_direct_converter_validates_text_before_default_resource_loading(monkeypatch):
    monkeypatch.setattr(lepcha_module, "_DEFAULT", None)

    def unexpected_default():
        raise AssertionError("default resource loaded before text validation")

    monkeypatch.setattr(
        lepcha_module.LepchaConverter,
        "default",
        staticmethod(unexpected_default),
    )
    with pytest.raises(TypeError, match=r"^text must be a string$"):
        lepcha_module.convert_lepcha([])


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
