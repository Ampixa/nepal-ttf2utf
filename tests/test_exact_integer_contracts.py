"""Cross-family exact-integer contracts for public custom converters."""

from collections.abc import Mapping

import pytest

import nepal_ttf2utf.limbu as limbu_module
from nepal_ttf2utf import (
    JGLepchaConverter,
    KiratRaiConverter,
    LepchaConverter,
    LimbuConverter,
    OLChikiConverter,
    OLChikiLaticConverter,
    TibetanMachineConverter,
)


class _SingleItemMapping(Mapping):
    """Yield a source scalar without hashing it before converter validation."""

    def __init__(self, source, target):
        self._item = (source, target)

    def __getitem__(self, key):
        raise KeyError(key)

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 1

    def items(self):
        return iter((self._item,))


class _HostileInt(int):
    def _explode(self, *args, **kwargs):
        raise AssertionError("integer validation invoked a subclass hook")

    __bool__ = _explode
    __eq__ = _explode
    __format__ = _explode
    __ge__ = _explode
    __gt__ = _explode
    __hash__ = _explode
    __index__ = _explode
    __int__ = _explode
    __le__ = _explode
    __lt__ = _explode
    __ne__ = _explode
    __repr__ = _explode


class _IntSubclass(int):
    pass


class _NumericProxy:
    def __index__(self):
        raise AssertionError("integer validation invoked numeric indexing")

    def __int__(self):
        raise AssertionError("integer validation invoked numeric coercion")

    def __repr__(self):
        raise AssertionError("integer validation represented a numeric proxy")


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        pytest.param(
            lambda: KiratRaiConverter([((_HostileInt(0x100),), (0x16D43,))]),
            r"^invalid Kirat Rai source byte must be an int$",
            id="kirat-source",
        ),
        pytest.param(
            lambda: KiratRaiConverter([((0x41,), (_HostileInt(0x110000),))]),
            r"^invalid Unicode scalar in Kirat Rai map must be an int$",
            id="kirat-target",
        ),
        pytest.param(
            lambda: LimbuConverter([((_HostileInt(0x41),), (0x1901,))]),
            r"^invalid Limbu source byte must be an int$",
            id="limbu-source",
        ),
        pytest.param(
            lambda: LimbuConverter([((0x41,), (_HostileInt(0x1901),))]),
            r"^invalid Unicode scalar in Limbu map must be an int$",
            id="limbu-target",
        ),
        pytest.param(
            lambda: JGLepchaConverter([((_HostileInt(0x41),), (0x1C00,))], [], {}, None),
            r"^invalid JG Lepcha source byte must be an int$",
            id="jg-byte-source",
        ),
        pytest.param(
            lambda: JGLepchaConverter([((0x41,), (_HostileInt(0x1C00),))], [], {}, None),
            r"^invalid Unicode scalar in JG Lepcha map must be an int$",
            id="jg-byte-target",
        ),
        pytest.param(
            lambda: JGLepchaConverter(
                [((0x41,), (0x1C00,))], [], {"Cons": (_HostileInt(0x1C00),)}, None
            ),
            r"^invalid Unicode scalar in JG Lepcha map must be an int$",
            id="jg-class-member",
        ),
        pytest.param(
            lambda: JGLepchaConverter(
                [((0x3C,), (0x25CC,))],
                [],
                {},
                None,
                (_HostileInt(0x3C),),
            ),
            r"^invalid JG Lepcha uncertain source byte must be an int$",
            id="jg-uncertain-source",
        ),
        pytest.param(
            lambda: JGLepchaConverter(
                [((0x41,), (0x1C00,))],
                [],
                {},
                (_HostileInt(0x41), (0x42,), 0x1C01),
            ),
            r"^invalid JG Lepcha context trigger byte must be an int$",
            id="jg-context-trigger",
        ),
        pytest.param(
            lambda: JGLepchaConverter(
                [((0x41,), (0x1C00,))],
                [],
                {},
                (0x41, (_HostileInt(0x42),), 0x1C01),
            ),
            r"^invalid JG Lepcha context class byte must be an int$",
            id="jg-context-class",
        ),
        pytest.param(
            lambda: JGLepchaConverter(
                [((0x41,), (0x1C00,))],
                [],
                {},
                (0x41, (0x42,), _HostileInt(0x1C01)),
            ),
            r"^invalid Unicode scalar in JG Lepcha map must be an int$",
            id="jg-context-target",
        ),
        pytest.param(
            lambda: LepchaConverter(_SingleItemMapping(_HostileInt(0x41), (0x1C00,))),
            r"^invalid Lepcha source byte must be an int$",
            id="lepcha-source",
        ),
        pytest.param(
            lambda: LepchaConverter({0x41: (_HostileInt(0x1C00),)}),
            r"^invalid or unassigned Lepcha target for source 0x41 must be an int$",
            id="lepcha-target",
        ),
        pytest.param(
            lambda: OLChikiConverter(_SingleItemMapping(_HostileInt(0x61), 0x1C5F)),
            r"^invalid Ol Chiki confirmed map source must be an int$",
            id="olchiki-confirmed-source",
        ),
        pytest.param(
            lambda: OLChikiConverter({0x61: _HostileInt(0x1C5F)}),
            r"^invalid or unassigned Ol Chiki confirmed map target for source 0x61 must be an int$",
            id="olchiki-confirmed-target",
        ),
        pytest.param(
            lambda: OLChikiConverter({0x61: 0x1C5F}, _SingleItemMapping(_HostileInt(0x62), 0x1C60)),
            r"^invalid Ol Chiki uncertain map source must be an int$",
            id="olchiki-uncertain-source",
        ),
        pytest.param(
            lambda: OLChikiConverter({0x61: 0x1C5F}, {0x62: _HostileInt(0x1C60)}),
            r"^invalid or unassigned Ol Chiki uncertain map target for source 0x62 must be an int$",
            id="olchiki-uncertain-target",
        ),
        pytest.param(
            lambda: OLChikiLaticConverter(_SingleItemMapping(_HostileInt(0x61), 0x1C5F)),
            r"^invalid Ol Chiki confirmed map source must be an int$",
            id="latic-confirmed-source",
        ),
        pytest.param(
            lambda: OLChikiLaticConverter({0x61: _HostileInt(0x1C5F)}),
            r"^invalid or unassigned Ol Chiki confirmed map target for source 0x61 must be an int$",
            id="latic-confirmed-target",
        ),
        pytest.param(
            lambda: OLChikiLaticConverter(
                {0x61: 0x1C5F}, _SingleItemMapping(_HostileInt(0x62), 0x1C60)
            ),
            r"^invalid Ol Chiki uncertain map source must be an int$",
            id="latic-uncertain-source",
        ),
        pytest.param(
            lambda: OLChikiLaticConverter({0x61: 0x1C5F}, {0x62: _HostileInt(0x1C60)}),
            r"^invalid or unassigned Ol Chiki uncertain map target for source 0x62 must be an int$",
            id="latic-uncertain-target",
        ),
        pytest.param(
            lambda: TibetanMachineConverter(_SingleItemMapping(_HostileInt(0x21), "ཀ")),
            r"^invalid TibetanMachine source must be an int$",
            id="tibetan-source",
        ),
    ],
)
def test_custom_converters_reject_integer_subclasses_before_hooks(factory, message):
    with pytest.raises(ValueError, match=message):
        factory()


