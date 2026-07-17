<template>
  <span class="brandmark" :style="{ width: size + 'px', height: size + 'px' }">
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" class="brandmark__svg">
      <defs>
        <linearGradient :id="gid" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#7c5cff" />
          <stop offset="1" stop-color="#19e3c5" />
        </linearGradient>
      </defs>

      <!-- ROI corner brackets (scan frame) -->
      <g :stroke="`url(#${gid})`" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" class="brandmark__frame">
        <path d="M8 15V10a2 2 0 0 1 2-2h5" />
        <path d="M33 8h5a2 2 0 0 1 2 2v5" />
        <path d="M40 33v5a2 2 0 0 1-2 2h-5" />
        <path d="M15 40h-5a2 2 0 0 1-2-2v-5" />
      </g>

      <!-- Rotating measurement reticle -->
      <circle class="brandmark__ring" cx="24" cy="24" r="9.5"
              fill="none" :stroke="`url(#${gid})`" stroke-width="1.6"
              stroke-dasharray="7 6" opacity="0.85" />

      <!-- Caliper crosshair ticks -->
      <g stroke="#19e3c5" stroke-width="1.8" stroke-linecap="round" opacity="0.9">
        <line x1="24" y1="14.5" x2="24" y2="18" />
        <line x1="24" y1="30" x2="24" y2="33.5" />
        <line x1="14.5" y1="24" x2="18" y2="24" />
        <line x1="30" y1="24" x2="33.5" y2="24" />
      </g>

      <!-- Object node with pulse -->
      <circle class="brandmark__pulse" cx="24" cy="24" r="5" fill="#19e3c5" opacity="0.35" />
      <circle class="brandmark__node" cx="24" cy="24" r="3.4" fill="#19e3c5" />
    </svg>
  </span>
</template>

<script setup>
defineProps({
  size: { type: Number, default: 40 }
})
// Unique gradient id so multiple marks don't collide
const gid = 'bm-grad-' + Math.random().toString(36).slice(2, 8)
</script>

<style scoped>
.brandmark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  filter: drop-shadow(0 0 10px rgba(25, 227, 197, 0.45));
}
.brandmark__svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}
.brandmark__ring {
  transform-origin: 24px 24px;
  animation: bm-spin 7s linear infinite;
}
.brandmark__node {
  transform-origin: 24px 24px;
  animation: bm-node 2.4s cubic-bezier(0.83, 0, 0.17, 1) infinite;
}
.brandmark__pulse {
  transform-origin: 24px 24px;
  animation: bm-pulse 2.4s cubic-bezier(0.22, 1, 0.36, 1) infinite;
}
.brandmark__frame {
  transform-origin: 24px 24px;
  animation: bm-breathe 4s ease-in-out infinite;
}
@keyframes bm-spin {
  to { transform: rotate(360deg); }
}
@keyframes bm-node {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(0.7); }
}
@keyframes bm-pulse {
  0% { transform: scale(0.7); opacity: 0.5; }
  80%, 100% { transform: scale(2.4); opacity: 0; }
}
@keyframes bm-breathe {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.75; }
}
@media (prefers-reduced-motion: reduce) {
  .brandmark__ring, .brandmark__node, .brandmark__pulse, .brandmark__frame {
    animation: none;
  }
}
</style>
