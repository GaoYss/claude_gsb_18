"""养护记录模型。"""

from ..constants import (
    QUALITY_RESULT,
    TASK_TYPE,
    TASK_TYPE_STANDARDS,
    WEATHER,
    work_hours_deviation,
)
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from ..utils.numbers import to_float
from .mixins import TimestampMixin, quantity_column


class MaintenanceRecord(TimestampMixin, db.Model):
    """养护记录录入：某次养护任务的作业明细，也可独立登记日常养护。"""

    __tablename__ = "maintenance_record"

    id = db.Column(db.Integer, primary_key=True)
    record_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("maintenance_task.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    green_space_id = db.Column(
        db.Integer, db.ForeignKey("green_space.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 任务类型：关联任务时跟随任务，日常巡查手工选择，用于带出标准工时与常用材料
    task_type = db.Column(db.String(32), nullable=True, index=True)
    record_date = db.Column(db.Date, nullable=False, index=True)
    work_content = db.Column(db.Text, nullable=False)
    worker = db.Column(db.String(64))
    work_hours = db.Column(quantity_column())
    standard_work_hours = db.Column(quantity_column())
    weather = db.Column(db.String(16))
    materials = db.Column(db.Text)
    # 录入时按任务类型快照的常用材料（换行分隔），作为材料偏差的对照基准
    common_materials = db.Column(db.Text)
    quality_result = db.Column(db.String(16), nullable=False, default="pending", index=True)
    # 工时/材料是否偏离标准较大（写入时按当时标准判定落库，便于历史留痕与看板汇总）
    hours_deviation_flag = db.Column(db.Boolean, nullable=False, default=False, index=True)
    materials_deviation_flag = db.Column(db.Boolean, nullable=False, default=False, index=True)
    # 工时或材料偏离标准较大时，必须填写偏差原因
    deviation_reason = db.Column(db.Text)
    issue_found = db.Column(db.Text)
    remark = db.Column(db.Text)

    task = db.relationship("MaintenanceTask", back_populates="records")
    green_space = db.relationship("GreenSpace", back_populates="records", lazy="joined")
    replacements = db.relationship("PlantReplacement", back_populates="record")

    @property
    def common_material_list(self):
        if not self.common_materials:
            return []
        return [item for item in self.common_materials.split("\n") if item]

    @property
    def hours_deviation_ratio(self):
        ratio, _ = work_hours_deviation(self.work_hours, self.standard_work_hours)
        return ratio

    @property
    def hours_deviation_hours(self):
        _, delta = work_hours_deviation(self.work_hours, self.standard_work_hours)
        return delta

    @property
    def hours_deviated(self):
        return bool(self.hours_deviation_flag)

    @property
    def materials_deviated(self):
        return bool(self.materials_deviation_flag)

    @property
    def has_deviation(self):
        """工时或材料任一项与标准偏差较大。"""

        return self.hours_deviation_flag or self.materials_deviation_flag

    @staticmethod
    def materials_to_text(items):
        """常用材料列表入库为换行分隔文本。"""

        if not items:
            return None
        if isinstance(items, str):
            items = items.split("\n")
        cleaned = [str(item).strip() for item in items if str(item).strip()]
        return "\n".join(dict.fromkeys(cleaned)) or None

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "record_no": self.record_no,
            "task_id": self.task_id,
            "task": (
                {
                    "id": self.task.id,
                    "task_no": self.task.task_no,
                    "title": self.task.title,
                    "status": self.task.status,
                }
                if self.task
                else None
            ),
            "green_space_id": self.green_space_id,
            "green_space": self.green_space.to_brief() if self.green_space else None,
            "task_type": self.task_type,
            "task_type_label": TASK_TYPE.label(self.task_type) if self.task_type else None,
            "record_date": format_date(self.record_date),
            "work_content": self.work_content,
            "worker": self.worker,
            "work_hours": to_float(self.work_hours),
            "standard_work_hours": to_float(self.standard_work_hours),
            "hours_deviation_ratio": self.hours_deviation_ratio,
            "hours_deviation_hours": self.hours_deviation_hours,
            "hours_deviated": self.hours_deviated,
            "materials_deviated": self.materials_deviated,
            "has_deviation": self.has_deviation,
            "weather": self.weather,
            "weather_label": WEATHER.label(self.weather) if self.weather else None,
            "quality_result": self.quality_result,
            "quality_result_label": QUALITY_RESULT.label(self.quality_result),
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["materials"] = self.materials
            data["common_materials"] = self.common_material_list
            # 任务类型标准被调整时，仍回退展示当前字典中的常用材料
            current_standard = TASK_TYPE_STANDARDS.get(self.task_type) if self.task_type else None
            data["standard_common_materials"] = (
                list(current_standard["common_materials"]) if current_standard else []
            )
            data["deviation_reason"] = self.deviation_reason
            data["issue_found"] = self.issue_found
            data["remark"] = self.remark
            data["replacements"] = [item.to_dict() for item in self.replacements]
        return data