def test_custom_converters_do_not_coerce_numeric_proxies():
    with pytest.raises(ValueError, match=r"^invalid Kirat Rai source byte must be an int$"):
        KiratRaiConverter([((_NumericProxy(),), (0x16D43,))])


@pytest.mark.parametrize("field", ["vowels", "subjoined", "kemphreng"])
def test_limbu_private_reorder_scalars_are_exact_integers(field):
    default = limbu_module._DEFAULT_REORDER_CONTRACT
    vowels = default.vowels
    subjoined = default.subjoined
    kemphreng = default.kemphreng
    if field == "vowels":
        vowels = frozenset(
            _IntSubclass(value) if value == min(default.vowels) else value
            for value in default.vowels
        )
    elif field == "subjoined":
        subjoined = frozenset(
            _IntSubclass(value) if value == min(default.subjoined) else value
            for value in default.subjoined
        )
    else:
        kemphreng = _IntSubclass(kemphreng)
    contract = limbu_module._LimbuReorderContract(
        vowels=vowels,
        subjoined=subjoined,
        kemphreng=kemphreng,
        provenance=default.provenance,
    )
    with pytest.raises(ValueError, match=r"^invalid Limbu reorder contract$"):
        LimbuConverter([((0x41,), (0x1901,))], _reorder_contract=contract)


def test_parser_backed_custom_contract_snapshots_contain_only_exact_integers():
    kirat = KiratRaiConverter.default()
    limbu = LimbuConverter.default()
    jg = JGLepchaConverter.default()
    lepcha = LepchaConverter.default()
    optimum = OLChikiConverter.default()
    latic = OLChikiLaticConverter.default()
    tibetan = TibetanMachineConverter.default()

    assert all(type(value) is int for rule in kirat._rules for side in rule for value in side)
    assert all(type(value) is int for rule in limbu._rules for side in rule for value in side)
    assert all(type(value) is int for value in limbu._contract.reorder.vowels)
    assert all(type(value) is int for value in limbu._contract.reorder.subjoined)
    assert type(limbu._contract.reorder.kemphreng) is int
    assert all(type(value) is int for rule in jg._byte_rules for side in rule for value in side)
    assert all(type(value) is int for members in jg._unicode_classes.values() for value in members)
    assert all(type(value) is int for value in jg._uncertain_source_codepoints)
    assert jg._context_rule is not None
    assert type(jg._context_rule[0]) is int
    assert all(type(value) is int for value in jg._context_rule[1])
    assert type(jg._context_rule[2]) is int
    assert all(
        type(value) is int
        for source, target in lepcha._byte_map.items()
        for value in (source, *target)
    )
    for converter in (optimum, latic):
        assert all(
            type(value) is int
            for table in (converter._confirmed, converter._uncertain)
            for entry in table.items()
            for value in entry
        )
    assert all(type(source) is int for source in tibetan._table)
