<template>
  <Modal :title="title" :error="error" @close="$emit('cancel')">
    <p class="confirm-message">{{ message }}</p>
    <div class="modal-actions">
      <button type="button" class="btn secondary" @click="$emit('cancel')">Cancel</button>
      <button type="button" class="btn danger" :disabled="busy" @click="$emit('confirm')">
        {{ busy ? 'Deleting…' : confirmLabel }}
      </button>
    </div>
  </Modal>
</template>

<script setup>
import Modal from './Modal.vue'

defineProps({
  title: { type: String, default: 'Are you sure?' },
  message: { type: String, required: true },
  confirmLabel: { type: String, default: 'Delete' },
  busy: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
defineEmits(['confirm', 'cancel'])
</script>

<style scoped>
.confirm-message {
  font-size: 13.5px;
  color: var(--text-primary);
  margin: 0;
}
</style>
