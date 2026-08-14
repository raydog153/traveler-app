<template>
  <Modal :title="isEdit ? 'Edit fill-up' : 'Add fill-up'" :error="error || scanError" @close="$emit('close')">
    <div v-if="showUploadStep" class="upload-step">
      <p class="upload-hint">
        Upload a photo of the odometer to prefill the mileage, date, and location — or skip and enter everything by
        hand.
      </p>
      <label class="btn" :class="{ disabled: scanning }">
        {{ scanning ? 'Scanning…' : 'Upload photo' }}
        <input type="file" accept="image/*" capture="environment" :disabled="scanning" @change="onFileSelected" />
      </label>
      <button type="button" class="btn secondary" :disabled="scanning" @click="showUploadStep = false">
        Skip / enter manually
      </button>
    </div>
    <form v-else @submit.prevent="onSubmit">
      <p v-if="scanWarnings.length" class="scan-warnings">Couldn't read from photo: {{ scanWarnings.join(', ') }}</p>
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
        <p v-if="form.gps_latitude != null && form.gps_longitude != null" class="gps-hint">
          📍 GPS from photo: {{ form.gps_latitude.toFixed(5) }}, {{ form.gps_longitude.toFixed(5) }}
        </p>
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
import { computed, reactive, ref } from 'vue'
import { api } from '../api/client'
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
        gps_latitude: props.fillup.gps_latitude ?? null,
        gps_longitude: props.fillup.gps_longitude ?? null,
      }
    : {
        date: new Date().toISOString().slice(0, 10),
        odometer_miles: null,
        gallons: null,
        price: null,
        city: '',
        notes: '',
        gps_latitude: null,
        gps_longitude: null,
      },
)

// Add mode only prompts for a photo -- edit mode goes straight to the field
// form, since re-scanning an existing fill-up isn't the point of this step.
const showUploadStep = ref(!isEdit.value)
const scanning = ref(false)
const scanError = ref('')
const scanWarnings = ref([])

async function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return
  scanning.value = true
  scanError.value = ''
  scanWarnings.value = []
  try {
    const result = await api.scanOdometerPhoto(file)
    if (result.odometer_miles != null) form.odometer_miles = result.odometer_miles
    if (result.date) form.date = result.date
    if (result.city) form.city = result.state ? `${result.city}, ${result.state}` : result.city
    form.gps_latitude = result.latitude ?? null
    form.gps_longitude = result.longitude ?? null
    scanWarnings.value = result.warnings || []
  } catch (err) {
    scanError.value = err.message || 'Could not process photo'
  } finally {
    scanning.value = false
    showUploadStep.value = false
  }
}

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

<style scoped>
.upload-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 8px 0 4px;
  text-align: center;
}
.upload-hint {
  color: var(--text-muted);
  font-size: 12.5px;
  margin: 0;
}
.upload-step .btn {
  position: relative;
  cursor: pointer;
}
.upload-step .btn.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.upload-step .btn input[type='file'] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}
.scan-warnings {
  color: var(--amber-text);
  font-size: 12.5px;
  margin: 0 0 12px;
}
.gps-hint {
  color: var(--text-muted);
  font-size: 12px;
  margin: 4px 0 0;
}
</style>
