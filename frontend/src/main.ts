import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'

// NasFusion Design System (Dracula Purple Dark Theme)
import './assets/styles/index.scss'

// Legacy styles (can be removed after migration)
import './styles/main.css'
import './styles/animations.css'
import './styles/mobile.css'

// 应用主题 class 到 <html>，确保与 localStorage 一致
const savedTheme = localStorage.getItem('nf-theme') || 'ocean'
document.documentElement.className = savedTheme

const app = createApp(App)
const pinia = createPinia()

// 配置 Pinia 持久化插件
pinia.use(piniaPluginPersistedstate)

// Register all Element Plus icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus)

app.mount('#app')
