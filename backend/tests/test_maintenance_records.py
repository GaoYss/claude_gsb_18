"""养护记录接口测试：重点覆盖与养护任务的状态联动。"""

from datetime import date


def test_create_record_without_task_is_allowed(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "record_date": "2026-04-02",
        "work_content": "日常巡查，清理零星垃圾与倒伏草本",
        "worker": "何丽萍",
        "work_hours": 2,
        "quality_result": "qualified",
    }), 201)
    assert data["record_no"] == f"MR-{date.today():%Y%m%d}-001"
    assert data["task"] is None
    assert data["green_space"]["id"] == space.id


def test_create_record_requires_green_space_or_task(api):
    response = api.post("/api/v1/maintenance-records", {
        "record_date": "2026-04-02",
        "work_content": "无归属记录",
    })
    assert response.status_code == 422
    assert response.get_json()["data"] == {"green_space_id": "请选择所属绿地或关联养护任务"}


def test_record_derives_green_space_from_task(api, make_task):
    task = make_task()
    data = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪香樟下垂枝 32 株",
    }), 201)
    assert data["green_space_id"] == task.green_space_id
    assert data["task"]["task_no"] == task.task_no


def test_green_space_must_match_task(api, make_task, make_space):
    task = make_task()
    other = make_space(name="另一处绿地")
    response = api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "green_space_id": other.id,
        "record_date": "2026-03-12",
        "work_content": "绿地与任务不匹配",
    })
    assert response.status_code == 422
    assert "不一致" in response.get_json()["data"]["green_space_id"]


def test_qualified_record_completes_task(api, make_task):
    task = make_task()
    assert api.data(api.get(f"/api/v1/maintenance-tasks/{task.id}"))["status"] == "pending"

    api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪完成，清运枝条 2 车",
        "quality_result": "qualified",
    })
    detail = api.data(api.get(f"/api/v1/maintenance-tasks/{task.id}"))
    assert detail["status"] == "completed"
    assert detail["completed_at"].startswith("2026-03-12")


def test_unqualified_record_blocks_task_completion(api, make_task):
    task = make_task()
    unqualified = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪后现场未清理",
        "quality_result": "unqualified",
    }), 201)
    detail = api.data(api.get(f"/api/v1/maintenance-tasks/{task.id}"))
    assert detail["status"] == "in_progress"
    assert detail["completed_at"] is None

    # 存在不合格记录时，追加合格记录也不会自动完成，必须先整改
    api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-15",
        "work_content": "整改复检合格",
        "quality_result": "qualified",
    })
    assert api.data(api.get(f"/api/v1/maintenance-tasks/{task.id}"))["status"] == "in_progress"

    # 把不合格记录改判为合格后，任务自动完成
    api.put(f"/api/v1/maintenance-records/{unqualified['id']}", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪后现场未清理，当日整改完成",
        "quality_result": "qualified",
    })
    assert api.data(api.get(f"/api/v1/maintenance-tasks/{task.id}"))["status"] == "completed"


def test_cancelled_task_rejects_new_record(api, make_task):
    task = make_task(status="cancelled")
    response = api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "取消后补录",
    })
    assert response.status_code == 409
    assert "已取消" in response.get_json()["message"]


def test_record_date_cannot_precede_established_date(api, make_space):
    space = make_space(established_date=date(2020, 1, 1))
    response = api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "record_date": "2019-12-31",
        "work_content": "建成前记录",
    })
    assert response.status_code == 422
    assert "建成日期" in response.get_json()["data"]["record_date"]


def test_delete_record_reverts_task_status(api, make_task):
    task = make_task()
    record = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪完成",
        "quality_result": "qualified",
    }), 201)
    assert api.data(api.get(f"/api/v1/maintenance-tasks/{task.id}"))["status"] == "completed"

    api.delete(f"/api/v1/maintenance-records/{record['id']}")
    task_after = api.data(api.get(f"/api/v1/maintenance-tasks/{task.id}"))
    assert task_after["status"] == "pending"
    assert task_after["completed_at"] is None


def test_update_record_quality_resyncs_task(api, make_task):
    task = make_task()
    record = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪完成",
        "quality_result": "qualified",
    }), 201)
    assert api.data(api.get(f"/api/v1/maintenance-tasks/{task.id}"))["status"] == "completed"

    api.put(f"/api/v1/maintenance-records/{record['id']}", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪完成，验收不合格",
        "quality_result": "unqualified",
    })
    assert api.data(api.get(f"/api/v1/maintenance-tasks/{task.id}"))["status"] == "in_progress"


