/**
 * 养护记录标准值偏差判定（与后端 constants.py 阈值保持一致）。
 */

export const WORK_HOURS_DEVIATION_RATIO = 0.3
export const WORK_HOURS_DEVIATION_MIN_HOURS = 1

const NO_MATERIAL_TOKENS = new Set(['无', '没有', '无材料', '未使用', '未使用材料', '/', '-', 'none', '无。'])

/** 工时偏差比例：(实际 - 标准) / 标准；缺值返回 null。 */
export function hoursDeviationRatio(actual, standard) {
  const actualNumber = Number(actual)
  const standardNumber = Number(standard)
  if (!Number.isFinite(actualNumber) || !Number.isFinite(standardNumber) || standardNumber <= 0) {
    return null
  }
  return (actualNumber - standardNumber) / standardNumber
}

/** 实际工时相对标准是否偏差较大：比例与绝对小时数同时超过阈值。 */
export function isHoursDeviated(actual, standard) {
  const ratio = hoursDeviationRatio(actual, standard)
  if (ratio === null) return false
  return Math.abs(ratio) >= WORK_HOURS_DEVIATION_RATIO
    && Math.abs(Number(actual) - Number(standard)) >= WORK_HOURS_DEVIATION_MIN_HOURS
}

/** 把材料文本拆成条目，兼容顿号、逗号、分号等分隔符。 */
export function splitMaterials(materialsText) {
  if (!materialsText) return []
  return String(materialsText)
    .replace(/[、，；;,]/g, '\n')
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

/** 实际使用材料与常用材料完全无交集即判为材料偏差；未使用材料或常用清单为空时不判定。 */
export function isMaterialsDeviated(materialsText, commonMaterials) {
  if (!commonMaterials || commonMaterials.length === 0) return false
  const used = splitMaterials(materialsText)
  if (used.length === 0) return false
  if (used.every((item) => NO_MATERIAL_TOKENS.has(item.toLowerCase()))) return false
  const common = commonMaterials.map((item) => item.trim()).filter(Boolean)
  return !used.some((item) => common.some((token) => token.includes(item) || item.includes(token)))
}
