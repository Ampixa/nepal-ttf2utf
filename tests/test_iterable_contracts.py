"""Cross-family protocol-failure contracts for caller-owned containers."""

from collections.abc import Mapping

import pytest

from nepal_ttf2utf import (
    JGLepchaConverter,
    KiratRaiConverter,
    LepchaConverter,
    LimbuConverter,
    OLChikiConverter,
    OLChikiLaticConverter,
    TibetanMachineConverter,
)
from nepal_ttf2utf.jg_lepcha import _ReorderRule


class _IterBomb:
    def __init__(self, error: BaseException):
        self.error = error

    def __iter__(self):
        raise self.error


class _NextBomb:
    def __init__(self, error: BaseException):
        self.error = error

    def __iter__(self):
        return self

    def __next__(self):
        raise self.error


class _PairBomb(_IterBomb):
    def __repr__(self):
        raise AssertionError("container validation represented a malformed pair")


class _HostilePair:
    def __init__(self, parts):
        self.parts = parts

    def __iter__(self):
        return iter(self.parts)

    def __repr__(self):
        raise AssertionError("container validation represented an invalid pair")


class _ItemsMapping(Mapping):
    def __init__(self, items):
        self._items = items

    def __getitem__(self, key):
        raise KeyError(key)

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 1

    def items(self):
        if isinstance(self._items, BaseException):
            raise self._items
        return self._items


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        pytest.param(
            lambda error: KiratRaiConverter(_IterBomb(error)),
            "invalid Kirat Rai byte-rule sequence",
            id="kirat-iter",
        ),
        pytest.param(
            lambda error: LimbuConverter(_NextBomb(error)),
            "invalid Limbu byte-rule sequence",
            id="limbu-next",
        ),
        pytest.param(
            lambda error: JGLepchaConverter([((0x41,), (0x1C00,))], [], _ItemsMapping(error), None),
            "invalid JG Lepcha Unicode class sequence",
            id="jg-items",
        ),
        pytest.param(
            lambda error: LepchaConverter(_ItemsMapping(_IterBomb(error))),
            "invalid Lepcha source map item sequence",
            id="herald-items-iter",
        ),
        pytest.param(
            lambda error: OLChikiConverter(_ItemsMapping(_NextBomb(error))),
            "invalid Ol Chiki confirmed map item sequence",
            id="olchiki-items-next",
        ),
        pytest.param(
            lambda error: TibetanMachineConverter(_ItemsMapping(error)),
            "invalid TibetanMachine table item sequence",
            id="tibetan-items",
        ),
    ],
)
def test_custom_container_protocol_failures_are_contextual(factory, message):
    sentinel = RuntimeError("caller protocol failed")
    with pytest.raises(ValueError, match=f"^{message}$") as caught:
        factory(sentinel)
    assert caught.value.__cause__ is sentinel


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        pytest.param(
            lambda pair: KiratRaiConverter([pair]),
            "invalid Kirat Rai byte rule",
            id="kirat",
        ),
        pytest.param(
            lambda pair: LimbuConverter([pair]),
            "invalid Limbu byte rule",
            id="limbu",
        ),
        pytest.param(
            lambda pair: JGLepchaConverter([pair], [], {}, None),
            "invalid JG Lepcha byte rule",
            id="jg",
        ),
        pytest.param(
            lambda pair: LepchaConverter(_ItemsMapping(iter((pair,)))),
            "invalid Lepcha source map entry",
            id="herald",
        ),
        pytest.param(
            lambda pair: OLChikiConverter(_ItemsMapping(iter((pair,)))),
            "invalid Ol Chiki confirmed map entry",
            id="olchiki",
        ),
        pytest.param(
            lambda pair: TibetanMachineConverter(_ItemsMapping(iter((pair,)))),
            "invalid TibetanMachine table entry",
            id="tibetan",
        ),
    ],
)
def test_malformed_pairs_fail_without_representation(factory, message):
    sentinel = RuntimeError("pair iteration failed")
    with pytest.raises(ValueError, match=f"^{message}$") as caught:
        factory(_PairBomb(sentinel))
    assert caught.value.__cause__ is sentinel


def test_jg_reorder_slot_protocol_failure_is_contextual():
    sentinel = RuntimeError("slot iteration failed")
    rule = _ReorderRule((_PairBomb(sentinel),), ("c",))
    with pytest.raises(ValueError, match="^invalid JG Lepcha reorder slot$") as caught:
        JGLepchaConverter(
            [((0x41,), (0x1C00,))],
            [rule],
            {"Cons": (0x1C00,)},
            None,
        )
    assert caught.value.__cause__ is sentinel


