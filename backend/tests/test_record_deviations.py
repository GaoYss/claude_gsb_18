"""养护记录标准值带出与偏差规则测试。"""

from datetime import date


# ------------------------------------------------------------ 标准带出
def test_record_linked_to_task_brings_out_standard(api, make_task):
    task = make_task(task_type="prune")
    data = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪香樟下垂枝 32 株",
        "work_hours": 6,
        "materials": "支撑杆",
        "quality_result": "qualified",
    }), 201)
    assert data["task_type"] == "prune"
    assert data["task_type_label"] == "修剪整形"
    assert data["standard_work_hours"] == 6.0
    assert "支撑杆" in data["common_materials"]
    assert data["has_deviation"] is False
    assert data["hours_deviated"] is False
    assert data["materials_deviated"] is False


def test_standalone_record_with_manual_task_type_brings_out_standard(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "task_type": "fertilize",
        "record_date": "2026-03-12",
        "work_content": "草坪追施复合肥",
        "work_hours": 4,
        "materials": "复合肥",
        "quality_result": "qualified",
    }), 201)
    assert data["standard_work_hours"] == 4.0
    assert "复合肥" in data["common_materials"]


def test_record_without_task_type_has_no_standard(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "record_date": "2026-03-12",
        "work_content": "日常巡查",
        "work_hours": 2,
        "quality_result": "qualified",
    }), 201)
    assert data["task_type"] is None
    assert data["standard_work_hours"] is None
    assert data["has_deviation"] is False


# ------------------------------------------------------------ 工时偏差
def test_over_hours_deviation_requires_reason(api, make_task):
    task = make_task(task_type="prune")  # 标准 6h
    response = api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪耗时明显偏长",
        "work_hours": 8,
        "quality_result": "qualified",
    })
    assert response.status_code == 422
    assert "deviation_reason" in response.get_json()["data"]
    assert "偏差较大" in response.get_json()["data"]["deviation_reason"]


def test_under_hours_deviation_requires_reason(api, make_task):
    task = make_task(task_type="prune")  # 标准 6h，实际 3h 偏差 -50%
    response = api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪耗时明显偏短",
        "work_hours": 3,
        "quality_result": "qualified",
    })
    assert response.status_code == 422
    assert "deviation_reason" in response.get_json()["data"]


def test_deviation_with_reason_is_accepted_and_recorded(api, make_task):
    task = make_task(task_type="prune")
    data = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪耗时偏长",
        "work_hours": 8,
        "quality_result": "qualified",
        "deviation_reason": "作业面受限、苗木规格偏大，清运耗时高于标准",
    }), 201)
    assert data["hours_deviated"] is True
    assert data["has_deviation"] is True
    assert data["hours_deviation_ratio"] == 0.3333
    assert data["deviation_reason"] == "作业面受限、苗木规格偏大，清运耗时高于标准"


def test_hours_within_threshold_needs_no_reason(api, make_task):
    task = make_task(task_type="prune")  # 6h ±30% 且至少 1h
    data = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "工时在标准允许范围内",
        "work_hours": 6.5,
        "quality_result": "qualified",
    }), 201)
    assert data["hours_deviated"] is False
    assert data["deviation_reason"] is None


# ------------------------------------------------------------ 材料偏差
def test_off_standard_material_requires_reason(api, make_task):
    task = make_task(task_type="prune")  # 常用：支撑杆/伤口涂补剂/安全警示带
    response = api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪",
        "work_hours": 6,
        "materials": "复合肥 180kg",
        "quality_result": "qualified",
    })
    assert response.status_code == 422
    assert "材料" in response.get_json()["data"]["deviation_reason"]


def test_off_standard_material_with_reason_flagged(api, make_task):
    task = make_task(task_type="prune")
    data = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪并应急施肥",
        "work_hours": 6,
        "materials": "复合肥 180kg",
        "quality_result": "qualified",
        "deviation_reason": "现场发现缺肥，临时增加施肥工序",
    }), 201)
    assert data["materials_deviated"] is True
    assert data["hours_deviated"] is False
    assert data["has_deviation"] is True


def test_material_none_does_not_count_as_deviation(api, make_task):
    task = make_task(task_type="prune")
    data = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪，未使用材料",
        "work_hours": 6,
        "materials": "无",
        "quality_result": "qualified",
    }), 201)
    assert data["materials_deviated"] is False
    assert data["has_deviation"] is False


# ------------------------------------------------------------ 更新回退
def test_update_back_to_standard_clears_reason(api, make_task):
    task = make_task(task_type="prune")
    record = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪耗时偏长",
        "work_hours": 8,
        "quality_result": "qualified",
        "deviation_reason": "作业面受限，耗时高于标准",
    }), 201)
    assert record["has_deviation"] is True

    updated = api.data(api.put(f"/api/v1/maintenance-records/{record['id']}", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪耗时回到标准范围",
        "work_hours": 6,
        "materials": "支撑杆",
        "quality_result": "qualified",
    }))
    assert updated["has_deviation"] is False
    assert updated["deviation_reason"] is None


# ------------------------------------------------------------ 筛选与看板
def test_deviated_list_filter_and_summary(api, make_task, make_space):
    prune_task = make_task(task_type="prune")
    fertilize_space = make_space(name="施肥绿地")

    api.post("/api/v1/maintenance-records", {
        "task_id": prune_task.id,
        "record_date": "2026-03-12",
        "work_content": "工时偏高",
        "work_hours": 9,
        "quality_result": "qualified",
        "deviation_reason": "超时作业",
    })
    api.post("/api/v1/maintenance-records", {
        "task_id": prune_task.id,
        "record_date": "2026-03-13",
        "work_content": "工时正常",
        "work_hours": 6,
        "quality_result": "qualified",
    })
    api.post("/api/v1/maintenance-records", {
        "green_space_id": fertilize_space.id,
        "task_type": "fertilize",
        "record_date": "2026-03-14",
        "work_content": "材料异常",
        "work_hours": 4,
        "materials": "生根粉",
        "quality_result": "qualified",
        "deviation_reason": "临时促根处理",
    })

    listing = api.data(api.get("/api/v1/maintenance-records", deviated="true", page_size=50))
    assert listing["meta"]["total"] == 2
    assert all(item["has_deviation"] for item in listing["items"])
    assert listing["summary"]["deviation_summary"] == {
        "deviated_count": 2, "hours_deviated_count": 1, "materials_deviated_count": 1,
    }

    deviations = api.data(api.get("/api/v1/statistics/deviations", limit=50))
    assert deviations["deviated_count"] == 2
    assert deviations["hours_deviated_count"] == 1
    assert deviations["materials_deviated_count"] == 1
    by_type = {item["value"]: item["count"] for item in deviations["by_task_type"]}
    assert by_type == {"prune": 1, "fertilize": 1}
    assert all(item["deviation_reason"] for item in deviations["items"])

    overview = api.data(api.get("/api/v1/statistics/overview"))
    assert overview["record"]["deviated_count"] == 2
