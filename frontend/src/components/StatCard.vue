<template>
  <div class="stat">
    <div class="label">{{ label }}</div>
    <div class="value" :class="cls">{{ value }}</div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: String, required: true },
  cls: { type: String, default: '' },
})
</script>

<style scoped>
.stat {
  background: var(--panel);
  border: 1px solid var(--grid);
  border-radius: 12px;
  padding: 14px 16px;
}
.label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted);
  margin-bottom: 6px;
}
.value {
  font-size: 21px;
  font-weight: 700;
}
.value.accent {
  color: var(--accent);
}
.value.accent2 {
  color: var(--accent2);
}
.value.accent3 {
  color: var(--accent3);
}
</style>
