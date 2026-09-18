<template>
  <el-dialog :model-value="visible" :title="isEdit ? `编辑养护记录 · ${form.record_no}` : '录入养护记录'"
             width="760px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
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
      <el-form-item label="任务类型" :error="fieldErrors.task_type">
        <el-select v-model="form.task_type" clearable placeholder="选择任务类型后带出作业标准"
                   :disabled="!!form.task_id" style="width: 100%">
          <el-option v-for="item in taskTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <div class="form-hint">
          <span v-if="form.task_id">已关联任务，任务类型以任务为准，不可单独修改。</span>
          <span v-else>日常巡查类记录可不选；选择后自动带出标准工时与常用材料。</span>
        </div>
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
          <el-form-item label="作业人员" :error="fieldErrors.worker">
            <el-input v-model="form.worker" placeholder="如：王海涛" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="工时" :error="fieldErrors.work_hours">
            <el-input-number v-model="form.work_hours" :min="0" :max="1000" :precision="1"
                             :controls="false" placeholder="单位：小时" style="width: 100%" />
            <div v-if="deviation.standard" class="form-hint" :class="{ 'hint-error': deviation.hoursDeviated }">
              标准 {{ deviation.standard.standard_hours }}h，合理区间约 {{ deviation.lower }}~{{ deviation.upper }}h
              （±{{ Math.round(deviation.standard.hours_tolerance_ratio * 100) }}%，{{ deviation.standard.hours_abs_tolerance }}h 容差）
            </div>
            <el-alert v-if="deviation.hoursDeviated" class="deviation-alert" type="error" :closable="false"
                      title="实际工时偏离合理区间，请在下方填写偏差原因" />
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
            <div v-if="deviation.standard" class="form-hint" :class="{ 'hint-error': deviation.materialsDeviated }">
              常用材料：{{ deviation.standard.materials_default }}
            </div>
            <el-alert v-if="deviation.materialsDeviated" class="deviation-alert" type="error" :closable="false"
                      title="未使用该类型的常用材料/药剂，请确认并在下方填写偏差原因" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item v-if="deviation.deviated" label="偏差原因" prop="deviation_reason"
                    :error="fieldErrors.deviation_reason" required>
        <el-input v-model="form.deviation_reason" type="textarea" :rows="2" maxlength="1000"
                  show-word-limit placeholder="请说明实际工时/材料与作业标准偏差较大的原因" />
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
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { maintenanceRecordApi, maintenanceTaskApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import TaskSelect from '@/components/common/TaskSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useMetaStore } from '@/stores/meta'
import { evaluateDeviation } from '@/utils/deviation'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: qualityOptions } = useEnumOptions('quality_result')
const { options: weatherOptions } = useEnumOptions('weather')
const { options: taskTypeOptions } = useEnumOptions('task_type')
const metaStore = useMetaStore()

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const taskPreset = ref(null)
const suppressMaterialAutofill = ref(false)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const deviation = computed(() =>
  evaluateDeviation(metaStore.standard(form.task_type), {
    task_type: form.task_type,
    work_hours: form.work_hours,
    materials: form.materials,
  }),
)

const rules = {
  record_date: [{ required: true, message: '请选择养护日期', trigger: 'change' }],
  work_content: [{ required: true, message: '请输入作业内容', trigger: 'blur' }],
}

function emptyForm() {
  return {
    record_no: '',
    green_space_id: null,
    task_id: null,
    task_type: null,
    record_date: today(),
    work_content: '',
    worker: '',
    work_hours: null,
    weather: '',
    materials: '',
    deviation_reason: '',
    quality_result: 'qualified',
    issue_found: '',
    remark: '',
  }
}

async function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  taskPreset.value = null
  editingId.value = row?.id ?? null

  // 编辑时先拉详情：列表行不含材料全文与偏差原因，直接回显会误清空
  suppressMaterialAutofill.value = true
  if (row?.id) {
    const detail = await maintenanceRecordApi.detail(row.id)
    Object.keys(form).forEach((key) => {
      if (detail[key] !== undefined && detail[key] !== null) form[key] = detail[key]
    })
    spacePreset.value = detail.green_space || null
    taskPreset.value = detail.task ? { ...detail.task, id: detail.task_id } : null
  } else if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    spacePreset.value = row.green_space || null
    taskPreset.value = row.task ? { ...row.task, id: row.task_id } : null
  }
  visible.value = true
  await nextTick()
  suppressMaterialAutofill.value = false
}

function close() {
  visible.value = false
}

function onGreenSpaceChange() {
  form.task_id = null
  taskPreset.value = null
}

async function onTaskChange(taskId) {
  if (!taskId) {
    // 解除任务关联：释放任务类型锁定，保留当前值供手动调整
    form.task_type = form.task_type || null
    return
  }
  const task = await maintenanceTaskApi.detail(taskId).catch(() => null)
  if (task?.green_space) {
    form.green_space_id = task.green_space_id
    spacePreset.value = task.green_space
    taskPreset.value = { id: task.id, task_no: task.task_no, title: task.title, status: task.status }
    form.task_type = task.task_type
  }
}

// 任务类型变化且材料尚未填写时，自动带出该类型的常用材料
watch(
  () => form.task_type,
  (taskType) => {
    if (suppressMaterialAutofill.value) return
    if (form.materials && form.materials.trim()) return
    form.materials = taskType ? metaStore.standard(taskType)?.materials_default || '' : ''
  },
)

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  if (!form.green_space_id && !form.task_id) {
    fieldErrors.value = { green_space_id: '请选择所属绿地或关联养护任务' }
    return
  }
  if (deviation.value.deviated && !(form.deviation_reason || '').trim()) {
    fieldErrors.value = { deviation_reason: '实际工时或使用材料与作业标准偏差较大，请填写偏差原因' }
    return
  }
  submitting.value = true
  fieldErrors.value = {}
  const payload = { ...form }
  delete payload.record_no
  if (!payload.record_no) delete payload.record_no
  if (!payload.task_id) payload.task_id = null
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
  margin-top: 2px;
}

.hint-error {
  color: #f56c6c;
}

.deviation-alert {
  margin-top: 4px;
  padding: 4px 8px;
}
</style>
