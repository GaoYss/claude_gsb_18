import { defineStore } from 'pinia'

import { metaApi } from '@/api'

/** 业务字典缓存：后端 /meta/enums 是唯一数据源，前端不重复维护枚举。 */
export const useMetaStore = defineStore('meta', {
  state: () => ({
    enums: {},
    taskStandards: {},
    loaded: false,
    pending: null,
  }),
  getters: {
    options: (state) => (group) => state.enums[group] || [],
    standard: (state) => (taskType) => state.taskStandards[taskType] || null,
  },
  actions: {
    async ensureLoaded() {
      if (this.loaded) return this.enums
      if (!this.pending) {
        this.pending = metaApi
          .getEnums()
          .then((data) => {
            this.enums = data?.enums || {}
            this.taskStandards = data?.task_standards || {}
            this.loaded = true
            return this.enums
          })
          .finally(() => {
            this.pending = null
          })
      }
      return this.pending
    },
    label(group, value) {
      if (value === null || value === undefined || value === '') return '-'
      const option = (this.enums[group] || []).find((item) => item.value === value)
      return option ? option.label : value
    },
  },
})
