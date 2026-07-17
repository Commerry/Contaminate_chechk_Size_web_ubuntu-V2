/**
 * Debug utility to intercept and log ALL file input activities
 */

let isInterceptorInstalled = false

export function installFileInputDebugger() {
  if (isInterceptorInstalled) {
    console.log('⚠️ File input debugger already installed')
    return
  }

  console.log('🔧 Installing file input debugger...')

  // Intercept HTMLInputElement.click()
  const originalClick = HTMLInputElement.prototype.click
  HTMLInputElement.prototype.click = function() {
    if (this.type === 'file') {
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
      console.log('🚨 FILE INPUT .click() CALLED!')
      console.log('  Element:', this)
      console.log('  ID:', this.id || '(no id)')
      console.log('  Class:', this.className || '(no class)')
      console.log('  Name:', this.name || '(no name)')
      console.log('  Accept:', this.accept || '(any)')
      console.log('  Multiple:', this.multiple)
      console.trace('📍 Stack trace:')
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    }
    return originalClick.apply(this, arguments)
  }

  // Intercept addEventListener for file inputs
  const originalAddEventListener = EventTarget.prototype.addEventListener
  EventTarget.prototype.addEventListener = function(type, listener, options) {
    if (this instanceof HTMLInputElement && this.type === 'file') {
      console.log('📌 Event listener added to file input:', type)
    }
    return originalAddEventListener.call(this, type, listener, options)
  }

  // Monitor file input creation
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node instanceof HTMLInputElement && node.type === 'file') {
          console.log('➕ New file input created:', node)
        }
      })
    })
  })

  observer.observe(document.body, {
    childList: true,
    subtree: true
  })

  isInterceptorInstalled = true
  console.log('✅ File input debugger installed successfully')
}

export function logFileInputEvent(eventName, details = {}) {
  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`)
  console.log(`🔍 FILE INPUT EVENT: ${eventName}`)
  Object.entries(details).forEach(([key, value]) => {
    console.log(`  ${key}:`, value)
  })
  console.trace('📍 Stack trace:')
  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`)
}
