<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-panel">
      <h2>Add maintenance record</h2>
      <p v-if="error" class="form-error">{{ error }}</p>
      <form @submit.prevent="submit">
        <div class="field-row">
          <div class="field">
            <label>Date</label>
            <input v-model="form.date" type="date" required />
          </div>
          <div class="field">
            <label>Cost ($)</label>
            <input v-model.number="form.cost" type="number" step="0.01" required />
          </div>
        </div>
        <div class="field">
          <label>Expense</label>
          <input v-model="form.expense" type="text" placeholder="e.g. Front brake rotors" required />
        </div>
        <div class="field-row">
          <div class="field">
            <label>Place (optional)</label>
            <input v-model="form.place" type="text" placeholder="e.g. Lancaster, MA" />
          </div>
          <div class="field">
            <label>Vendor (optional)</label>
            <input v-model="form.vendor" type="text" />
          </div>
        </div>
        <div class="field">
          <label>Odometer (optional)</label>
          <input v-model.number="form.odometer_miles" type="number" step="0.1" min="0" />
        </div>
        <div class="modal-actions">
          <button type="button" class="btn secondary" @click="$emit('close')">Cancel</button>
          <button type="submit" class="btn" :disabled="submitting">
            {{ submitting ? 'Saving…' : 'Save record' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useMaintenanceStore } from '../stores/maintenanceStore'

const emit = defineEmits(['close', 'created'])
const maintenanceStore = useMaintenanceStore()

const form = reactive({
  date: new Date().toISOString().slice(0, 10),
  expense: '',
  place: '',
  odometer_miles: null,
  vendor: '',
  cost: null,
})

const submitting = ref(false)
const error = ref('')

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    const created = await maintenanceStore.create({ ...form })
    emit('created', created)
    emit('close')
  } catch (err) {
    error.value = err.message
  } finally {
    submitting.value = false
  }
}
</script>
