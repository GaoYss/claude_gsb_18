<template>
  <div class="page" v-loading="loading">
    <PageHeader title="养护总览" description="绿地台账、养护任务、养护记录与绿植更换的整体运行情况">
      <template #actions>
        <el-button :icon="'Refresh'" @click="load">刷新数据</el-button>
      </template>
    </PageHeader>

    <div class="stat-grid">
      <StatCard
        label="在册绿地"
        :value="formatNumber(overview.green_space.total)"
        unit="处"
        :hint="`总面积 ${formatArea(overview.green_space.total_area)}`"
        icon="MapLocation"
      />
      <StatCard
        label="未完成养护任务"
        :value="formatNumber(overview.task.open_count)"
        unit="项"
        :hint="`其中逾期 ${overview.task.overdue_count} 项，7 天内到期 ${overview.task.due_soon_count} 项`"
        :tone="overview.task.overdue_count ? 'danger' : 'default'"
        icon="Tickets"
      />
      <StatCard
        label="任务完成率"
        :value="formatPercent(overview.task.completion_rate)"
        :hint="`已完成 ${overview.task.by_status.completed} / 共 ${overview.task.total} 项`"
        tone="info"
        icon="CircleCheck"
      />
      <StatCard
        label="本月养护记录"
        :value="formatNumber(overview.record.month_count)"
        unit="条"
        :hint="`本月工时 ${formatHours(overview.record.month_work_hours)}，累计 ${formatNumber(overview.record.total)} 条`"
        icon="Notebook"
      />
      <StatCard
        label="本月绿植更换"
        :value="formatNumber(overview.replacement.month_quantity)"
        unit="株/㎡"
        :hint="`金额 ${formatCurrency(overview.replacement.month_amount)}`"
        icon="Cherry"
      />
      <StatCard
        label="累计更换投入"
        :value="formatCurrency(overview.replacement.total_amount)"
        :hint="`今年 ${formatCurrency(overview.replacement.year_amount)}，共 ${formatNumber(overview.replacement.total)} 次`"
        tone="info"
        icon="Money"
      />
      <StatCard
        label="偏差养护记录"
        :value="formatNumber(deviation.total)"
        unit="条"
        :hint="`工时偏差 ${deviation.work_hours_count} 条 · 材料偏差 ${deviation.materials_count} 条`"
        :tone="deviation.total ? 'danger' : 'default'"
        icon="Warning"
      />
    </div>

    <div class="chart-grid">
      <ChartPanel title="近半年养护记录与工时" hint="柱：记录条数，折线：工时" :option="trendChart" />
      <ChartPanel title="绿地类型分布" hint="按绿地处数" :option="typeChart" />
      <ChartPanel title="养护任务类型分布" hint="按任务条数" :option="taskTypeChart" />
      <ChartPanel title="绿植更换原因分布" hint="按更换数量" :option="reasonChart" />
    </div>

    <div class="panel deviation-panel">
      <div class="table-toolbar">
        <span class="panel-title">工时/材料偏差记录汇总</span>
        <el-link type="primary" :underline="false" @click="router.push('/records?deviated=true')">
          查看全部偏差记录
        </el-link>
      </div>
      <div class="deviation-summary">
        <span class="summary-text">
          共 <strong>{{ deviation.total }}</strong> 条偏差记录，
          工时偏差 <strong class="danger-text">{{ deviation.work_hours_count }}</strong> 条，
          材料偏差 <strong class="danger-text">{{ deviation.materials_count }}</strong> 条
        </span>
        <span v-if="deviation.by_task_type.length" class="type-tags">
          <el-tag v-for="item in deviation.by_task_type" :key="item.value" size="small" type="danger"
                  effect="plain" class="type-tag">{{ item.label }} {{ item.count }}</el-tag>
        </span>
      </div>
      <el-table :data="deviation.records" size="small" empty-text="暂无偏差记录">
        <el-table-column prop="record_no" label="记录编号" width="150" />
        <el-table-column label="绿地" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="任务类型" width="105">
          <template #default="{ row }">
            <EnumTag v-if="row.task_type" group="task_type" :value="row.task_type" :label="row.task_type_label" />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="record_date" label="养护日期" width="105" />
        <el-table-column prop="worker" label="作业人员" width="90">
          <template #default="{ row }">{{ row.worker || '-' }}</template>
        </el-table-column>
        <el-table-column label="实际/标准工时" width="130" align="right">
          <template #default="{ row }">
            <div :class="{ 'danger-text deviation-hours': row.work_hours_deviation }">
              {{ formatNumber(row.work_hours) }}
            </div>
            <div class="cell-sub">
              标准 {{ row.standard_hours }}（{{ row.hours_lower }}~{{ row.hours_upper }}）
            </div>
          </template>
        </el-table-column>
        <el-table-column label="偏差类型" width="150">
          <template #default="{ row }">
            <el-tag v-for="flag in row.deviation_flags" :key="flag" size="small" type="danger"
                    effect="plain" class="deviation-tag">{{ deviationLabels[flag] || flag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="deviation_reason" label="偏差原因" min-width="200" show-overflow-tooltip />
      </el-table>
    </div>

    <div class="dashboard-columns">
      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">逾期未完成的养护任务</span>
          <el-link type="primary" :underline="false" @click="router.push('/tasks')">
            查看全部任务
          </el-link>
        </div>
        <el-table :data="dashboard.overdue_tasks" size="small" empty-text="暂无逾期任务">
          <el-table-column prop="task_no" label="任务编号" width="150" />
          <el-table-column label="绿地" min-width="140">
            <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="title" label="任务名称" min-width="150" show-overflow-tooltip />
          <el-table-column prop="plan_date" label="计划日期" width="110" />
          <el-table-column label="逾期" width="80">
            <template #default="{ row }">
              <span class="overdue-days">{{ overdueDays(row.plan_date) }} 天</span>
            </template>
          </el-table-column>
          <el-table-column prop="executor" label="执行班组" width="110">
            <template #default="{ row }">{{ row.executor || '-' }}</template>
          </el-table-column>
        </el-table>
      </div>

      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">养护工作量排名</span>
          <span class="summary-text">按累计养护记录条数</span>
        </div>
        <el-table :data="dashboard.ranking" size="small" empty-text="暂无养护记录">
          <el-table-column type="index" label="#" width="48" />
          <el-table-column prop="name" label="绿地名称" min-width="150" show-overflow-tooltip />
          <el-table-column prop="district" label="行政区" width="90" />
          <el-table-column prop="record_count" label="养护次数" width="90" />
          <el-table-column label="累计工时" width="100">
            <template #default="{ row }">{{ formatHours(row.total_work_hours) }}</template>
          </el-table-column>
          <el-table-column label="更换量" width="100">
            <template #default="{ row }">{{ formatNumber(row.replacement_quantity) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div class="dashboard-columns">
      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">最近养护记录</span>
          <el-link type="primary" :underline="false" @click="router.push('/records')">进入养护记录</el-link>
        </div>
        <el-table :data="dashboard.recent_activity.records" size="small" empty-text="暂无养护记录">
          <el-table-column prop="record_no" label="记录编号" width="150" />
          <el-table-column label="绿地" min-width="140">
            <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="record_date" label="养护日期" width="110" />
          <el-table-column prop="work_content" label="作业内容" min-width="180" show-overflow-tooltip />
          <el-table-column label="质量评定" width="100">
            <template #default="{ row }">
              <EnumTag group="quality_result" :value="row.quality_result" />
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">最近绿植更换</span>
          <el-link type="primary" :underline="false" @click="router.push('/replacements')">
            进入更换记录
          </el-link>
        </div>
        <el-table :data="dashboard.recent_activity.replacements" size="small" empty-text="暂无更换记录">
          <el-table-column prop="replacement_no" label="编号" width="150" />
          <el-table-column label="绿地" min-width="130">
            <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="plant_name" label="植株" width="110" />
          <el-table-column label="数量" width="110">
            <template #default="{ row }">
              {{ formatNumber(row.quantity) }} {{ row.unit_label }}
            </template>
          </el-table-column>
          <el-table-column label="金额" width="120">
            <template #default="{ row }">{{ formatCurrency(row.amount) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { statisticsApi } from '@/api'
import ChartPanel from '@/components/common/ChartPanel.vue'
import EnumTag from '@/components/common/EnumTag.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import { formatArea, formatCurrency, formatHours, formatNumber, formatPercent, today } from '@/utils/format'
import { DEVIATION_LABELS } from '@/utils/deviation'

import { barOption, pieOption, trendOption } from './chartOptions'

const router = useRouter()
const loading = ref(false)
const dashboard = ref(emptyDashboard())
const deviationLabels = DEVIATION_LABELS

function emptyDashboard() {
  return {
    overview: {
      green_space: { total: 0, total_area: 0, by_status: {} },
      task: { total: 0, open_count: 0, overdue_count: 0, due_soon_count: 0, completion_rate: 0, by_status: {} },
      record: { total: 0, month_count: 0, month_work_hours: 0, total_work_hours: 0 },
      replacement: { total: 0, month_count: 0, month_quantity: 0, month_amount: 0, year_amount: 0, total_amount: 0 },
    },
    distributions: {
      green_space_by_type: [],
      task_by_type: [],
      replacement_by_reason: [],
      replacement_by_category: [],
    },
    trends: [],
    deviation: { total: 0, work_hours_count: 0, materials_count: 0, by_task_type: [], records: [] },
    ranking: [],
    overdue_tasks: [],
    upcoming_tasks: [],
    recent_activity: { records: [], replacements: [] },
  }
}

const overview = computed(() => dashboard.value.overview)
const deviation = computed(() => dashboard.value.deviation)

const trendChart = computed(() => trendOption(dashboard.value.trends || []))

const typeChart = computed(() =>
  pieOption(
    (dashboard.value.distributions.green_space_by_type || []).map((item) => ({
      name: item.label,
      value: item.count,
    })),
    { unit: '处' },
  ),
)

const taskTypeChart = computed(() =>
  barOption(
    (dashboard.value.distributions.task_by_type || []).map((item) => ({
      name: item.label,
      value: item.count,
    })),
    { unit: '项', horizontal: true },
  ),
)

const reasonChart = computed(() =>
  pieOption(
    (dashboard.value.distributions.replacement_by_reason || []).map((item) => ({
      name: item.label,
      value: item.quantity,
    })),
    { unit: '株/㎡' },
  ),
)

function overdueDays(planDate) {
  if (!planDate) return 0
  const diff = new Date(today()) - new Date(planDate)
  return Math.max(Math.round(diff / 86400000), 0)
}

async function load() {
  loading.value = true
  try {
    dashboard.value = await statisticsApi.dashboard({ months: 6 })
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.dashboard-columns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 16px;
}

.deviation-panel {
  margin: 16px 0;
}

.deviation-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}

.type-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.type-tag {
  margin: 0;
}

.panel-title {
  font-weight: 600;
}

.danger-text {
  color: #f56c6c;
  font-weight: 600;
}

.deviation-hours {
  line-height: 1.4;
}

.deviation-tag {
  margin: 0 4px 2px 0;
}

.cell-sub {
  color: #909399;
  font-size: 12px;
}

.overdue-days {
  color: #f56c6c;
  font-weight: 600;
}
</style>
