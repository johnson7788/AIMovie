import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import "@/assets/css/theme.min.css";
import "@/assets/css/common.min.css";
import "@/assets/css/style.min.css";
import App from './App.vue'
import { createPinia } from 'pinia'
const pinia = createPinia()
import router from "@/routers";
import zhCn from 'element-plus/es/locale/lang/zh-cn';
const app = createApp(App)
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
}
app.use(ElementPlus, { locale: zhCn });
import { i18n } from '@/locale';
app.use(i18n);
app.use(pinia);
app.use(router);
app.mount('#app')