def test_jg_semantically_invalid_reorder_slot_is_not_represented():
    rule = _ReorderRule((_HostilePair(("bad!", "v")),), ("v",))
    with pytest.raises(ValueError, match="^invalid JG Lepcha reorder slot$"):
        JGLepchaConverter(
            [((0x41,), (0x1C00,))],
            [rule],
            {"Cons": (0x1C00,)},
            None,
        )


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        pytest.param(
            lambda error: LepchaConverter(_ItemsMapping(iter(((0x41, _IterBomb(error)),)))),
            "invalid Lepcha target sequence for source 0x41",
            id="herald-target",
        ),
        pytest.param(
            lambda error: JGLepchaConverter(
                [((0x41,), (0x1C00,))], [], {}, (0x41, _NextBomb(error), 0x1C01)
            ),
            "invalid JG Lepcha context exclusion class",
            id="jg-context",
        ),
        pytest.param(
            lambda error: OLChikiConverter({0x61: 0x1C5F}, passthrough=_NextBomb(error)),
            "invalid Ol Chiki passthrough sequence",
            id="olchiki-passthrough",
        ),
    ],
)
def test_nested_container_protocol_failures_are_contextual(factory, message):
    sentinel = RuntimeError("nested protocol failed")
    with pytest.raises(ValueError, match=f"^{message}$") as caught:
        factory(sentinel)
    assert caught.value.__cause__ is sentinel


@pytest.mark.parametrize(
    "error_type",
    [AssertionError, LookupError, NotImplementedError, OSError, StopAsyncIteration],
)
def test_ordinary_exceptions_share_the_validation_boundary(error_type):
    sentinel = error_type("ordinary caller failure")
    with pytest.raises(ValueError, match="^invalid Kirat Rai byte-rule sequence$") as caught:
        KiratRaiConverter(_NextBomb(sentinel))
    assert caught.value.__cause__ is sentinel


@pytest.mark.parametrize("error_type", [MemoryError, RecursionError])
@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(lambda error: KiratRaiConverter(_NextBomb(error)), id="kirat"),
        pytest.param(lambda error: LimbuConverter(_NextBomb(error)), id="limbu"),
        pytest.param(lambda error: JGLepchaConverter(_NextBomb(error), [], {}, None), id="jg"),
        pytest.param(
            lambda error: LepchaConverter(_ItemsMapping(iter(((0x41, _NextBomb(error)),)))),
            id="herald",
        ),
        pytest.param(
            lambda error: OLChikiConverter({0x61: 0x1C5F}, passthrough=_NextBomb(error)),
            id="olchiki",
        ),
        pytest.param(lambda error: TibetanMachineConverter(_ItemsMapping(error)), id="tibetan"),
    ],
)
def test_critical_exceptions_propagate_unchanged(factory, error_type):
    sentinel = error_type("critical caller failure")
    with pytest.raises(error_type) as caught:
        factory(sentinel)
    assert caught.value is sentinel


@pytest.mark.parametrize("error_type", [MemoryError, RecursionError])
@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(
            lambda error: JGLepchaConverter([((0x41,), (0x1C00,))], [], _ItemsMapping(error), None),
            id="jg-items",
        ),
        pytest.param(lambda error: LepchaConverter(_ItemsMapping(error)), id="herald-items"),
        pytest.param(
            lambda error: LepchaConverter(_ItemsMapping(iter((_PairBomb(error),)))),
            id="herald-pair",
        ),
        pytest.param(lambda error: OLChikiConverter(_ItemsMapping(error)), id="olchiki-items"),
    ],
)
def test_critical_exceptions_cross_separate_mapping_boundaries(factory, error_type):
    sentinel = error_type("critical mapping failure")
    with pytest.raises(error_type) as caught:
        factory(sentinel)
    assert caught.value is sentinel


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit, GeneratorExit])
def test_process_control_exceptions_propagate_unchanged(error_type):
    sentinel = error_type("process control")
    with pytest.raises(error_type) as caught:
        KiratRaiConverter(_NextBomb(sentinel))
    assert caught.value is sentinel


def test_one_shot_contracts_keep_cross_family_anchor_output():
    kirat = KiratRaiConverter(((iter((0x41,)), iter((0x16D43,))) for _ in range(1)))
    assert kirat.convert("A").unicode_text == "\U00016d43"

    limbu = LimbuConverter(((iter((0x41,)), iter((0x1901,))) for _ in range(1)))
    assert limbu.convert("A").unicode_text == "\u1901"

    jg = JGLepchaConverter(
        ((iter((0x41,)), iter((0x1C00,))) for _ in range(1)),
        iter(()),
        _ItemsMapping(iter(())),
        None,
        iter(()),
    )
    assert jg.convert("A").unicode_text == "\u1c00"

    herald = LepchaConverter(_ItemsMapping(iter(((0x41, iter((0x1C00,))),))))
    assert herald.convert("A").unicode_text == "\u1c00"

    optimum = OLChikiConverter(_ItemsMapping(iter(((0x61, 0x1C5F),))), passthrough=iter(("!",)))
    assert optimum.convert("a").unicode_text == "\u1c5f"

    latic = OLChikiLaticConverter(_ItemsMapping(iter(((0x61, 0x1C5F),))))
    assert latic.convert("a").unicode_text == "\u1c5f"

    tibetan = TibetanMachineConverter(_ItemsMapping(iter(((0x21, "\u0f40"),))))
    assert tibetan.convert("!").unicode_text == "\u0f40"
