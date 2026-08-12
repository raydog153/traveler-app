import { ref } from 'vue'

/** Shared submitting/error state + submit wrapper for the entry-form modals. */
export function useCreateForm(createFn) {
  const submitting = ref(false)
  const error = ref('')

  async function submit(payload, { onSuccess } = {}) {
    submitting.value = true
    error.value = ''
    try {
      const created = await createFn(payload)
      onSuccess?.(created)
    } catch (err) {
      error.value = err.message
    } finally {
      submitting.value = false
    }
  }

  return { submitting, error, submit }
}
