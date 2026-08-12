import { api } from '../api/client'
import { createResourceStore } from './resourceStore'

export const useGasStore = createResourceStore('gas', {
  stateKey: 'fillups',
  fetchFn: api.listFillups,
  createFn: api.createFillup,
  updateFn: api.updateFillup,
  deleteFn: api.deleteFillup,
})
