<template>
  <el-dialog :model-value="visible" :title="detail.record_no ? `养护记录 · ${detail.record_no}` : '养护记录详情'"
             width="700px" @update:model-value="close">
    <div v-loading="loading">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="所属绿地" :span="2">
          {{ detail.green_space ? `${detail.green_space.code} ${detail.green_space.name}` : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="关联任务" :span="2">
          <span v-if="detail.task">
            {{ detail.task.task_no }} · {{ detail.task.title }}
            <EnumTag group="task_status" :value="detail.task.status" />
          </span>
          <el-tag v-else size="small" type="info" effect="plain">日常养护（未关联任务）</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="养护日期">{{ formatDate(detail.record_date) }}</el-descriptions-item>
        <el-descriptions-item label="天气">{{ detail.weather_label || '-' }}</el-descriptions-item>
        <el-descriptions-item label="作业人员">{{ detail.worker || '-' }}</el-descriptions-item>
        <el-descriptions-item label="工时">
          <span :class="{ 'deviation-text': detail.work_hours_deviation }">{{ formatHours(detail.work_hours) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="任务类型">
          <EnumTag v-if="detail.task_type" group="task_type" :value="detail.task_type"
                   :label="detail.task_type_label" />
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="标准工时">
          <template v-if="detail.standard_hours">
            {{ detail.standard_hours }} h
            <span class="cell-sub">（合理区间 {{ detail.hours_lower }}~{{ detail.hours_upper }} h）</span>
          </template>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="质量评定">
          <EnumTag group="quality_result" :value="detail.quality_result" :label="detail.quality_result_label" />
        </el-descriptions-item>
        <el-descriptions-item label="登记时间">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
        <el-descriptions-item v-if="detail.is_deviated" label="偏差类型" :span="2">
          <el-tag v-for="flag in detail.deviation_flags" :key="flag" type="danger" effect="plain"
                  size="small" class="deviation-tag">{{ deviationLabels[flag] || flag }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="作业内容" :span="2">{{ detail.work_content || '-' }}</el-descriptions-item>
        <el-descriptions-item label="使用材料" :span="2">
          <span :class="{ 'deviation-text': detail.materials_deviation }">{{ detail.materials || '-' }}</span>
        </el-descriptions-item>
        <el-descriptions-item v-if="detail.deviation_reason" label="偏差原因" :span="2">
          <span class="deviation-reason">{{ detail.deviation_reason }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="发现问题" :span="2">{{ detail.issue_found || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
      </el-descriptions>

      <div v-if="detail.replacements?.length" class="linked-replacements">
        <div class="panel-title">关联的绿植更换记录</div>
        <el-table :data="detail.replacements" size="small" border>
          <el-table-column prop="replacement_no" label="编号" width="150" />
          <el-table-column prop="plant_name" label="植株" width="120" />
          <el-table-column label="数量" width="110">
            <template #default="{ row }">{{ formatNumber(row.quantity) }} {{ row.unit_label }}</template>
          </el-table-column>
          <el-table-column label="更换原因" width="120">
            <template #default="{ row }">
              <EnumTag group="replacement_reason" :value="row.reason" :label="row.reason_label" />
            </template>
          </el-table-column>
          <el-table-column label="金额" width="120" align="right">
            <template #default="{ row }">{{ formatCurrency(row.amount) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <template #footer>
      <el-button @click="close">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'

import { maintenanceRecordApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import { formatCurrency, formatDate, formatDateTime, formatHours, formatNumber } from '@/utils/format'
import { DEVIATION_LABELS } from '@/utils/deviation'

const visible = ref(false)
const loading = ref(false)
const detail = ref({})
const deviationLabels = DEVIATION_LABELS

async function open(id) {
  visible.value = true
  loading.value = true
  try {
    detail.value = await maintenanceRecordApi.detail(id)
  } finally {
    loading.value = false
  }
}

function close() {
  visible.value = false
}

defineExpose({ open })
</script>

<style scoped>
.linked-replacements {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.panel-title {
  font-weight: 600;
}

.cell-sub {
  color: #909399;
  font-size: 12px;
}

.deviation-text {
  color: #f56c6c;
  font-weight: 600;
}

.deviation-tag {
  margin-right: 6px;
}

.deviation-reason {
  color: #e6a23c;
  font-weight: 600;
}
</style>