def test_list_filters_and_summary(api, make_task, make_record):
    task = make_task()
    make_record(task=task, work_hours=6, quality_result="qualified")
    make_record(task=task, work_hours=4, quality_result="unqualified", record_date=date(2026, 3, 20),
                deviation_reason="现场配合设施检修，作业时间缩短")
    make_record(space=task.green_space, work_hours=2, quality_result="qualified",
                record_date=date(2026, 4, 1), work_content="日常巡查，清理园路落叶")

    data = api.data(api.get("/api/v1/maintenance-records", task_id=task.id))
    assert data["meta"]["total"] == 2
    assert data["summary"]["record_count"] == 2
    assert data["summary"]["total_work_hours"] == 10.0
    assert data["summary"]["quality_summary"] == {"qualified": 1, "pending": 0, "unqualified": 1}

    ranged = api.data(api.get("/api/v1/maintenance-records", date_from="2026-04-01",
                              date_to="2026-04-30"))
    assert ranged["meta"]["total"] == 1

    keyword = api.data(api.get("/api/v1/maintenance-records", keyword="下垂枝"))
    assert keyword["meta"]["total"] == 2


# ------------------------------------------------------------ 作业标准与偏差
def test_task_linked_record_inherits_task_type(api, make_task):
    task = make_task(task_type="water")
    data = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-03-12",
        "work_content": "早晚两班次浇灌新栽苗木 260 株",
    }), 201)
    assert data["task_type"] == "water"
    assert data["task_type_label"] == "浇灌排涝"
    assert data["standard_hours"] == 4.0
    assert data["hours_lower"] == 2.8
    assert data["hours_upper"] == 5.2
    assert data["is_deviated"] is False
    assert data["deviation_flags"] == []


def test_explicit_task_type_conflicting_with_task_rejected(api, make_task):
    task = make_task(task_type="prune")
    response = api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "task_type": "water",
        "record_date": "2026-03-12",
        "work_content": "类型与任务不一致",
    })
    assert response.status_code == 422
    assert "以养护任务为准" in response.get_json()["data"]["task_type"]


def test_update_switching_task_follows_new_task_type(api, make_space, make_task):
    space = make_space()
    prune_task = make_task(space=space, task_type="prune", plan_date=date(2026, 3, 10))
    water_task = make_task(space=space, task_type="water", plan_date=date(2026, 3, 11))
    record = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": prune_task.id,
        "record_date": "2026-03-12",
        "work_content": "修剪作业",
        "work_hours": 6,
        "materials": "修枝剪",
    }), 201)
    assert record["task_type"] == "prune"

    # 切到浇灌任务且不带 task_type，类型自动跟随为 water；工时 6 对 water 标准 4 偏差，需补原因
    response = api.put(f"/api/v1/maintenance-records/{record['id']}", {
        "task_id": water_task.id,
        "record_date": "2026-03-12",
        "work_content": "转执行浇灌作业",
        "work_hours": 6,
        "materials": "修枝剪",
    })
    assert response.status_code == 422
    assert "deviation_reason" in response.get_json()["data"]

    updated = api.data(api.put(f"/api/v1/maintenance-records/{record['id']}", {
        "task_id": water_task.id,
        "record_date": "2026-03-12",
        "work_content": "转执行浇灌作业",
        "work_hours": 6,
        "materials": "修枝剪",
        "deviation_reason": "任务调整，浇灌面积大于常规",
    }))
    assert updated["task_type"] == "water"
    assert updated["deviation_flags"] == ["work_hours", "materials"]


def test_standalone_record_allows_manual_task_type(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "task_type": "weed",
        "record_date": "2026-04-02",
        "work_content": "清除绿篱内杂草约 800 平方米",
    }), 201)
    assert data["task_type"] == "weed"

    # 不关联任务也不选类型，允许作为日常巡查录入
    plain = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "record_date": "2026-04-03",
        "work_content": "日常巡查，无明显异常",
    }), 201)
    assert plain["task_type"] is None
    assert plain["standard_hours"] is None


def test_work_hours_deviation_requires_reason(api, make_space):
    space = make_space()
    base = {
        "green_space_id": space.id,
        "task_type": "water",   # 标准 4h，区间 2.8~5.2
        "record_date": "2026-04-02",
        "work_content": "连续高温抗旱浇灌",
        "work_hours": 1,
    }
    response = api.post("/api/v1/maintenance-records", base)
    assert response.status_code == 422
    assert "偏差原因" in response.get_json()["data"]["deviation_reason"]

    data = api.data(api.post("/api/v1/maintenance-records", {
        **base, "deviation_reason": "连续高温干旱，临时增加浇灌频次",
    }), 201)
    assert data["deviation_flags"] == ["work_hours"]
    assert data["work_hours_deviation"] is True
    assert data["materials_deviation"] is False
    assert data["is_deviated"] is True
    assert data["deviation_reason"] == "连续高温干旱，临时增加浇灌频次"


