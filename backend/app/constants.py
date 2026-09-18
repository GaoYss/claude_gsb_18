"""业务字典。

集中维护各模块的枚举选项：模型层用于入库校验与展示文案，
接口层通过 /api/v1/meta/enums 下发给前端，避免前后端重复定义。
"""


class EnumGroup:
    """一组枚举选项：value 入库，label 用于展示。"""

    def __init__(self, name, options):
        self.name = name
        self.options = [{"value": value, "label": label} for value, label in options]
        self._labels = {value: label for value, label in options}

    @property
    def values(self):
        return list(self._labels)

    def label(self, value):
        return self._labels.get(value, value)

    def has(self, value):
        return value in self._labels

    def default(self):
        return self.options[0]["value"]

    def __contains__(self, value):
        return value in self._labels


# ---------------------------------------------------------------- 绿地台账
GREEN_SPACE_TYPE = EnumGroup("green_space_type", [
    ("park", "公园绿地"),
    ("street", "街头游园"),
    ("road", "道路绿地"),
    ("residential", "居住区绿地"),
    ("attached", "单位附属绿地"),
    ("other", "其他绿地"),
])

MAINTENANCE_GRADE = EnumGroup("maintenance_grade", [
    ("level1", "一级养护"),
    ("level2", "二级养护"),
    ("level3", "三级养护"),
])

GREEN_SPACE_STATUS = EnumGroup("green_space_status", [
    ("normal", "正常养护"),
    ("repairing", "整治提升中"),
    ("suspended", "暂停养护"),
    ("archived", "已归档"),
])

# ---------------------------------------------------------------- 养护任务
TASK_TYPE = EnumGroup("task_type", [
    ("prune", "修剪整形"),
    ("water", "浇灌排涝"),
    ("fertilize", "施肥"),
    ("pest", "病虫害防治"),
    ("weed", "除草松土"),
    ("clean", "保洁清扫"),
    ("replant", "补植补种"),
    ("winter", "防寒防冻"),
    ("other", "其他养护"),
])

TASK_PRIORITY = EnumGroup("task_priority", [
    ("low", "低"),
    ("medium", "中"),
    ("high", "高"),
    ("urgent", "紧急"),
])

TASK_STATUS = EnumGroup("task_status", [
    ("pending", "待执行"),
    ("in_progress", "进行中"),
    ("completed", "已完成"),
    ("cancelled", "已取消"),
])

# ---------------------------------------------------------------- 养护记录
QUALITY_RESULT = EnumGroup("quality_result", [
    ("qualified", "合格"),
    ("pending", "待复检"),
    ("unqualified", "不合格"),
])

WEATHER = EnumGroup("weather", [
    ("sunny", "晴"),
    ("cloudy", "多云"),
    ("overcast", "阴"),
    ("rain", "雨"),
    ("snow", "雪"),
    ("windy", "大风"),
])

# 各任务类型的单次作业标准工时（小时）与常用材料/药剂；
# 养护记录录入时按任务类型带出，作为实际填报的对照基准。
TASK_TYPE_STANDARDS = {
    "prune": {"standard_work_hours": 6.0, "common_materials": ["支撑杆", "伤口涂补剂", "安全警示带"]},
    "water": {"standard_work_hours": 4.0, "common_materials": ["水管", "洒水车用水"]},
    "fertilize": {"standard_work_hours": 4.0, "common_materials": ["复合肥", "缓释肥", "有机肥"]},
    "pest": {"standard_work_hours": 5.0, "common_materials": ["低毒药剂", "黄板", "喷雾器用油"]},
    "weed": {"standard_work_hours": 4.0, "common_materials": ["除草剂", "垃圾袋"]},
    "clean": {"standard_work_hours": 3.0, "common_materials": ["垃圾袋", "清扫工具"]},
    "replant": {"standard_work_hours": 6.0, "common_materials": ["苗木", "种植土", "支撑杆"]},
    "winter": {"standard_work_hours": 5.0, "common_materials": ["防寒布", "草绳", "涂白剂"]},
    "other": {"standard_work_hours": 4.0, "common_materials": []},
}

# 实际工时相对标准工时的偏差阈值：绝对偏差比例与最小绝对小时数同时超过才判定为偏差较大
WORK_HOURS_DEVIATION_RATIO = 0.3
WORK_HOURS_DEVIATION_MIN_HOURS = 1.0

