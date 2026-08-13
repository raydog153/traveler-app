<template>
  <div class="pill-tabs">
    <button
      v-for="t in tabs"
      :key="t.key"
      type="button"
      class="pill-tab"
      :class="{ active: t.key === activeKey }"
      @click="$emit('update:activeKey', t.key)"
    >
      {{ t.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  tabs: { type: Array, required: true }, // [{ key, label }]
  activeKey: { type: String, required: true },
})
defineEmits(['update:activeKey'])
</script>

<style scoped>
.pill-tabs {
  display: inline-flex;
  background: oklch(0.965 0.004 255);
  padding: 4px;
  border-radius: 11px;
  gap: 3px;
}
.pill-tab {
  border: none;
  background: transparent;
  color: var(--text-muted);
  padding: 8px 15px;
  border-radius: 8px;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
}
.pill-tab.active {
  background: #fff;
  color: var(--text-primary);
  box-shadow: var(--shadow-tab);
}
</style>
