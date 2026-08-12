<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-panel">
      <h2>{{ title }}</h2>
      <p v-if="error" class="form-error">{{ error }}</p>
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  error: { type: String, default: '' },
})
defineEmits(['close'])
</script>
