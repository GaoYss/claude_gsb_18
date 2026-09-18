import { defineStore } from 'pinia'

import { metaApi } from '@/api'

/** 业务字典与任务类型标准缓存：后端 /meta 是唯一数据源，前端不重复维护。 */
export const useMetaStore = defineStore('meta', {
  state: () => ({
    enums: {},
    loaded: false,
    pending: null,
    standards: {},
    standardsLoaded: false,
    standardsPending: null,
  }),
  getters: {
    options: (state) => (group) => state.enums[group] || [],
    standard: (state) => (taskType) => state.standards[taskType] || null,
  },
  actions: {
    async ensureLoaded() {
      if (this.loaded) return this.enums
      if (!this.pending) {
        this.pending = metaApi
          .getEnums()
          .then((data) => {
            this.enums = data?.enums || {}
            this.loaded = true
            return this.enums
          })
          .finally(() => {
            this.pending = null
          })
      }
      return this.pending
    },
    async ensureStandardsLoaded() {
      if (this.standardsLoaded) return this.standards
      if (!this.standardsPending) {
        this.standardsPending = metaApi
          .getTaskStandards()
          .then((data) => {
            const list = data?.standards || []
            this.standards = Object.fromEntries(list.map((item) => [item.task_type, item]))
            this.standardsLoaded = true
            return this.standards
          })
          .finally(() => {
            this.standardsPending = null
          })
      }
      return this.standardsPending
    },
    label(group, value) {
      if (value === null || value === undefined || value === '') return '-'
      const option = (this.enums[group] || []).find((item) => item.value === value)
      return option ? option.label : value
    },
  },
})
