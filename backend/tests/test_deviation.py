"""工时/材料偏差判定纯函数测试：覆盖 ±30% 区间与 0.5 小时绝对容差边界。"""

import pytest

from app.utils.deviation import (
    FLAG_MATERIALS,
    FLAG_WORK_HOURS,
    evaluate_deviation,
    is_materials_deviation,
    is_work_hours_deviation,
    task_standards_payload,
)


@pytest.mark.parametrize(
    "actual, expected",
    [
        (6.0, False),   # 恰好等于标准
        (5.5, False),   # 区间内且差值 0.5（含边界，容差优先）
        (6.5, False),
        (7.8, False),   # 区间上界（±30%）
        (4.2, False),   # 区间下界
        (7.9, True),    # 超出上界且差值 > 0.5
        (4.1, True),    # 低于下界且差值 > 0.5
        (12, True),
        (3, True),
        (None, False),  # 工时未填不判定
    ],
)
def test_work_hours_deviation_around_prune_standard(actual, expected):
    assert is_work_hours_deviation(actual, 6.0) is expected


def test_absolute_tolerance_takes_precedence_over_ratio():
    # 标准 1h，区间为 0.7~1.3；1.4 虽在区间外，但差值仅 0.4，在绝对容差内
    assert is_work_hours_deviation(1.4, 1.0) is False
    # 差值 0.6 超过绝对容差且在区间外
    assert is_work_hours_deviation(1.6, 1.0) is True
    # 无标准不判定
    assert is_work_hours_deviation(8.0, None) is False


@pytest.mark.parametrize(
    "materials, expected",
    [
        ("", False),
        ("   ", False),
        (None, False),
        ("复合肥 180kg", False),   # 命中关键词「肥」
        ("缓释肥 60 公斤", False),
        ("低毒药剂 12L", True),    # 施药材料对施肥类型判为偏差
        ("无", True),
        ("只做了现场登记，未领用任何东西", True),
    ],
)
def test_materials_deviation_keyword_match(materials, expected):
    keywords = task_standards_payload()["fertilize"]["materials_keywords"]
    assert is_materials_deviation(materials, keywords) is expected


def test_evaluate_deviation_flags_and_ranges():
    result = evaluate_deviation("prune", 12, "复合肥 180kg")
    assert result["standard_hours"] == 6.0
    assert result["hours_lower"] == 4.2
    assert result["hours_upper"] == 7.8
    assert result["work_hours_deviation"] is True
    assert result["materials_deviation"] is True
    assert result["flags"] == [FLAG_WORK_HOURS, FLAG_MATERIALS]
    assert result["deviated"] is True


def test_evaluate_deviation_clean_record():
    result = evaluate_deviation("fertilize", 5, "复合肥 180kg")
    assert result["flags"] == []
    assert result["deviated"] is False


def test_evaluate_deviation_without_standard():
    # other 类型无标准：任何工时与材料都不产生偏差
    result = evaluate_deviation("other", 20, "随便填的材料")
    assert result["standard_hours"] is None
    assert result["hours_lower"] is None
    assert result["deviated"] is False
    assert result["flags"] == []


def test_materials_keyword_for_pest_type():
    keywords = task_standards_payload()["pest"]["materials_keywords"]
    assert is_materials_deviation("黄板 60 张", keywords) is False
    assert is_materials_deviation("复合肥", keywords) is True


def test_task_standards_payload_covers_all_task_types():
    payload = task_standards_payload()
    assert set(payload) == {
        "prune", "water", "fertilize", "pest", "weed", "clean", "replant", "winter", "other",
    }
    prune = payload["prune"]
    assert prune["standard_hours"] == 6.0
    assert prune["hours_tolerance_ratio"] == 0.30
    assert prune["hours_abs_tolerance"] == 0.5
    assert "修枝剪" in prune["materials_keywords"]
    assert prune["materials_default"]
    assert payload["other"] is None
