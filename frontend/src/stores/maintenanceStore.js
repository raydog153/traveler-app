import { defineStore } from 'pinia'
import { api } from '../api/client'

export const useMaintenanceStore = defineStore('maintenance', {
  state: () => ({
    records: [],
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
        this.records = await api.listMaintenance()
        this.loaded = true
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    },
    async create(payload) {
      const created = await api.createMaintenance(payload)
      this.records.push(created)
      return created
    },
  },
})
