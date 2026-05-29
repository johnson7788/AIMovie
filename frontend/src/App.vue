<script setup lang="ts">
import { useModelStore, useRefs, useStateStore, useUserStore, useWebConfigStore } from '@/stores';

import zhCn from 'element-plus/es/locale/lang/zh-cn';
import en from 'element-plus/es/locale/lang/en';

import { useI18n } from 'vue-i18n';
import { Push } from '@/common/push';
import { $http } from './common/http';
import { ResponseCode } from './common/const';
const { locale } = useI18n();

const stateStore = useStateStore();
const { STATE } = useRefs(stateStore);

const language = ref(zhCn);
watch(() => STATE.value.language, (newLanguage: LanguageInterface) => {
	locale.value = newLanguage;
	document.documentElement.setAttribute('lang', newLanguage);
	switch (newLanguage) {
		case 'zh-CN':
			language.value = zhCn;
			break;
		case 'en':
			language.value = en;
			break;
	}
});
const userStore = useUserStore();
userStore.userListener();
userStore.initUserInfo();
const webConfigStore = useWebConfigStore();
const { WEBCONFIG } = useRefs(webConfigStore);
webConfigStore.initWebConfig();
const modelStore = useModelStore();
modelStore.initModel();
const { appContext } = getCurrentInstance()!
const global = appContext.config.globalProperties
const createPush = () => {
	if (WEBCONFIG.value.push && !global.$push) {
		const host = location.host;
		// 建立连接
		global.$push = new Push({
			url: host === 'short-play-vue.yc.com' ? 'wss://' + host : WEBCONFIG.value.push.url, // websocket地址
			app_key: WEBCONFIG.value.push.app_key,
			auth: WEBCONFIG.value.push.auth // 订阅鉴权(仅限于私有频道)
		});
	}
}

const getUserInfo = () => {
	return new Promise((resolve, reject) => {
		$http.get('/app/user/api/User/info').then((res: any) => {
			if (res.code === ResponseCode.SUCCESS) {
				const userStore = useUserStore();
				userStore.setUserInfo(res.data as UserInfoInterface);
				resolve(res.data);
			} else {
				reject();
			}
		}).catch(() => {
			reject();
		});
	})
}
if (userStore.hasLogin()) {
	getUserInfo()
}
const getModelsList = () => {
	$http.get('/app/model/api/Model/models').then((res: any) => {
		if (res.code === ResponseCode.SUCCESS) {
			modelStore.setModel(res.data);
		}
	})
}
const getWebConfig = () => {
	$http.get('/app/control/api/Public/config').then((res: any) => {
		if (res.code === ResponseCode.SUCCESS) {
			webConfigStore.setWebConfig(res.data as WebConfigInterface);
		}
	})
}
onMounted(() => {
	getModelsList();
	getWebConfig();
	try {
		createPush()
		watch(() => WEBCONFIG.value.push, () => {
			createPush()
		})
	} catch (error) {

	}
})
</script>

<template>
	<el-config-provider :locale="language">
		<router-view />
	</el-config-provider>
</template>

<style scoped lang="scss"></style>
