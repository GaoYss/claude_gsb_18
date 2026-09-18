/**
 * 作业标准偏差判定（前端镜像）。
 *
 * 规则与后端 app/utils/deviation.py 保持 1:1，仅用于录入时的即时提示；
 * 是否允许提交最终以后端校验为准。
 */

export function hoursRange(standard) {
  const std = Number(standard)
  return [round2(std * 0.7), round2(std * 1.3)]
}

function round2(value) {
  return Math.round(value * 100) / 100
}

function isWorkHoursDeviation(workHours, standardInfo) {
  if (workHours === null || workHours === undefined || workHours === '') return false
  if (!standardInfo?.standard_hours) return false
  const actual = Number(workHours)
  const std = Number(standardInfo.standard_hours)
  if (!Number.isFinite(actual)) return false
  const absTolerance = standardInfo.hours_abs_tolerance ?? 0.5
  if (Math.abs(actual - std) <= absTolerance) return false
  const [lower, upper] = hoursRange(std)
  return actual < lower || actual > upper
}

function isMaterialsDeviation(materials, standardInfo) {
  const text = (materials || '').trim()
  if (!text) return false
  const keywords = standardInfo?.materials_keywords || []
  if (keywords.length === 0) return false
  return !keywords.some((keyword) => text.includes(keyword))
}

/**
 * 综合判定一条记录的工时/材料偏差。
 * @param {object} standard meta store 中该任务类型的作业标准（null 表示无标准）
 * @param {{task_type: string, work_hours: number|string|null, materials: string}} record
 */
export function evaluateDeviation(standard, { task_type: taskType, work_hours: workHours, materials }) {
  if (!standard) {
    return {
      taskType,
      standard: null,
      lower: null,
      upper: null,
      hoursDeviated: false,
      materialsDeviated: false,
      deviated: false,
      flags: [],
    }
  }
  const [lower, upper] = hoursRange(standard.standard_hours)
  const hoursDeviated = isWorkHoursDeviation(workHours, standard)
  const materialsDeviated = isMaterialsDeviation(materials, standard)
  const flags = []
  if (hoursDeviated) flags.push('work_hours')
  if (materialsDeviated) flags.push('materials')
  return {
    taskType,
    standard,
    lower,
    upper,
    hoursDeviated,
    materialsDeviated,
    deviated: flags.length > 0,
    flags,
  }
}

export const DEVIATION_LABELS = {
  work_hours: '工时偏差',
  materials: '材料偏差',
}
