<script setup lang="ts">
import HelperSvg from '@/svg/icon/helper.vue';
import { useUserStore, useRefs, useWebConfigStore } from '@/stores';
import { useNotify } from '@/composables/useNotify';
import IconEmailSvg from '@/svg/icon/icon-email.vue';
import { usePush } from '@/composables/usePush';
import { useI18n } from 'vue-i18n';
import router from '@/routers';
import { throttle } from '@/common/functions';
import { $http } from '@/common/http';
import { ResponseCode } from '@/common/const';
const { locale } = useI18n();
const props = withDefaults(defineProps<{
    showMenu?: any[]
}>(), {
    showMenu: () => ([]),
});
const showMenu = computed(() => {
    return props.showMenu?.length > 0 ? props.showMenu : ['invitation', 'language', 'helper', 'userinfo'];
});
const userStore = useUserStore();
const { USERINFO } = useRefs(userStore);
const webConfigStore = useWebConfigStore();
const { WEBCONFIG } = useRefs(webConfigStore);
const notify = useNotify();
const { subscribe, unsubscribe, unsubscribeAll } = usePush();
const toggleLanguage = () => {
    locale.value = locale.value === 'zh-CN' ? 'en' : 'zh-CN';
    localStorage.setItem('locale', locale.value);
};
const getUserInfo = throttle(() => {
    $http.get('/app/user/api/User/info').then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            const userStore = useUserStore();
            userStore.setUserInfo(res.data as UserInfoInterface);
        }
    }).catch(() => {
    });
}, 1000);
const addListener = () => {
    if (userStore.hasLogin()) {
        subscribe('private-notify-' + USERINFO.value?.user, (res: any) => {
            notify.parse(res);
        });
        subscribe('private-user-' + USERINFO.value?.user, () => {
            getUserInfo();
        });
    }
    subscribe('notify', (res: any) => {
        notify.parse(res);
    });
}
watch(USERINFO, (newVal, oldVal) => {
    if (newVal !== oldVal && oldVal?.user) {
        unsubscribe('private-notify-' + oldVal.user);
        unsubscribe('private-user-' + oldVal.user);
    }
    addListener();
});
const xlInvitationCodeRef = ref<any>(null);

//跳转链接
const toUse = () => {
    const url = WEBCONFIG.value.guide_url
    if (url) {
        window.open(url, '_blank');
    } else {
        router.push('/article/guide');
    }
}

onMounted(() => {
    addListener();
})
onUnmounted(() => {
    unsubscribeAll();
})
</script>
<template>
    <div class="flex flex-y-center flex-x-flex-end grid-gap-4 x-header-tools">
        <div class="btn h10" @click="xlInvitationCodeRef.open" v-if="USERINFO && showMenu?.includes('invitation')">
            <el-icon :size="16">
                <IconEmailSvg />
            </el-icon>
            <span class="h10">{{ $t('header.invitation') }}</span>
        </div>
        <div class="x-header-tool" v-if="showMenu?.includes('helper')" @click="toUse">
            <el-icon alt="帮助" :size="26" class="x-header-tool-img"  color="rgba(255, 255, 255, 0.3)">
                <HelperSvg />
            </el-icon>
        </div>
        <div class="x-header-tool lang-toggle" v-if="showMenu?.includes('language')" @click="toggleLanguage" :title="locale === 'zh-CN' ? 'Switch to English' : '切换为中文'">
            <span class="lang-label" :class="{ active: locale === 'zh-CN' }">中</span>
            <span class="lang-divider">/</span>
            <span class="lang-label" :class="{ active: locale !== 'zh-CN' }">EN</span>
        </div>
        <xl-header-userinfo v-if="showMenu?.includes('userinfo')" />
        <xl-invitation-code ref="xlInvitationCodeRef" />
    </div>
</template>
<style scoped lang="scss">
.x-header-tools {
    .btn {
        background: rgba(255, 255, 255, 0.04);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 10px 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 2px;
        cursor: pointer;

        &:hover {
            background: rgba(255, 255, 255, 0.1);
        }
    }

    .x-header-tool {
        width: calc(var(--xl-header-height) - 20px);
        height: calc(var(--xl-header-height) - 20px);
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;

        &:hover {
            background-color: rgba(13, 242, 131, 0.10);
        }

        cursor: pointer;

        &-img {
            font-size: 30px;
            width: 50%;
            height: 50%;
        }

        &.lang-toggle {
            width: auto;
            padding: 0 10px;
            gap: 4px;
            font-size: 14px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.3);

            .lang-label {
                transition: color 0.2s ease;

                &.active {
                    color: rgba(255, 255, 255, 0.9);
                }
            }

            .lang-divider {
                color: rgba(255, 255, 255, 0.15);
                font-weight: 400;
            }
        }
    }
}
</style>
<style>
.el-dialog {
    --el-border-radius-base: 20px !important;
}
</style>