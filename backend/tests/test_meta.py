"""字典与健康检查接口测试。"""


def test_health_reports_database_up(api):
    data = api.data(api.get("/api/v1/meta/health"))
    assert data["status"] == "ok"
    assert data["database"] == "up"


def test_enums_cover_all_business_groups(api):
    data = api.data(api.get("/api/v1/meta/enums"))
    enums = data["enums"]
    expected = {
        "green_space_type",
        "maintenance_grade",
        "green_space_status",
        "task_type",
        "task_priority",
        "task_status",
        "quality_result",
        "weather",
        "plant_category",
        "replacement_reason",
        "old_plant_status",
        "measure_unit",
    }
    assert expected.issubset(set(enums))
    assert {"value": "park", "label": "公园绿地"} in enums["green_space_type"]


def test_task_standards_are_delivered_with_enums(api):
    data = api.data(api.get("/api/v1/meta/enums"))
    standards = data["task_standards"]
    assert {"prune", "water", "fertilize", "pest", "weed", "clean", "replant", "winter", "other"} <= set(standards)
    prune = standards["prune"]
    assert prune["standard_hours"] == 6.0
    assert prune["hours_tolerance_ratio"] == 0.30
    assert prune["hours_abs_tolerance"] == 0.5
    assert prune["materials_default"]
    assert isinstance(prune["materials_keywords"], list) and prune["materials_keywords"]
    # other 明确不设标准
    assert standards["other"] is None


def test_unknown_api_returns_unified_404(api):
    response = api.get("/api/v1/not-exists")
    assert response.status_code == 404
    body = response.get_json()
    assert body["success"] is False
    assert body["code"] == 40400


def test_non_json_body_is_rejected(client):
    response = client.post("/api/v1/green-spaces", data="name=abc",
                           content_type="application/x-www-form-urlencoded")
    assert response.status_code == 400
    assert response.get_json()["message"].startswith("请求体必须为 JSON")
