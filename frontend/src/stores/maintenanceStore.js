import { api } from '../api/client'
import { createResourceStore } from './resourceStore'

export const useMaintenanceStore = createResourceStore('maintenance', {
  stateKey: 'records',
  fetchFn: api.listMaintenance,
  createFn: api.createMaintenance,
})