# ---------------------------------------------------------------- 绿植更换
PLANT_CATEGORY = EnumGroup("plant_category", [
    ("tree", "乔木"),
    ("shrub", "灌木"),
    ("flower", "草本花卉"),
    ("ground", "地被草坪"),
    ("vine", "藤本植物"),
    ("aquatic", "水生植物"),
])

REPLACEMENT_REASON = EnumGroup("replacement_reason", [
    ("dead", "枯死更换"),
    ("disease", "病虫害更换"),
    ("aging", "老化更新"),
    ("upgrade", "品种改造"),
    ("supplement", "补植补种"),
    ("design", "景观调整"),
])

OLD_PLANT_STATUS = EnumGroup("old_plant_status", [
    ("dead", "已枯死"),
    ("dying", "长势衰弱"),
    ("diseased", "感染病虫害"),
    ("aging", "老化退化"),
    ("normal", "长势正常"),
])

MEASURE_UNIT = EnumGroup("measure_unit", [
    ("plant", "株"),
    ("square_meter", "平方米"),
    ("pot", "盆"),
    ("clump", "丛"),
])

# 前端下拉与文档共用的一份字典清单
ENUM_GROUPS = {
    "green_space_type": GREEN_SPACE_TYPE,
    "maintenance_grade": MAINTENANCE_GRADE,
    "green_space_status": GREEN_SPACE_STATUS,
    "task_type": TASK_TYPE,
    "task_priority": TASK_PRIORITY,
    "task_status": TASK_STATUS,
    "quality_result": QUALITY_RESULT,
    "weather": WEATHER,
    "plant_category": PLANT_CATEGORY,
    "replacement_reason": REPLACEMENT_REASON,
    "old_plant_status": OLD_PLANT_STATUS,
    "measure_unit": MEASURE_UNIT,
}


def all_enums():
    """返回全部字典，供前端下拉初始化。"""

    return {name: group.options for name, group in ENUM_GROUPS.items()}


def task_standards():
    """返回各任务类型的标准工时与常用材料，供录入时带出。"""

    return {
        task_type: {
            "task_type": task_type,
            "task_type_label": TASK_TYPE.label(task_type),
            "standard_work_hours": standard["standard_work_hours"],
            "common_materials": list(standard["common_materials"]),
        }
        for task_type, standard in TASK_TYPE_STANDARDS.items()
    }


def work_hours_deviation(actual, standard):
    """计算实际工时相对标准工时的偏差比例。

    返回 (偏差比例, 偏差小时数)；标准值或实际值缺失时返回 (None, None)。
    偏差比例 = (实际 - 标准) / 标准，正值为超工时，负值为低于标准。
    """

    if actual is None or standard in (None, 0):
        return None, None
    try:
        actual_value = float(actual)
        standard_value = float(standard)
    except (TypeError, ValueError):
        return None, None
    if standard_value <= 0:
        return None, None
    return (
        round((actual_value - standard_value) / standard_value, 4),
        round(actual_value - standard_value, 2),
    )


def is_significant_hours_deviation(actual, standard):
    """实际工时与标准工时偏差是否较大：比例与绝对小时数同时超过阈值。"""

    ratio, _ = work_hours_deviation(actual, standard)
    if ratio is None:
        return False
    return (
        abs(ratio) >= WORK_HOURS_DEVIATION_RATIO
        and abs(float(actual) - float(standard)) >= WORK_HOURS_DEVIATION_MIN_HOURS
    )


def split_materials(materials_text):
    """把材料文本拆成条目，兼容顿号、逗号、分号、空白等分隔符。"""

    if not materials_text:
        return []
    normalized = str(materials_text)
    for separator in ("、", "，", "；", ";", ","):
        normalized = normalized.replace(separator, "\n")
    return [item.strip() for item in normalized.splitlines() if item.strip()]


# 表示「未使用材料」的填写值，不应参与材料偏差判定
NO_MATERIAL_TOKENS = {"无", "没有", "无材料", "未使用", "未使用材料", "/", "-", "none", "无。"}


def is_significant_materials_deviation(materials_text, common_materials):
    """实际使用材料与常用材料清单完全无交集时判定为材料偏差较大。

    常用清单为空（如「其他养护」）或实际未填/明确填「无」时不判定。
    """

    if not common_materials:
        return False
    used = split_materials(materials_text)
    if not used:
        return False
    if all(item.lower() in NO_MATERIAL_TOKENS for item in used):
        return False
    common = {item.strip() for item in common_materials if item.strip()}
    return not any(any(token in item or item in token for token in common) for item in used)
