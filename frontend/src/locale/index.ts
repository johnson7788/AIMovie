import { createI18n } from 'vue-i18n';
import { default as en } from './en'
import { default as zhCn } from './zh-cn';
import { App } from 'vue';
export const i18n = createI18n({
	legacy: false,
	locale: 'zh-CN',
	globalInjection: true,
	messages: {
		en,
		zh: zhCn,
		'zh-CN': zhCn
	}
});
export const setupI18n = {
	install(app: App) {
		app.use(i18n);
	},
};