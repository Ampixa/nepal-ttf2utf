"""Cross-family exact-string contracts for caller-supplied converter state."""

from collections.abc import Mapping

import pytest

import nepal_ttf2utf.limbu as limbu_module
from nepal_ttf2utf import JGLepchaConverter, LimbuConverter, OLChikiConverter
from nepal_ttf2utf.jg_lepcha import _ReorderRule


class _SingleItemMapping(Mapping):
    """Yield a key without hashing it before converter validation."""

    def __init__(self, key, value):
        self._item = (key, value)

    def __getitem__(self, key):
        raise KeyError(key)

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 1

    def items(self):
        return iter((self._item,))


class _HostileString(str):
    def _explode(self, *args, **kwargs):
        raise AssertionError("string validation invoked a subclass hook")

    __contains__ = _explode
    __eq__ = _explode
    __format__ = _explode
    __getitem__ = _explode
    __hash__ = _explode
    __iter__ = _explode
    __len__ = _explode
    __ne__ = _explode
    __repr__ = _explode
    isspace = _explode


class _StringProxy:
    def __repr__(self):
        raise AssertionError("string validation represented a proxy")

    def __str__(self):
        raise AssertionError("string validation coerced a proxy")


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        pytest.param(
            lambda: JGLepchaConverter(
                [((0x41,), (0x1C00,))],
                [],
                _SingleItemMapping(_HostileString("Cons"), (0x1C00,)),
                None,
            ),
            r"^invalid JG Lepcha Unicode class name$",
            id="jg-class-name",
        ),
        pytest.param(
            lambda: JGLepchaConverter(
                [((0x41,), (0x1C00,))],
                [_ReorderRule(((_HostileString("Cons"), "c"),), ("c",))],
                {"Cons": (0x1C00,)},
                None,
            ),
            r"^invalid JG Lepcha reorder slot$",
            id="jg-slot-class",
        ),
        pytest.param(
            lambda: JGLepchaConverter(
                [((0x41,), (0x1C00,))],
                [_ReorderRule((("Cons", _HostileString("c")),), ("c",))],
                {"Cons": (0x1C00,)},
                None,
            ),
            r"^invalid JG Lepcha reorder slot$",
            id="jg-slot-variable",
        ),
        pytest.param(
            lambda: JGLepchaConverter(
                [((0x41,), (0x1C00,))],
                [_ReorderRule((("Cons", "c"),), (_HostileString("c"),))],
                {"Cons": (0x1C00,)},
                None,
            ),
            r"^invalid JG Lepcha reorder output$",
            id="jg-output-variable",
        ),
        pytest.param(
            lambda: OLChikiConverter({0x61: 0x1C5F}, passthrough=(_HostileString("!"),)),
            r"^invalid Ol Chiki passthrough character$",
            id="olchiki-passthrough",
        ),
        pytest.param(
            lambda: LimbuConverter(
                [((0x41,), (0x1901,))],
                _reorder_contract=limbu_module._LimbuReorderContract(
                    vowels=limbu_module._DEFAULT_REORDER_CONTRACT.vowels,
                    subjoined=limbu_module._DEFAULT_REORDER_CONTRACT.subjoined,
                    kemphreng=limbu_module._DEFAULT_REORDER_CONTRACT.kemphreng,
                    provenance=_HostileString("legacy-byte-derived-only"),
                ),
            ),
            r"^invalid Limbu reorder contract$",
            id="limbu-private-provenance",
        ),
    ],
)
def test_custom_contracts_reject_string_subclasses_before_hooks(factory, message):
    with pytest.raises(ValueError, match=message):
        factory()


def test_custom_contracts_do_not_coerce_string_proxies():
    with pytest.raises(ValueError, match=r"^invalid Ol Chiki passthrough character$"):
        OLChikiConverter({0x61: 0x1C5F}, passthrough=(_StringProxy(),))


def test_exact_built_in_custom_strings_remain_accepted():
    jg = JGLepchaConverter(
        [((0x41,), (0x1C00,))],
        [_ReorderRule((("Cons", "c"),), ("c",))],
        {"Cons": (0x1C00,)},
        None,
    )
    optimum = OLChikiConverter({0x61: 0x1C5F}, passthrough=("!",))

    assert jg.convert("A").unicode_text == "ᰀ"
    assert optimum.convert("a!").unicode_text == "ᱟ!"


def test_default_string_snapshots_contain_only_exact_strings():
    jg = JGLepchaConverter.default()
    optimum = OLChikiConverter.default()
    limbu = LimbuConverter.default()

    assert all(type(name) is str for name in jg._unicode_classes)
    assert all(
        type(value) is str for rule in jg._reorder_rules for slot in rule.slots for value in slot
    )
    assert all(type(variable) is str for rule in jg._reorder_rules for variable in rule.output_vars)
    assert all(type(member) is str for member in optimum._passthrough)
    assert type(limbu._contract.reorder.provenance) is str
