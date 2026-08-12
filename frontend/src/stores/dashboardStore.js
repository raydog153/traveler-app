import { api } from '../api/client'
import { createResourceStore } from './resourceStore'

export const useDashboardStore = createResourceStore('dashboard', {
  stateKey: 'summary',
  fetchFn: api.dashboardSummary,
})
