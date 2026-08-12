import { defineStore } from 'pinia'
import { api } from '../api/client'

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    summary: null,
    loaded: false,
    loading: false,
    error: null,
  }),
  actions: {
    async fetchAll({ force = false } = {}) {
      if (this.loaded && !force) return
      this.loading = true
      this.error = null
      try {
        this.summary = await api.dashboardSummary()
        this.loaded = true
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    },
  },
})
