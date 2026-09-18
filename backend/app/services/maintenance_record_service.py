"""养护记录业务逻辑。"""

from datetime import datetime, time

from sqlalchemy import func, or_

from ..constants import (
    QUALITY_RESULT,
    TASK_TYPE_STANDARDS,
    is_significant_hours_deviation,
    is_significant_materials_deviation,
)
from ..errors import ConflictError, ValidationError
from ..extensions import db
from ..models import GreenSpace, MaintenanceRecord, MaintenanceTask, PlantReplacement
from ..utils.dates import format_date
from ..utils.numbers import to_float
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix


class MaintenanceRecordService(BaseService):
    """养护记录录入。

    与养护任务的联动规则（在同一个事务内完成）：

    1. 任务处于「待执行」时登记记录，任务自动转为「进行中」；
    2. 任务存在合格记录且没有不合格记录时，任务自动转为「已完成」；
    3. 存在不合格记录时任务保持「进行中」，等待整改复检；
    4. 删除记录后重新推算任务状态，避免出现「已完成但没有记录」的脏数据；
    5. 已取消的任务不允许再补录记录。
    """

    model = MaintenanceRecord
    label = "养护记录"
    code_field = "record_no"
    code_width = 3

    SORTABLE = {
        "record_date": MaintenanceRecord.record_date,
        "record_no": MaintenanceRecord.record_no,
        "created_at": MaintenanceRecord.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("MR")

    # ------------------------------------------------------------ 校验
    @classmethod
    def prepare_instance(cls, instance, payload):
        task_id = payload.get("task_id", instance.task_id)
        green_space_id = payload.get("green_space_id", instance.green_space_id)

        task = None
        if task_id:
            task = db.session.get(MaintenanceTask, task_id)
            if task is None:
                raise ValidationError("录入失败", details={"task_id": "关联的养护任务不存在"})
            if task.status == "cancelled":
                raise ConflictError(f"任务 {task.task_no} 已取消，不能补录养护记录")
            if green_space_id and green_space_id != task.green_space_id:
                raise ValidationError(
                    "录入失败", details={"green_space_id": "所属绿地与关联任务的绿地不一致"}
                )
            green_space_id = task.green_space_id
            # 关联任务时任务类型始终跟随任务，忽略前端传入值
            payload["task_type"] = task.task_type
            instance.task_type = task.task_type
        elif "task_type" in payload:
            instance.task_type = payload["task_type"] or None

        if not green_space_id:
            raise ValidationError(
                "录入失败", details={"green_space_id": "请选择所属绿地或关联养护任务"}
            )
        space = db.session.get(GreenSpace, green_space_id)
        if space is None:
            raise ValidationError("录入失败", details={"green_space_id": "所选绿地不存在"})

        instance.green_space_id = green_space_id
        record_date = payload.get("record_date", instance.record_date)
        if record_date and space.established_date and record_date < space.established_date:
            raise ValidationError(
                "录入失败",
                details={"record_date": f"养护日期不能早于该绿地建成日期 {space.established_date}"},
            )

    @classmethod
    def prepare_update(cls, instance, payload):
        setattr(instance, "_previous_task_id", instance.task_id)
        cls.prepare_instance(instance, payload)

    @classmethod
    def apply_derived(cls, instance):
        """按任务类型快照标准值，判定工时/材料偏差并强制填写原因。"""

        standard = TASK_TYPE_STANDARDS.get(instance.task_type)
        if standard is None:
            instance.standard_work_hours = None
            instance.common_materials = None
            instance.hours_deviation_flag = False
            instance.materials_deviation_flag = False
            instance.deviation_reason = None
            return

        instance.standard_work_hours = standard["standard_work_hours"]
        instance.common_materials = MaintenanceRecord.materials_to_text(standard["common_materials"])
        instance.hours_deviation_flag = is_significant_hours_deviation(
            instance.work_hours, standard["standard_work_hours"]
        )
        instance.materials_deviation_flag = is_significant_materials_deviation(
            instance.materials, standard["common_materials"]
        )

        reason = (instance.deviation_reason or "").strip()
        if instance.hours_deviation_flag or instance.materials_deviation_flag:
            if not reason:
                dimensions = []
                if instance.hours_deviation_flag:
                    dimensions.append(
                        f"工时 {to_float(instance.work_hours)}h 与标准 "
                        f"{standard['standard_work_hours']}h 偏差较大"
                    )
                if instance.materials_deviation_flag:
                    dimensions.append("使用材料不在该任务类型的常用材料范围内")
                raise ValidationError(
                    "录入失败",
                    details={"deviation_reason": "；".join(dimensions) + "，请填写偏差原因"},
                )
            instance.deviation_reason = reason
        else:
            # 实际值回到标准范围内时清理历史原因，避免残留误导
            instance.deviation_reason = None

    # ------------------------------------------------------------ 任务状态联动
    @classmethod
    def sync_task_status(cls, task_id, *, task=None):
        """按该任务下的全部养护记录重新推算任务状态。"""

        if task is None:
            if not task_id:
                return None
            task = db.session.get(MaintenanceTask, task_id)
            if task is None:
                return None
        if task.status == "cancelled":
            return task

        records = (
            db.session.query(MaintenanceRecord)
            .filter(MaintenanceRecord.task_id == task.id)
            .all()
        )
        if not records:
            task.status = "pending"
            task.completed_at = None
            return task

        qualified = [item for item in records if item.quality_result == "qualified"]
        unqualified = [item for item in records if item.quality_result == "unqualified"]

        if qualified and not unqualified:
            task.status = "completed"
            latest = max(item.record_date for item in records)
            task.completed_at = datetime.combine(latest, time.min)
        else:
            task.status = "in_progress"
            task.completed_at = None
        return task

    @classmethod
    def after_create(cls, instance, payload):
        cls.sync_task_status(instance.task_id)

    @classmethod
    def after_update(cls, instance, payload):
        cls.sync_task_status(getattr(instance, "_previous_task_id", None))
        cls.sync_task_status(instance.task_id)

    @classmethod
    def delete(cls, obj_id):
        instance = cls.get(obj_id)
        task_id = instance.task_id
        db.session.delete(instance)
        db.session.flush()
        cls.sync_task_status(task_id)
        db.session.commit()
        return instance

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("task_id"):
            query = query.filter(MaintenanceRecord.task_id == filters["task_id"])
        if filters.get("green_space_id"):
            query = query.filter(MaintenanceRecord.green_space_id == filters["green_space_id"])
        if filters.get("quality_result"):
            query = query.filter(MaintenanceRecord.quality_result == filters["quality_result"])
        if filters.get("weather"):
            query = query.filter(MaintenanceRecord.weather == filters["weather"])
        if filters.get("unlinked"):
            query = query.filter(MaintenanceRecord.task_id.is_(None))
        if filters.get("deviated"):
            query = query.filter(
                or_(
                    MaintenanceRecord.hours_deviation_flag.is_(True),
                    MaintenanceRecord.materials_deviation_flag.is_(True),
                )
            )
        if filters.get("date_from"):
            query = query.filter(MaintenanceRecord.record_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(MaintenanceRecord.record_date <= filters["date_to"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    MaintenanceRecord.record_no.like(like),
                    MaintenanceRecord.work_content.like(like),
                    MaintenanceRecord.worker.like(like),
                    MaintenanceRecord.materials.like(like),
                )
            )
        return query

    @classmethod
    def list_records(cls, filters, args):
        query = cls._apply_filters(db.session.query(MaintenanceRecord), filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, MaintenanceRecord.record_date.desc())
        )

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    @classmethod
    def summary(cls, filters):
        """记录汇总：条数、工时与质量评定分布。"""

        query = cls._apply_filters(db.session.query(MaintenanceRecord), filters)
        subquery = query.with_entities(
            MaintenanceRecord.id,
            MaintenanceRecord.record_date,
            MaintenanceRecord.work_hours,
            MaintenanceRecord.quality_result,
            MaintenanceRecord.hours_deviation_flag,
            MaintenanceRecord.materials_deviation_flag,
        ).subquery()

        total, hours = db.session.query(
            func.count(subquery.c.id), func.coalesce(func.sum(subquery.c.work_hours), 0)
        ).one()
        rows = (
            db.session.query(subquery.c.quality_result, func.count(subquery.c.id))
            .group_by(subquery.c.quality_result)
            .all()
        )
        quality = {code: 0 for code in QUALITY_RESULT.values}
        for result, count in rows:
            quality[result] = count
        first_date, last_date = db.session.query(
            func.min(subquery.c.record_date), func.max(subquery.c.record_date)
        ).one()

        deviated_total = (
            db.session.query(func.count(subquery.c.id))
            .filter(
                or_(
                    subquery.c.hours_deviation_flag.is_(True),
                    subquery.c.materials_deviation_flag.is_(True),
                )
            )
            .scalar()
        )
        hours_deviated = (
            db.session.query(func.count(subquery.c.id))
            .filter(subquery.c.hours_deviation_flag.is_(True))
            .scalar()
        )
        materials_deviated = (
            db.session.query(func.count(subquery.c.id))
            .filter(subquery.c.materials_deviation_flag.is_(True))
            .scalar()
        )

        replacement_total = (
            db.session.query(func.count(PlantReplacement.id))
            .filter(PlantReplacement.maintenance_record_id.in_(db.session.query(subquery.c.id)))
            .scalar()
            or 0
        )
        return {
            "record_count": total or 0,
            "total_work_hours": to_float(hours) or 0,
            "quality_summary": quality,
            "first_record_date": format_date(first_date),
            "last_record_date": format_date(last_date),
            "replacement_count": replacement_total,
            "deviation_summary": {
                "deviated_count": deviated_total or 0,
                "hours_deviated_count": hours_deviated or 0,
                "materials_deviated_count": materials_deviated or 0,
            },
        }