def test_materials_deviation_requires_reason(api, make_space):
    space = make_space()
    base = {
        "green_space_id": space.id,
        "task_type": "prune",   # 标准 6h
        "record_date": "2026-04-02",
        "work_content": "修剪香樟下垂枝 32 株",
        "work_hours": 6,
        "materials": "复合肥 180kg",   # 与修剪类常用材料完全无关
    }
    response = api.post("/api/v1/maintenance-records", base)
    assert response.status_code == 422
    assert "偏差原因" in response.get_json()["data"]["deviation_reason"]

    data = api.data(api.post("/api/v1/maintenance-records", {
        **base, "deviation_reason": "库存材料替代，已现场核实",
    }), 201)
    assert data["deviation_flags"] == ["materials"]


def test_double_deviation_flag_order(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "task_type": "prune",
        "record_date": "2026-04-02",
        "work_content": "应急修剪并顺手施肥",
        "work_hours": 12,
        "materials": "复合肥 180kg",
        "deviation_reason": "应急抢险，作业范围与用料均超出常规计划",
    }), 201)
    assert data["deviation_flags"] == ["work_hours", "materials"]


def test_type_without_standard_never_blocks(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "task_type": "other",
        "record_date": "2026-04-02",
        "work_content": "其他临时性养护",
        "work_hours": 20,
        "materials": "随便登记的材料",
    }), 201)
    assert data["is_deviated"] is False


def test_deviation_reason_cleared_after_record_back_to_standard(api, make_space):
    space = make_space()
    record = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "task_type": "water",
        "record_date": "2026-04-02",
        "work_content": "抗旱浇灌",
        "work_hours": 1,
        "deviation_reason": "连续高温干旱，临时增加浇灌频次",
    }), 201)
    assert record["is_deviated"] is True

    updated = api.data(api.put(f"/api/v1/maintenance-records/{record['id']}", {
        "green_space_id": space.id,
        "task_type": "water",
        "record_date": "2026-04-02",
        "work_content": "抗旱浇灌",
        "work_hours": 4,
    }))
    assert updated["is_deviated"] is False
    assert updated["deviation_reason"] is None


def test_update_into_deviation_requires_reason(api, make_space):
    space = make_space()
    record = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "task_type": "prune",
        "record_date": "2026-04-02",
        "work_content": "修剪作业",
        "work_hours": 6,
        "materials": "修枝剪、手锯",
    }), 201)

    response = api.put(f"/api/v1/maintenance-records/{record['id']}", {
        "green_space_id": space.id,
        "task_type": "prune",
        "record_date": "2026-04-02",
        "work_content": "修剪作业延时",
        "work_hours": 12,
        "materials": "修枝剪、手锯",
    })
    assert response.status_code == 422

    updated = api.data(api.put(f"/api/v1/maintenance-records/{record['id']}", {
        "green_space_id": space.id,
        "task_type": "prune",
        "record_date": "2026-04-02",
        "work_content": "修剪作业延时",
        "work_hours": 12,
        "materials": "修枝剪、手锯",
        "deviation_reason": "台风后应急抢险",
    }))
    assert updated["deviation_flags"] == ["work_hours"]
    assert updated["deviation_reason"] == "台风后应急抢险"


def test_reason_ignored_when_no_deviation(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "task_type": "prune",
        "record_date": "2026-04-02",
        "work_content": "常规修剪",
        "work_hours": 6,
        "materials": "修枝剪、手锯",
        "deviation_reason": "其实没有偏差，原因应被忽略",
    }), 201)
    assert data["is_deviated"] is False
    assert data["deviation_reason"] is None


def test_missing_work_hours_does_not_trigger_hours_deviation(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "task_type": "prune",
        "record_date": "2026-04-02",
        "work_content": "只登记作业，暂未统计工时",
    }), 201)
    assert data["work_hours"] is None
    assert data["work_hours_deviation"] is False
    assert data["is_deviated"] is False


def test_deviated_and_task_type_filters(api, make_space):
    space = make_space()
    # 工时偏差
    api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id, "task_type": "water", "record_date": "2026-04-01",
        "work_content": "偏差浇水", "work_hours": 1,
        "deviation_reason": "高温抗旱",
    }), 201)
    # 材料偏差
    api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id, "task_type": "prune", "record_date": "2026-04-02",
        "work_content": "偏差材料", "work_hours": 6, "materials": "复合肥",
        "deviation_reason": "材料替代",
    }), 201)
    # 合规记录
    api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id, "task_type": "prune", "record_date": "2026-04-03",
        "work_content": "常规修剪", "work_hours": 6, "materials": "修枝剪",
    }), 201)

    deviated = api.data(api.get("/api/v1/maintenance-records", deviated="true"))
    assert deviated["meta"]["total"] == 2

    water_only = api.data(api.get("/api/v1/maintenance-records", task_type="water"))
    assert water_only["meta"]["total"] == 1
    assert water_only["items"][0]["task_type"] == "water"

    both = api.data(api.get("/api/v1/maintenance-records", deviated="true", task_type="prune"))
    assert both["meta"]["total"] == 1
    assert both["items"][0]["deviation_flags"] == ["materials"]
