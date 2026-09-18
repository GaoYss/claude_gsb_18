<template>
  <el-dialog :model-value="visible" :title="isEdit ? `编辑养护记录 · ${form.record_no}` : '录入养护记录'"
             width="760px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px" v-loading="detailLoading">
      <el-form-item label="所属绿地" prop="green_space_id" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset"
                          placeholder="选择绿地（可与右侧任务二选一）"
                          @update:model-value="onGreenSpaceChange" />
      </el-form-item>
      <el-form-item label="关联养护任务" :error="fieldErrors.task_id">
        <TaskSelect v-model="form.task_id" :green-space-id="form.green_space_id" :preset="taskPreset"
                    @update:model-value="onTaskChange" />
        <div class="form-hint">关联任务后，绿地与任务类型自动跟随任务；任务状态会随本记录的评定结果自动流转。</div>
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="养护日期" prop="record_date" :error="fieldErrors.record_date">
            <el-date-picker v-model="form.record_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择养护日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="天气" :error="fieldErrors.weather">
            <el-select v-model="form.weather" clearable placeholder="选择天气" style="width: 100%">
              <el-option v-for="item in weatherOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="任务类型" :error="fieldErrors.task_type">
            <el-select v-model="form.task_type" clearable :disabled="!!form.task_id"
                        placeholder="选择任务类型以带出标准" style="width: 100%"
                        @update:model-value="onTaskTypeChange">
              <el-option v-for="item in taskTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <div v-if="form.task_id" class="form-hint">已关联任务，任务类型不可修改</div>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="作业人员" :error="fieldErrors.worker">
            <el-input v-model="form.worker" placeholder="如：王海涛" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="工时" :error="fieldErrors.work_hours">
            <el-input-number v-model="form.work_hours" :min="0" :max="1000" :precision="1"
                             :controls="false" placeholder="单位：小时" style="width: 100%" />
            <div v-if="standardHours" class="form-hint" :class="{ 'hint-danger': hoursDeviated }">
              标准工时 {{ standardHours }}h<template v-if="hoursRatio !== null">
                ，偏差 <span :class="hoursDeviated ? 'text-danger' : ''">{{ formatPercent(hoursRatio) }}</span>
                （{{ hoursDelta >= 0 ? '+' : '' }}{{ hoursDelta }}h）
              </template>
              <span v-if="hoursDeviated" class="text-danger"> · 超出允许偏差</span>
            </div>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="作业内容" prop="work_content" :error="fieldErrors.work_content">
        <el-input v-model="form.work_content" type="textarea" :rows="3" maxlength="4000"
                  placeholder="如：修剪香樟下垂枝 32 株，清运枝条 2 车" />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="质量评定" :error="fieldErrors.quality_result">
            <el-select v-model="form.quality_result" style="width: 100%">
              <el-option v-for="item in qualityOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="使用材料/药剂" :error="fieldErrors.materials">
            <el-input v-model="form.materials" placeholder="如：复合肥 180kg" maxlength="1000" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item v-if="commonMaterials.length" label="常用材料">
        <div class="material-tags">
          <el-tag v-for="item in commonMaterials" :key="item" class="material-tag"
                  :type="isMaterialUsed(item) ? 'success' : 'info'" :effect="isMaterialUsed(item) ? 'dark' : 'plain'"
                  @click="appendMaterial(item)">
            {{ item }}
          </el-tag>
          <span class="form-hint">点击标签填入；当前材料不在常用范围内会提示材料偏差。</span>
        </div>
      </el-form-item>

      <el-alert v-if="hasDeviation" type="warning" :closable="false" show-icon class="deviation-alert"
                title="实际值与标准值偏差较大，请填写偏差原因后再保存">
        <template #default>
          <ul class="deviation-list">
            <li v-if="hoursDeviated">
              工时 {{ form.work_hours }}h 与标准工时 {{ standardHours }}h
              偏差 {{ formatPercent(hoursRatio) }}（超出 ±{{ Math.round(RATIO * 100) }}% 且不少于 1h）
            </li>
            <li v-if="materialsDeviated">使用材料「{{ form.materials }}」不在该任务类型常用材料范围内</li>
          </ul>
        </template>
      </el-alert>
      <el-form-item v-if="hasDeviation" label="偏差原因" prop="deviation_reason"
                    :error="fieldErrors.deviation_reason">
        <el-input v-model="form.deviation_reason" type="textarea" :rows="2" maxlength="1000"
                  placeholder="请说明实际工时/材料偏离标准的具体原因，如天气、现场状况、作业范围变化等" />
      </el-form-item>

      <el-form-item label="发现问题" :error="fieldErrors.issue_found">
        <el-input v-model="form.issue_found" type="textarea" :rows="2" maxlength="2000"
                  placeholder="巡查或作业中发现的问题及处理情况" />
      </el-form-item>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { maintenanceRecordApi, maintenanceTaskApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import TaskSelect from '@/components/common/TaskSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useMetaStore } from '@/stores/meta'
import {
  WORK_HOURS_DEVIATION_RATIO as RATIO,
  hoursDeviationRatio,
  isHoursDeviated,
  isMaterialsDeviated,
  splitMaterials,
} from '@/utils/deviation'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const metaStore = useMetaStore()
metaStore.ensureLoaded()
metaStore.ensureStandardsLoaded()

const { options: qualityOptions } = useEnumOptions('quality_result')
const { options: weatherOptions } = useEnumOptions('weather')
const taskTypeOptions = computed(() => metaStore.options('task_type'))

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const detailLoading = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const taskPreset = ref(null)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  record_date: [{ required: true, message: '请选择养护日期', trigger: 'change' }],
  work_content: [{ required: true, message: '请输入作业内容', trigger: 'blur' }],
}

