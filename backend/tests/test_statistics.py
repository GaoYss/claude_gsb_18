"""统计看板接口测试。"""

from datetime import date, timedelta


def test_overview_reflects_seeded_data(api, seeded):
    data = api.data(api.get("/api/v1/statistics/overview"))
    assert data["green_space"]["total"] == seeded["green_space"]
    assert data["green_space"]["total_area"] > 0
    assert data["green_space"]["by_status"]["archived"] == 1

    assert data["task"]["total"] == seeded["maintenance_task"]
    assert data["task"]["by_status"]["cancelled"] == 1
    assert 0 <= data["task"]["completion_rate"] <= 100

    assert data["record"]["total"] == seeded["maintenance_record"]
    assert data["record"]["total_work_hours"] > 0
    assert data["replacement"]["total"] == seeded["plant_replacement"]
    assert data["replacement"]["total_amount"] > 0


def test_overdue_and_due_soon_reminders(api, make_space, make_task):
    space = make_space()
    make_task(space=space, plan_date=date.today() - timedelta(days=3), status="pending")
    make_task(space=space, plan_date=date.today() + timedelta(days=2), status="pending")
    make_task(space=space, plan_date=date.today() - timedelta(days=3), status="completed")

    overview = api.data(api.get("/api/v1/statistics/overview"))
    assert overview["task"]["overdue_count"] == 1
    assert overview["task"]["due_soon_count"] == 1

    reminders = api.data(api.get("/api/v1/statistics/reminders"))
    assert len(reminders["overdue"]) == 1
    assert reminders["overdue"][0]["is_overdue"] is True
    assert len(reminders["upcoming"]) == 1


def test_distributions_cover_all_dimensions(api, make_task, make_replacement, make_record):
    task = make_task()
    record = make_record(task=task)
    make_replacement(record=record, plant_category="shrub", reason="aging", quantity=30, unit_price=10)

    data = api.data(api.get("/api/v1/statistics/distributions"))
    assert {item["value"] for item in data["green_space_by_type"]} == {"park"}
    assert {item["value"] for item in data["green_space_by_grade"]} == {"level2"}
    assert data["green_space_by_district"][0]["value"] == "西湖区"
    assert {item["value"] for item in data["task_by_type"]} == {"prune"}
    assert data["replacement_by_category"][0]["amount"] == 300.0
    assert data["replacement_by_reason"][0]["quantity"] == 30.0


def test_trends_return_requested_month_window(api, seeded):
    data = api.data(api.get("/api/v1/statistics/trends", months=6))
    items = data["items"]
    assert len(items) == 6
    assert items[-1]["month"] == f"{date.today():%Y-%m}"
    assert sum(item["record_count"] for item in items) == seeded["maintenance_record"]
    for item in items:
        assert set(item) == {
            "month", "record_count", "work_hours",
            "replacement_count", "replacement_quantity", "replacement_amount",
        }


def test_ranking_orders_by_record_count(api, make_space, make_record):
    busy = make_space(name="高频养护绿地")
    quiet = make_space(name="低频养护绿地")
    make_record(space=busy)
    make_record(space=busy, record_date=date(2026, 4, 2))
    make_record(space=quiet)

    items = api.data(api.get("/api/v1/statistics/ranking"))["items"]
    assert items[0]["name"] == "高频养护绿地"
    assert items[0]["record_count"] == 2
    assert items[0]["green_space_id"] == busy.id


def test_dashboard_returns_all_sections(api, seeded):
    data = api.data(api.get("/api/v1/statistics/dashboard"))
    assert set(data) == {
        "overview", "distributions", "trends", "deviation", "ranking",
        "overdue_tasks", "upcoming_tasks", "recent_activity",
    }
    assert len(data["trends"]) == 6
    assert data["recent_activity"]["records"]
    assert data["recent_activity"]["replacements"]


def test_deviation_summary_counts_groups_and_records(api, make_space, make_record):
    space = make_space()
    # prune 标准 6h：一条工时偏差，一条材料偏差
    make_record(space=space, task_type="prune", work_hours=12,
                materials="修枝剪、手锯", deviation_reason="应急抢险，工时超标",
                record_date=date(2026, 4, 2))
    make_record(space=space, task_type="prune", work_hours=6,
                materials="复合肥 180kg", deviation_reason="材料替代",
                record_date=date(2026, 4, 5))
    # 一条合规记录不应计入
    make_record(space=space, task_type="prune", work_hours=6,
                materials="修枝剪", record_date=date(2026, 4, 6))

    dashboard = api.data(api.get("/api/v1/statistics/dashboard"))
    deviation = dashboard["deviation"]
    assert deviation["total"] == 2
    assert deviation["work_hours_count"] == 1
    assert deviation["materials_count"] == 1

    prune_group = next(item for item in deviation["by_task_type"] if item["value"] == "prune")
    assert prune_group["count"] == 2
    assert prune_group["label"] == "修剪整形"

    records = deviation["records"]
    assert len(records) == 2
    # 按养护日期倒序
    assert records[0]["record_date"] == "2026-04-05"
    first = records[0]
    assert first["green_space"]["id"] == space.id
    assert first["standard_hours"] == 6.0
    assert first["hours_lower"] == 4.2
    assert first["hours_upper"] == 7.8
    assert first["deviation_flags"] == ["materials"]
    assert first["deviation_reason"] == "材料替代"
    assert records[1]["deviation_flags"] == ["work_hours"]


def test_seeded_dashboard_contains_stable_deviation_records(api, seeded):
    # seed 中固定保底了一条工时偏差与一条材料偏差记录
    deviation = api.data(api.get("/api/v1/statistics/dashboard"))["deviation"]
    assert deviation["total"] >= 2
    assert deviation["work_hours_count"] >= 1
    assert deviation["materials_count"] >= 1
    assert deviation["records"]
    for item in deviation["records"]:
        assert item["deviation_reason"]
        assert item["deviation_flags"]
