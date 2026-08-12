<template>
  <div class="app-shell">
    <header class="app-nav">
      <span class="brand">🚌 Bus Living</span>
      <nav>
        <RouterLink to="/dashboard">Dashboard</RouterLink>
        <RouterLink to="/log">Data Log</RouterLink>
        <RouterLink to="/map">Map</RouterLink>
      </nav>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<style scoped>
.app-shell {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.app-nav {
  display: flex;
  align-items: center;
  gap: 28px;
  padding: 14px 24px;
  border-bottom: 1px solid var(--grid);
  background: var(--panel);
}

.brand {
  font-weight: 700;
  font-size: 15px;
}

.app-nav nav {
  display: flex;
  gap: 6px;
}

.app-nav nav a {
  text-decoration: none;
  color: var(--muted);
  font-size: 13.5px;
  font-weight: 600;
  padding: 7px 14px;
  border-radius: 8px;
}

.app-nav nav a:hover {
  color: var(--text);
}

.app-nav nav a.router-link-active {
  color: #0f1720;
  background: var(--accent);
}

.app-main {
  flex: 1;
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
  padding: 28px 20px 60px;
}
</style>
