import { api } from '../api/client'
import { createResourceStore } from './resourceStore'

export const useMapStore = createResourceStore('map', {
  stateKey: 'routeData',
  fetchFn: api.mapRoutes,
})
