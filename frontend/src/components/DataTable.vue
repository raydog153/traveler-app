<template>
  <div>
    <div class="controls">
      <input v-model="search" type="text" class="search" placeholder="Search this table..." />
      <span class="count">{{ sortedRows.length }} row{{ sortedRows.length !== 1 ? 's' : '' }}</span>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th
              v-for="c in columns"
              :key="c.key"
              @click="sortBy(c.key)"
              :class="{ sorted: sortKey === c.key, asc: sortKey === c.key && sortDir === -1 }"
            >
              {{ c.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in sortedRows" :key="row.id" :class="{ excluded: excludedPredicate && excludedPredicate(row) }">
            <td v-for="c in columns" :key="c.key" :class="{ num: c.num, 'notes-cell': c.notes }">
              <template v-if="c.badge">
                <span v-if="c.badge(row)" class="badge" :class="c.badge(row).cls">{{ c.badge(row).text }}</span>
              </template>
              <template v-else>
                {{ c.fmt ? c.fmt(row[c.key]) : row[c.key] }}
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, required: true },
  // Purely visual: dims a row when this returns true. Filtering rows in/out
  // (e.g. a "hide excluded" toggle) is the caller's concern, not this
  // generic table's -- pass already-filtered `rows` for that.
  excludedPredicate: { type: Function, default: null },
  defaultSortKey: { type: String, default: 'date' },
})

const search = ref('')
const sortKey = ref(props.defaultSortKey)
const sortDir = ref(1)

function sortBy(key) {
  if (sortKey.value === key) {
    sortDir.value *= -1
  } else {
    sortKey.value = key
    sortDir.value = 1
  }
}

const filteredRows = computed(() => {
  let rows = props.rows
  if (search.value.trim()) {
    const q = search.value.trim().toLowerCase()
    rows = rows.filter((r) => Object.values(r).some((v) => v != null && String(v).toLowerCase().includes(q)))
  }
  return rows
})

const sortedRows = computed(() => {
  const rows = [...filteredRows.value]
  const key = sortKey.value
  const dir = sortDir.value
  rows.sort((a, b) => {
    let av = a[key]
    let bv = b[key]
    if (av == null) av = ''
    if (bv == null) bv = ''
    if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir
    return String(av).localeCompare(String(bv)) * dir
  })
  return rows
})
</script>

<style scoped>
.controls {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.search {
  background: var(--panel2);
  border: 1px solid var(--grid);
  color: var(--text);
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  flex: 1;
  min-width: 200px;
}
.count {
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
}
.table-wrap {
  background: var(--panel);
  border: 1px solid var(--grid);
  border-radius: 12px;
  overflow: auto;
  max-height: 70vh;
}
table {
  border-collapse: collapse;
  width: 100%;
  font-size: 12.5px;
}
thead th {
  position: sticky;
  top: 0;
  background: var(--panel2);
  color: var(--muted);
  text-align: left;
  padding: 9px 10px;
  border-bottom: 1px solid var(--grid);
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
}
thead th:hover {
  color: var(--text);
}
thead th.sorted::after {
  content: ' \25be';
  color: var(--accent);
}
thead th.sorted.asc::after {
  content: ' \25b4';
}
tbody td {
  padding: 7px 10px;
  border-bottom: 1px solid #1e2833;
  white-space: nowrap;
}
tbody tr:hover {
  background: var(--panel2);
}
tbody tr.excluded {
  opacity: 0.45;
}
.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.notes-cell {
  white-space: normal;
  max-width: 220px;
  color: var(--muted);
  font-size: 12px;
}
.badge {
  display: inline-block;
  font-size: 10.5px;
  padding: 2px 7px;
  border-radius: 10px;
  font-weight: 600;
}
.badge.clean {
  background: rgba(74, 222, 128, 0.15);
  color: var(--good);
}
.badge.excluded {
  background: rgba(143, 161, 179, 0.2);
  color: var(--muted);
}
.badge.major {
  background: rgba(248, 113, 113, 0.18);
  color: var(--accent3);
}
</style>
