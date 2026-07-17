import { ref } from 'vue'

const STORAGE_KEY = 'pse-vision-theme'

// Resolve the initial theme: saved preference -> OS preference -> light
function resolveInitialTheme() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch (e) { /* ignore */ }
  if (typeof window !== 'undefined' && window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

// Shared singleton state so every component reads the same theme
const theme = ref(resolveInitialTheme())

function applyTheme(value) {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', value)
  }
}

// Apply immediately on module load (index.html also does this to avoid FOUC)
applyTheme(theme.value)

export function useTheme() {
  const setTheme = (value) => {
    theme.value = value === 'dark' ? 'dark' : 'light'
    applyTheme(theme.value)
    try { localStorage.setItem(STORAGE_KEY, theme.value) } catch (e) { /* ignore */ }
  }

  const toggleTheme = () => {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  return { theme, setTheme, toggleTheme }
}
