<template>
  <Modal :title="isEdit ? 'Edit maintenance record' : 'Add maintenance record'" :error="error" @close="$emit('close')">
    <form @submit.prevent="onSubmit">
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
          <label>Place</label>
          <input v-model="form.place" type="text" placeholder="e.g. Lancaster, MA" required />
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
          {{ submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Save record' }}
        </button>
      </div>
    </form>
  </Modal>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { useMaintenanceStore } from '../stores/maintenanceStore'
import { useCreateForm } from '../composables/useCreateForm'
import Modal from './Modal.vue'

const props = defineProps({
  record: { type: Object, default: null },
})
const emit = defineEmits(['close', 'saved'])
const maintenanceStore = useMaintenanceStore()

const isEdit = computed(() => props.record != null)

const form = reactive(
  props.record
    ? {
        date: props.record.date,
        expense: props.record.expense,
        place: props.record.place,
        odometer_miles: props.record.odometer_miles,
        vendor: props.record.vendor,
        cost: props.record.cost,
      }
    : {
        date: new Date().toISOString().slice(0, 10),
        expense: '',
        place: '',
        odometer_miles: null,
        vendor: '',
        cost: null,
      },
)

const { submitting, error, submit } = useCreateForm((payload) =>
  isEdit.value ? maintenanceStore.update(props.record.id, payload) : maintenanceStore.create(payload),
)

function onSubmit() {
  submit(
    { ...form },
    {
      onSuccess: (saved) => {
        emit('saved', saved)
        emit('close')
      },
    },
  )
}
</script>
