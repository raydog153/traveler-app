import { defineStore } from 'pinia'

/**
 * Shared shape for the app's four data stores: fetch-once-and-cache with a
 * loading/error flag, an invalidate() to force a refetch on next visit, and
 * optional create()/update()/remove() for the two stores that support
 * editing records.
 */
export function createResourceStore(id, { stateKey, fetchFn, createFn, updateFn, deleteFn }) {
  // Tracks an in-flight fetchAll() promise per store instance, outside Pinia
  // state (it's not serializable and shouldn't be reactive). Several
  // components can call fetchAll() independently on mount (e.g. App.vue's
  // header and a routed view both want the same data) -- without this, each
  // call passes the `this.loaded` guard before the first one resolves and
  // fires its own duplicate network request.
  let inFlight = null

  return defineStore(id, {
    state: () => ({
      [stateKey]: createFn ? [] : null,
      loaded: false,
      loading: false,
      error: null,
    }),
    actions: {
      // Resolves once data is loaded (or a load attempt has failed) --
      // never rejects, so callers that want to react to failure should read
      // `error`/`loaded` after it resolves rather than try/catch.
      async fetchAll({ force = false } = {}) {
        if (this.loaded && !force) return
        if (inFlight && !force) return inFlight
        this.loading = true
        this.error = null
        inFlight = (async () => {
          try {
            this[stateKey] = await fetchFn()
            this.loaded = true
          } catch (err) {
            this.error = err.message
          } finally {
            this.loading = false
            inFlight = null
          }
        })()
        return inFlight
      },
      // Marks the cache stale so the next fetchAll() call re-requests it,
      // without forcing an immediate fetch -- for other stores' data that
      // this action affects but that isn't currently being viewed.
      invalidate() {
        this.loaded = false
      },
      ...(createFn && {
        async create(payload) {
          const created = await createFn(payload)
          this[stateKey].push(created)
          return created
        },
      }),
      ...(updateFn && {
        async update(id, payload) {
          const updated = await updateFn(id, payload)
          const idx = this[stateKey].findIndex((r) => r.id === id)
          if (idx !== -1) this[stateKey][idx] = updated
          return updated
        },
      }),
      ...(deleteFn && {
        async remove(id) {
          await deleteFn(id)
          this[stateKey] = this[stateKey].filter((r) => r.id !== id)
        },
      }),
    },
  })
}
