<template>
    <el-dialog v-model="visible" :title="$t('user.settings')" width="700px" align-center>
        <div class="flex  grid-gap-10">
            <div class="flex flex-column grid-gap-1">
                <div v-for="item in options" class="flex flex-y-center grid-gap-2 menu-item"
                    :class="{ 'menu-item-active': activeValue == item.value }" @click="onChange(item.value)">
                    <el-icon :size="16">
                        <!-- <component :is="item.icon" /> -->
                        <HelpSvg v-if="item.value === 'help'" />
                        <UserSvg v-if="item.value === 'account'" />
                        <BookSvg v-if="item.value === 'terms'" />
                        <DunpaiSvg v-if="item.value === 'privacy'" />
                        <AboutSvg v-if="item.value === 'about'" />
                        <LogoutSvg v-if="item.value === 'logout'" />
                    </el-icon>
                    <span>{{ $t(item.name) }}</span>
                </div>
            </div>
            <div class="flex-1 h-p-100 box">
                <User v-if="activeValue === 'account'" ref="userRef" />
                <div v-else v-html="html"></div>
            </div>
        </div>
        <template #footer>
            <div class="dialog-footer">
                <el-button color="var(--el-fill-color-lighter)" size="large" v-if="activeValue === 'account'"
                    @click="handleSave">
                    {{ $t('common.save') }}
                </el-button>
            </div>
        </template>
    </el-dialog>
</template>
<script setup lang="ts">
import { $http } from '@/common/http';
import { ResponseCode } from '@/common/const';
import User from './modules/xl-user.vue';
import { useUserStore } from '@/stores';
import router from '@/routers';
import HelpSvg from '@/svg/icon/icon-help.vue';
import UserSvg from '@/svg/icon/icon-user.vue';
import BookSvg from '@/svg/icon/icon-book.vue';
import DunpaiSvg from '@/svg/icon/icon-dunpai.vue';
import AboutSvg from '@/svg/icon/icon-about.vue';
import LogoutSvg from '@/svg/icon/icon-logout.vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const html = ref(null);
const activeValue = ref('account');
const options = reactive([
    { name: 'user.account', icon: 'UserSvg', value: 'account' },
    { name: 'user.help', icon: 'HelpSvg', value: 'help' },
    { name: 'user.terms', icon: 'BookSvg', value: 'terms' },
    { name: 'user.privacy', icon: 'DunpaiSvg', value: 'privacy' },
    { name: 'user.about', icon: 'AboutSvg', value: 'about' },
    { name: 'user.logout', icon: 'LogoutSvg', value: 'logout' },
])
const visible = ref(false);
const userRef = ref<InstanceType<typeof User> | null>(null);
const userStore = useUserStore();
const getArticle = (key: string) => {
    $http.get('/app/article/api/Article/index', { params: { key } }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            html.value = res.data;
        }
    })
}
const onChange = (value: string) => {
    if (value !== 'account' && value !== 'logout') {
        getArticle(value);
    }
    if (value === 'logout') {
        ElMessageBox.confirm(t('user.logoutConfirm'), t('common.tips'), {
            confirmButtonText: t('common.confirm'),
            cancelButtonText: t('common.cancel'),
            type: 'warning',
        }).then(() => {
            userStore.clearUserInfo();
            router.push('/');
            visible.value = false;
            ElMessage.success(t('user.logoutSuccess'));
        });
        return ;
    }
    activeValue.value = value;
}

const handleSave = () => {
    if (userRef.value && typeof userRef.value.save === 'function') {
        userRef.value.save();
    }
}

defineExpose({
    open: () => {
        visible.value = true
    }
})
</script>
<style scoped lang="scss">
.menu-item {
    padding: 12px 36px 12px 12px;
    border-radius: 8px;
    cursor: pointer;

    &-active {
        background-color: var(--el-fill-color-lighter);
    }

    &:hover {
        background-color: var(--el-fill-color-lighter);
    }
}

.box {
    min-height: 400px !important;
    max-height: 400px !important;
    overflow-y: auto;
}

.dialog-footer {
    min-height: 40px;
}
</style>