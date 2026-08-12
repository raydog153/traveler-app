<template>
  <Modal :title="isEdit ? 'Edit fill-up' : 'Add fill-up'" :error="error" @close="$emit('close')">
    <form @submit.prevent="onSubmit">
      <div class="field-row">
        <div class="field">
          <label>Date</label>
          <input v-model="form.date" type="date" required />
        </div>
        <div class="field">
          <label>Odometer (miles)</label>
          <input v-model.number="form.odometer_miles" type="number" step="0.1" min="0.1" required />
        </div>
      </div>
      <div class="field-row">
        <div class="field">
          <label>Gallons</label>
          <input v-model.number="form.gallons" type="number" step="0.001" min="0.001" required />
        </div>
        <div class="field">
          <label>Price ($)</label>
          <input v-model.number="form.price" type="number" step="0.01" min="0" required />
        </div>
      </div>
      <div class="field">
        <label>City</label>
        <input v-model="form.city" type="text" placeholder="e.g. Lancaster, MA" required />
      </div>
      <div class="field">
        <label>Notes (optional)</label>
        <input v-model="form.notes" type="text" placeholder="e.g. Not a full fillup" />
      </div>
      <div class="modal-actions">
        <button type="button" class="btn secondary" @click="$emit('close')">Cancel</button>
        <button type="submit" class="btn" :disabled="submitting">
          {{ submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Save fill-up' }}
        </button>
      </div>
    </form>
  </Modal>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { useGasStore } from '../stores/gasStore'
import { useCreateForm } from '../composables/useCreateForm'
import Modal from './Modal.vue'

const props = defineProps({
  fillup: { type: Object, default: null },
})
const emit = defineEmits(['close', 'saved'])
const gasStore = useGasStore()

const isEdit = computed(() => props.fillup != null)

const form = reactive(
  props.fillup
    ? {
        date: props.fillup.date,
        odometer_miles: props.fillup.odometer_miles,
        gallons: props.fillup.gallons,
        price: props.fillup.price,
        city: props.fillup.city,
        notes: props.fillup.notes,
      }
    : {
        date: new Date().toISOString().slice(0, 10),
        odometer_miles: null,
        gallons: null,
        price: null,
        city: '',
        notes: '',
      },
)

const { submitting, error, submit } = useCreateForm((payload) =>
  isEdit.value ? gasStore.update(props.fillup.id, payload) : gasStore.create(payload),
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
