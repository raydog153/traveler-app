import { defineStore } from 'pinia'
import { api } from '../api/client'

export const useGasStore = defineStore('gas', {
  state: () => ({
    fillups: [],
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
        this.fillups = await api.listFillups()
        this.loaded = true
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    },
    async create(payload) {
      const created = await api.createFillup(payload)
      this.fillups.push(created)
      return created
    },
  },
})
