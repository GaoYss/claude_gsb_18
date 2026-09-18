"""作业标准与工时/材料偏差判定。

规则以后端实现为唯一权威，前端仅做录入时的即时提示：

- 工时偏差：实际工时落在标准值 ±30% 区间外，且与标准值的差值超过 0.5 小时
  （绝对容差优先，避免标准工时较小时边界抖动误报）；工时未填或无标准时不判定。
- 材料偏差：实际填写了材料，但不包含该任务类型任一常用材料关键词（子串匹配）。
"""

from ..constants import TASK_STANDARDS

WORK_HOURS_TOLERANCE_RATIO = 0.30
WORK_HOURS_ABS_TOLERANCE = 0.5

FLAG_WORK_HOURS = "work_hours"
FLAG_MATERIALS = "materials"


def get_standard(task_type):
    """返回某任务类型的作业标准字典；未配置标准时返回 None。"""

    if not task_type:
        return None
    return TASK_STANDARDS.get(task_type)


def hours_range(standard_hours):
    """标准工时的合理区间（±30%），返回 (下限, 上限)。"""

    std = float(standard_hours)
    return round(std * (1 - WORK_HOURS_TOLERANCE_RATIO), 2), round(
        std * (1 + WORK_HOURS_TOLERANCE_RATIO), 2
    )


def is_work_hours_deviation(actual_hours, standard_hours):
    """实际工时是否偏离标准：超出 ±30% 区间且差值超过绝对容差。"""

    if actual_hours is None or standard_hours is None:
        return False
    actual = float(actual_hours)
    std = float(standard_hours)
    if abs(actual - std) <= WORK_HOURS_ABS_TOLERANCE:
        return False
    lower, upper = hours_range(std)
    return actual < lower or actual > upper


def is_materials_deviation(materials, keywords):
    """实际材料是否偏离常用材料：填了内容但不包含任一关键词。"""

    if not materials or not str(materials).strip():
        return False
    if not keywords:
        return False
    text = str(materials)
    return not any(keyword in text for keyword in keywords)


def evaluate_deviation(task_type, work_hours, materials):
    """综合判定工时与材料偏差，供入库重算、序列化与看板复用。"""

    standard = get_standard(task_type)
    standard_hours = standard["standard_hours"] if standard else None
    lower, upper = hours_range(standard_hours) if standard_hours else (None, None)

    hours_deviation = is_work_hours_deviation(work_hours, standard_hours)
    material_deviation = (
        is_materials_deviation(materials, standard.get("materials_keywords", []))
        if standard
        else False
    )

    flags = []
    if hours_deviation:
        flags.append(FLAG_WORK_HOURS)
    if material_deviation:
        flags.append(FLAG_MATERIALS)

    return {
        "task_type": task_type,
        "standard_hours": standard_hours,
        "hours_lower": lower,
        "hours_upper": upper,
        "work_hours_deviation": hours_deviation,
        "materials_deviation": material_deviation,
        "deviated": bool(flags),
        "flags": flags,
    }


def task_standards_payload():
    """展开作业标准供 /meta/enums 一并下发给前端。"""

    payload = {}
    for task_type, standard in TASK_STANDARDS.items():
        if standard is None:
            payload[task_type] = None
            continue
        payload[task_type] = {
            "standard_hours": standard["standard_hours"],
            "hours_tolerance_ratio": WORK_HOURS_TOLERANCE_RATIO,
            "hours_abs_tolerance": WORK_HOURS_ABS_TOLERANCE,
            "materials_keywords": list(standard.get("materials_keywords", [])),
            "materials_default": standard.get("materials_default", ""),
        }
    return payload
