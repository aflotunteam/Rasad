import { createApp } from 'vue'
import { createPinia } from 'pinia'
import '@fontsource-variable/inter'
import 'maplibre-gl/dist/maplibre-gl.css'
import './styles/tokens.css'
import './styles/base.css'
import App from './App.vue'
import { router } from './router'
import { setUnauthorizedHandler } from './services/http'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

setUnauthorizedHandler(() => {
  const auth = useAuthStore(pinia)
  auth.clear()
  if (router.currentRoute.value.name !== 'login') {
    router.replace({ name: 'login', query: { next: router.currentRoute.value.fullPath, expired: '1' } })
  }
})

app.mount('#app')