function emptyForm() {
  return {
    record_no: '',
    green_space_id: null,
    task_id: null,
    task_type: '',
    record_date: today(),
    work_content: '',
    worker: '',
    work_hours: null,
    weather: '',
    materials: '',
    quality_result: 'qualified',
    deviation_reason: '',
    issue_found: '',
    remark: '',
  }
}

// 标准值随任务类型带出
const currentStandard = computed(() => metaStore.standard(form.task_type))
const standardHours = computed(() => currentStandard.value?.standard_work_hours ?? null)
const commonMaterials = computed(() => currentStandard.value?.common_materials || [])

const hoursRatio = computed(() => hoursDeviationRatio(form.work_hours, standardHours.value))
const hoursDelta = computed(() => {
  if (hoursRatio.value === null) return 0
  return Math.round((Number(form.work_hours) - Number(standardHours.value)) * 10) / 10
})
const hoursDeviated = computed(() => isHoursDeviated(form.work_hours, standardHours.value))
const materialsDeviated = computed(() =>
  isMaterialsDeviated(form.materials, commonMaterials.value),
)
const hasDeviation = computed(() => hoursDeviated.value || materialsDeviated.value)

function formatPercent(ratio) {
  return `${ratio > 0 ? '+' : ''}${Math.round(ratio * 100)}%`
}

function isMaterialUsed(item) {
  return splitMaterials(form.materials).some((used) => used.includes(item) || item.includes(used))
}

function appendMaterial(item) {
  const used = splitMaterials(form.materials)
  if (used.some((usedItem) => usedItem.includes(item) || item.includes(usedItem))) return
  form.materials = used.length ? `${used.join('、')}、${item}` : item
}

async function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  taskPreset.value = null
  editingId.value = row?.id ?? null
  visible.value = true

  if (!row?.id) return

  // 列表行不含材料/问题等明细字段，编辑时拉取完整详情，避免覆盖丢失
  let detail = row
  if (row.materials === undefined || row.issue_found === undefined) {
    detailLoading.value = true
    try {
      detail = await maintenanceRecordApi.detail(row.id)
    } finally {
      detailLoading.value = false
    }
  }
  Object.keys(form).forEach((key) => {
    if (detail[key] !== undefined && detail[key] !== null) form[key] = detail[key]
  })
  spacePreset.value = detail.green_space || null
  taskPreset.value = detail.task ? { ...detail.task, id: detail.task_id } : null
}

function close() {
  visible.value = false
}

function onGreenSpaceChange() {
  form.task_id = null
  taskPreset.value = null
}

function onTaskTypeChange() {
  // 切换任务类型后由 computed 重新带出标准；偏差原因留待提交时按新偏差判定
}

async function onTaskChange(taskId) {
  if (!taskId) {
    form.task_type = ''
    return
  }
  const task = await maintenanceTaskApi.detail(taskId).catch(() => null)
  if (task?.green_space) {
    form.green_space_id = task.green_space_id
    spacePreset.value = task.green_space
    taskPreset.value = { id: task.id, task_no: task.task_no, title: task.title, status: task.status }
    // 关联任务时任务类型跟随任务，自动带出对应标准
    form.task_type = task.task_type || ''
  }
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  if (!form.green_space_id && !form.task_id) {
    fieldErrors.value = { green_space_id: '请选择所属绿地或关联养护任务' }
    return
  }
  if (hasDeviation.value && !form.deviation_reason.trim()) {
    fieldErrors.value = { deviation_reason: '实际值与标准值偏差较大，请填写偏差原因' }
    ElMessage.warning('实际工时/材料与标准偏差较大，请填写偏差原因')
    return
  }
  submitting.value = true
  fieldErrors.value = {}
  const payload = { ...form }
  delete payload.record_no
  if (!payload.task_id) payload.task_id = null
  if (!payload.task_type) payload.task_type = null
  if (!hasDeviation.value) payload.deviation_reason = null
  try {
    if (isEdit.value) {
      await maintenanceRecordApi.update(editingId.value, payload)
      ElMessage.success('养护记录已更新')
    } else {
      await maintenanceRecordApi.create(payload)
      ElMessage.success('养护记录录入成功')
    }
    emit('saved')
    close()
  } catch (error) {
    fieldErrors.value = error?.details || {}
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.form-hint {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}

.hint-danger,
.text-danger {
  color: #e6a23c;
}

.text-danger {
  font-weight: 600;
}

.material-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.material-tag {
  cursor: pointer;
}

.deviation-alert {
  margin-bottom: 18px;
}

.deviation-list {
  margin: 4px 0 0;
  padding-left: 18px;
}
</style>
