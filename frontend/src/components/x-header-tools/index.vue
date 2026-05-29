<script setup lang="ts">
import HelperSvg from '@/svg/icon/helper.vue';
import { useUserStore, useRefs, useWebConfigStore } from '@/stores';
import { useNotify } from '@/composables/useNotify';
import IconEmailSvg from '@/svg/icon/icon-email.vue';
import { usePush } from '@/composables/usePush';
import IconWechatSvg from '@/svg/icon/icon-wechat.vue';
import router from '@/routers';
import { throttle } from '@/common/functions';
import { $http } from '@/common/http';
import { ResponseCode } from '@/common/const';
import { useLogin } from '@/composables/useLogin'
const login = useLogin()
const props = withDefaults(defineProps<{
    showMenu?: any[]
}>(), {
    showMenu: () => ([]),
});
const showMenu = computed(() => {
    return props.showMenu?.length > 0 ? props.showMenu : ['invitation', 'language', 'helper', 'userinfo', 'wechat'];
});
const userStore = useUserStore();
const { USERINFO } = useRefs(userStore);
const webConfigStore = useWebConfigStore();
const { WEBCONFIG } = useRefs(webConfigStore);
const notify = useNotify();
const { subscribe, unsubscribe, unsubscribeAll } = usePush();
const wechatGroupDialogVisible = ref(false);
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

// 打开微信群二维码对话框
const openWechatGroupDialog = () => {
    wechatGroupDialogVisible.value = true;
};
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
            <span class="h10">邀请好友得积分</span>
        </div>
        <div class="x-header-tool" v-if="showMenu?.includes('helper')" @click="toUse">
            <el-icon alt="帮助" :size="26" class="x-header-tool-img"  color="rgba(255,255,255,0.5)">
                <HelperSvg />
            </el-icon>
        </div>
        <div class="x-header-tool" v-if="showMenu?.includes('wechat')" @click="openWechatGroupDialog">
            <el-icon alt="微信群" :size="26" class="x-header-tool-img" color="rgba(255,255,255,0.5)">
                <IconWechatSvg />
            </el-icon>
        </div>
        <xl-header-userinfo v-if="showMenu?.includes('userinfo')" />
        <xl-invitation-code ref="xlInvitationCodeRef" />
    </div>

    <!-- 微信群二维码对话框 -->
    <el-dialog v-model="wechatGroupDialogVisible" title="加入官方微信群" width="512px" align-center>
        <div class="flex flex-column flex-y-center grid-gap-4 py-8" v-if="WEBCONFIG?.wechat_group_qrcode_url">
            <el-image :src="WEBCONFIG.wechat_group_qrcode_url" style="width: 230px; height: 230px;" fit="contain"
                :preview-src-list="[WEBCONFIG.wechat_group_qrcode_url]" preview-teleported />
            <p class="text-center">请使用微信扫描下方二维码加入群聊</p>
        </div>
        <p v-else class="text-center text-secondary">二维码暂未配置</p>
    </el-dialog>
</template>
<style scoped lang="scss">
.x-header-tools {
    .btn {
        background: rgba(30, 30, 30, 0.4);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 10px 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 2px;
        cursor: pointer;

        &:hover {
            background: rgba(255, 255, 255, 0.16);
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
    }
}
</style>
<style>
.el-dialog {
    --el-border-radius-base: 20px !important;
}
</style>