<script setup lang="ts">
import { truncate } from '@/common/functions';
import { useLogin } from '@/composables/useLogin';
import { useRefs, useUserStore } from '@/stores';
// import LanguageSvg from '@/svg/icon/language.vue';
import router from '@/routers';

const login = useLogin();
const userStore = useUserStore();
const { USERINFO } = useRefs(userStore);
const xlUserinfoRef = ref<any>(null);
const userinfoPopoverRef = ref<any>(null);
const xlInvitationCodeRef = ref<any>(null);
</script>
<template>
    <el-popover placement="bottom" ref="userinfoPopoverRef" :width="320" trigger="click"
        popper-style="border-radius: 10px;" v-if="userStore.hasLogin()">
        <template #reference>
            <div class="xl-header-userinfo">
                <div class="xl-header-userinfo-info">
                    <el-avatar :size="30" :src="USERINFO?.headimg">
                        {{ truncate(USERINFO.nickname, 1) }}
                    </el-avatar>
                </div>
            </div>
        </template>
        <template #default>
            <div class="userinfo">
                <div class="h7 font-weight-bold">{{ USERINFO?.nickname }}</div>
                <div class="text-secondary mt-4">ID {{ USERINFO?.id }}</div>

                <el-divider />
                <div class="flex flex-y-center grid-gap-2 pointer"
                    @click="userinfoPopoverRef.hide(); xlInvitationCodeRef.open()">
                    <el-icon color="#fff" size="20">
                        <Present />
                    </el-icon>
                    <span class="h8">邀请好友</span>
                    <div class="num">{{ USERINFO?.invitation_code_count || 0 }}</div>
                </div>
                <!-- <div class="flex flex-y-center grid-gap-2 mt-8">
                    <el-icon color="#fff" size="20">
                        <LanguageSvg />
                    </el-icon>
                    <span class=" h8">语言</span>
                    <el-divider direction="vertical" />
                    <span class="h9 text-secondary">简体中文</span>
                    <el-icon color="#B5B5B5">
                        <CaretBottom />
                    </el-icon>
                </div> -->
                <div class="flex flex-y-center grid-gap-2 mt-8 pointer"
                    @click="userinfoPopoverRef.hide(); xlUserinfoRef.open()">
                    <el-icon color="#fff" size="20">
                        <Setting />
                    </el-icon>
                    <span class=" h8">设置中心</span>
                </div>
            </div>
        </template>
    </el-popover>
    <div class="xl-header-userinfo" v-else>
        <div class="xl-header-userinfo-button" @click="login.open()">
            <span>一键登录</span>
        </div>
    </div>
    <xl-userinfo ref="xlUserinfoRef" />
    <xl-invitation-code ref="xlInvitationCodeRef" />
</template>

<style scoped lang="scss">
.xl-header-userinfo {
    cursor: pointer;

    &-info {
        display: flex;
        align-items: center;
        justify-content: center;
    }

    &-button {
        min-width: 120px;
        height: calc(var(--xl-header-height, 70px) - 30px);
        border-radius: 100px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid #FFFFFF;
        cursor: pointer;
        background: linear-gradient(to right, #FFFFFF, #FFFFFF);
        background-position: left center;
        background-size: 0% 100%;
        background-repeat: no-repeat;
        transition: background-size 0.3s ease-in;

        &:hover {
            background-size: 100% 100%;
        }

        span {
            font-size: 14px;
            font-weight: 500;
            color: #FFFFFF;
            mix-blend-mode: difference;
            selection: none;
            user-select: none;
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
        }
    }
}


.userinfo {
    border-radius: 10px;
    color: #FFFFFF;

    .btn {
        width: 100%;
        padding: 10px 0px;
        text-align: center;
        border-radius: 20px;
        background: linear-gradient(90deg, #F4CF77 0%, #FFF1D0 100%);
        border: 0px solid rgba(255, 255, 255, 0.3);
        color: #3D2D09;
        margin-top: 16px;
        font-weight: bold;
        cursor: pointer;
    }

    .num {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: linear-gradient(90deg, #79FFFF 0%, #0DF283 100%);
        color: #000;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
    }
}

.el-divider--horizontal {
    --el-border-color: rgba(255, 255, 255, 0.1);
}
</style>