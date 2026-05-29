<template>
    <div class="h9 text-black">
        <div class="flex flex-y-center ">
            <div class="flex flex-y-center  grid-gap-7 flex-1" v-if="!editStatus">
                <el-avatar :size="54" :src="USERINFO?.headimg">
                    {{ truncate(USERINFO?.nickname, 1) }}
                </el-avatar>
                <div class="flex flex-column flex-x-start grid-gap-2">
                    <span class="h8 font-weight-bold">{{ USERINFO?.nickname }}</span>
                    <div class="h9 text-secondary">{{ USERINFO?.id }}</div>
                </div>
            </div>
            <div class="flex flex-y-center  grid-gap-7 flex-1" v-else>
                <div class="position-relative">
                    <el-upload ref="uploadImageRef" class="avatar-uploader"
                        :data="{ dir_name: 'user/headimg', dir_title: '用户头像' }"
                        :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                        :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1" type="cover"
                        :disabled="uploadHeadimgLoading"
                        :before-upload="() => { uploadHeadimgLoading = true; return true; }"
                        :on-success="handleUploadSuccess" :show-file-list="false"
                        :on-error="() => { uploadHeadimgLoading = false; handleUploadError() }">
                        <template #default>
                            <div class="avatar-wrapper">
                                <el-avatar :size="54" :src="form.headimg || USERINFO?.headimg">
                                    {{ truncate(form.nickname || USERINFO?.nickname, 1) }}
                                </el-avatar>
                                <div class="pointer position-absolute bottom--0 right-0 edit" @click.stop="triggerUpload">
                                    <el-icon color="#000" :size="12" v-if="!uploadHeadimgLoading">
                                        <IconEdit />
                                    </el-icon>
                                    <el-icon color="#000" :size="12" v-else class="is-loading">
                                        <Loading />
                                    </el-icon>
                                </div>
                            </div>
                        </template>
                    </el-upload>
                </div>
                <div class="flex flex-column flex-x-start">
                    <el-input v-model="form.nickname" placeholder="请输入昵称" maxlength="20" show-word-limit />
                </div>
            </div>
            <el-button color="var(--el-fill-color-lighter)" @click="toggleEditStatus" >
                {{ editStatus ? '取消' : '编辑信息' }}
            </el-button>
        </div>
        <el-divider />

        <div class="flex flex-x-space-between">
            <span>手机号</span>
            <div class="flex flex-y-center grid-gap-4">
                <el-input v-if="editMobile" v-model="form.mobile" placeholder="请输入手机号" maxlength="11"
                    @blur="validateMobile" />
                <span v-else>{{ USERINFO?.mobile || '未绑定' }}</span>
                <el-icon :size="16" class="pointer" @click="toggleMobileEdit" v-if="!editStatus">
                    <Edit />
                </el-icon>
                <el-icon :size="16" class="pointer" @click="cancelMobileEdit" v-else-if="editMobile">
                    <Close />
                </el-icon>
            </div>
        </div>
        <div class="flex flex-x-space-between mt-10">
            <span>微信</span>
            <div class="flex flex-y-center grid-gap-4">
                <span>{{ isWechatBound ? '已绑定' : '未绑定' }}</span>
                <el-icon :size="16" class="pointer" @click="openWechatBindDialog" v-if="!isWechatBound">
                    <Edit />
                </el-icon>
            </div>
        </div>
        <div class="flex flex-x-space-between mt-10">
            <span>密码</span>
            <div class="flex flex-y-center grid-gap-4 pointer"  @click="openPasswordDialog">
                <span>{{ USERINFO?.password==1 ? '修改' : '设置' }}</span>
                <el-icon :size="16" >
                    <Edit />
                </el-icon>
            </div>
        </div>
    </div>

    <!-- 绑定微信二维码对话框 -->
    <el-dialog v-model="wechatBindDialogVisible" title="绑定微信" width="400px" align-center @close="closeWechatBindDialog">
        <div class="flex flex-column flex-y-center grid-gap-4">
            <p class="text-center">请使用微信扫描下方二维码完成绑定</p>
            <xl-qrcode-view 
                v-if="wechatBindDialogVisible"
                url="/app/user/api/Login/qrcode" 
                check="/app/user/api/Login/checkBind"
                @success="handleWechatBindSuccess" />
        </div>
    </el-dialog>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="400px" align-center @close="closePasswordDialog">
        <div class="flex flex-column grid-gap-4">
            <el-input v-model="passwordForm.password" type="password" placeholder="请输入新密码" show-password />
            <el-input v-model="passwordForm.confirmPassword" type="password" placeholder="请确认新密码" show-password />
            <el-input v-model="passwordForm.vcode" placeholder="请输入短信验证码" maxlength="6">
                <template #append>
                    <el-button type="primary" :disabled="passwordVcode.btnDisabled.value" @click="getPasswordVcode">
                        {{ passwordVcode.btnText.value }}
                    </el-button>
                </template>
            </el-input>
        </div>
        <template #footer>
            <div class="dialog-footer">
                <el-button @click="closePasswordDialog">取消</el-button>
                <el-button  color="var(--el-color-success)" :loading="passwordLoading" @click="handleSetPassword">确认</el-button>
            </div>
        </template>
    </el-dialog>
</template>
<script setup lang="ts">
import { truncate } from '@/common/functions';
import { useRefs, useUserStore } from '@/stores';
import { $http } from '@/common/http';
import { ResponseCode } from '@/common/const';
import { useVcode } from '@/composables/useVcode';
import IconEdit from '@/svg/icon/icon-edit.vue';
import { Edit, Close, Loading } from '@element-plus/icons-vue';

const userStore = useUserStore();
const { USERINFO } = useRefs(userStore);
const editMobile = ref(false);
const editStatus = ref(false);
const uploadHeadimgLoading = ref(false);
const saving = ref(false);
const uploadImageRef = ref<any>(null);
const wechatBindDialogVisible = ref(false);
const passwordDialogVisible = ref(false);
const passwordLoading = ref(false);
const passwordVcode = useVcode();

// 修改密码表单
const passwordForm = reactive({
    password: '',
    confirmPassword: '',
    vcode: '',
    token: null as string | null,
    phoneCountryCode: '+86'
});

// 计算是否已绑定微信（通过USERINFO.wechat判断）
const isWechatBound = computed(() => {
    return !!(USERINFO.value?.wechat && USERINFO.value.wechat.openid.trim() !== '');
});

// 保存原始数据，用于取消编辑时恢复
const originalData = ref({
    nickname: '',
    mobile: '',
    headimg: '',
});

const form = reactive({
    mobile: '',
    nickname: '',
    headimg: '',
});

// 初始化表单数据
const initForm = () => {
    form.nickname = USERINFO.value?.nickname || '';
    form.mobile = USERINFO.value?.mobile || '';
    form.headimg = USERINFO.value?.headimg || '';
    originalData.value = {
        nickname: form.nickname,
        mobile: form.mobile,
        headimg: form.headimg,
    };
};

// 监听用户信息变化，初始化表单
watch(() => USERINFO.value, () => {
    if (USERINFO.value) {
        initForm();
    }
}, { immediate: true });

// 打开绑定微信对话框
const openWechatBindDialog = () => {
    wechatBindDialogVisible.value = true;
};

// 关闭绑定微信对话框
const closeWechatBindDialog = () => {
    wechatBindDialogVisible.value = false;
};

// 微信绑定成功回调
const handleWechatBindSuccess = async (response: any) => {
    if (response.code === ResponseCode.SUCCESS) {
        ElMessage.success('微信绑定成功');
        wechatBindDialogVisible.value = false;
        
        // 刷新用户信息
        try {
            const infoRes: any = await $http.get('/app/user/api/User/info');
            if (infoRes.code === ResponseCode.SUCCESS) {
                await userStore.setUserInfo(infoRes.data as UserInfoInterface);
            }
        } catch (error: any) {
            ElMessage.error('刷新用户信息失败，请稍后重试');
        }
    }
};

// 打开修改密码对话框
const openPasswordDialog = () => {
    passwordForm.password = '';
    passwordForm.confirmPassword = '';
    passwordForm.vcode = '';
    passwordForm.token = null;
    passwordDialogVisible.value = true;
};

// 关闭修改密码对话框
const closePasswordDialog = () => {
    passwordDialogVisible.value = false;
    passwordForm.password = '';
    passwordForm.confirmPassword = '';
    passwordForm.vcode = '';
    passwordForm.token = null;
};

// 获取修改密码验证码
const getPasswordVcode = () => {
    if (!USERINFO.value?.mobile) {
        ElMessage.warning('请先绑定手机号');
        return;
    }
    passwordVcode.open({
        username: USERINFO.value.mobile,
        countryCode: passwordForm.phoneCountryCode,
        scene: 'set_password',
        headers: $http.getHeaders()
    }).then((res: any) => {
        passwordForm.vcode = '';
        passwordForm.token = res.token;
    }).catch(() => {
        // 用户取消验证码弹窗
    });
};

// 验证密码格式
const validatePassword = () => {
    if (!passwordForm.password || passwordForm.password.trim() === '') {
        ElMessage.warning('请输入新密码');
        return false;
    }
    if (passwordForm.password.length < 6) {
        ElMessage.warning('密码长度不能少于6位');
        return false;
    }
    if (passwordForm.password !== passwordForm.confirmPassword) {
        ElMessage.warning('两次输入的密码不一致');
        return false;
    }
    if (!passwordForm.vcode || passwordForm.vcode.trim() === '') {
        ElMessage.warning('请输入短信验证码');
        return false;
    }
    return true;
};

// 设置密码
const handleSetPassword = async () => {
    if (!validatePassword()) {
        return;
    }
    if (passwordLoading.value) return;

    passwordLoading.value = true;

    try {
        const res: any = await $http.post('/app/user/api/User/update', {
            password: passwordForm.password,
            vpassword: passwordForm.confirmPassword,
            vcode: passwordForm.vcode,
            token: passwordForm.token,
            username: USERINFO.value?.mobile
        });

        if (res.code === ResponseCode.SUCCESS || res.code === ResponseCode.SUCCESS_EVENT_PUSH) {
            ElMessage.success(res.msg || '密码修改成功');
            closePasswordDialog();
        } else {
            ElMessage.error(res.msg || '密码修改失败');
        }
    } catch (error: any) {
        ElMessage.error(error?.msg || '密码修改失败，请稍后重试');
    } finally {
        passwordLoading.value = false;
    }
};

// 切换编辑状态
const toggleEditStatus = () => {
    if (editStatus.value) {
        // 取消编辑，恢复原始数据
        form.nickname = originalData.value.nickname;
        form.headimg = originalData.value.headimg;
        editMobile.value = false;
        form.mobile = originalData.value.mobile;
    } else {
        // 进入编辑模式，保存当前数据
        originalData.value = {
            nickname: form.nickname,
            mobile: form.mobile,
            headimg: form.headimg,
        };
    }
    editStatus.value = !editStatus.value;
};

// 切换手机号编辑状态
const toggleMobileEdit = () => {
    if (!editStatus.value) {
        editStatus.value = true;
        originalData.value = {
            nickname: form.nickname,
            mobile: form.mobile,
            headimg: form.headimg,
        };
    }
    editMobile.value = true;
};

// 取消手机号编辑
const cancelMobileEdit = () => {
    form.mobile = originalData.value.mobile;
    editMobile.value = false;
};

// 验证手机号格式
const validateMobile = () => {
    if (form.mobile && !/^1[3-9]\d{9}$/.test(form.mobile)) {
        ElMessage.warning('请输入正确的手机号');
        return false;
    }
    return true;
};

// 头像上传成功
const handleUploadSuccess = (response: any) => {
    if (response.code === ResponseCode.SUCCESS) {
        uploadHeadimgLoading.value = false;
        form.headimg = response.data.url;
        uploadImageRef.value?.clearFiles();
        ElMessage.success('头像上传成功');
    } else {
        uploadHeadimgLoading.value = false;
        ElMessage.error(response.msg || '头像上传失败');
    }
};

// 头像上传失败
const handleUploadError = () => {
    uploadHeadimgLoading.value = false;
    uploadImageRef.value?.clearFiles();
    ElMessage.error('头像上传失败，请重试');
};

// 触发文件选择
const triggerUpload = () => {
    if (!uploadHeadimgLoading.value) {
        uploadImageRef.value?.$el?.querySelector('input[type="file"]')?.click();
    }
};

// 保存用户信息
const saveUserInfo = async () => {
    if (saving.value) return;

    // 验证昵称
    if (!form.nickname || form.nickname.trim() === '') {
        ElMessage.warning('请输入昵称');
        return;
    }

    // 验证手机号
    if (editMobile.value && form.mobile && !validateMobile()) {
        return;
    }

    saving.value = true;

    try {
        // 构建更新数据
        const updateData: any = {};
        if (form.nickname !== originalData.value.nickname) {
            updateData.nickname = form.nickname;
        }
        if (form.headimg !== originalData.value.headimg) {
            updateData.headimg = form.headimg;
        }
        if (editMobile.value && form.mobile !== originalData.value.mobile) {
            updateData.mobile = form.mobile;
        }

        // 如果没有需要更新的字段
        if (Object.keys(updateData).length === 0) {
            ElMessage.info('没有需要保存的更改');
            saving.value = false;
            return;
        }

        // 调用更新接口
        const res: any = await $http.post('/app/user/api/User/update', updateData);
        console.log(res);
        if (res.code === ResponseCode.SUCCESS_EVENT_PUSH||res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg || '保存成功');

            // 刷新用户信息
            const infoRes: any = await $http.get('/app/user/api/User/info');
            if (infoRes.code === ResponseCode.SUCCESS) {
                await userStore.setUserInfo(infoRes.data as UserInfoInterface);
                initForm();
            }

            // 退出编辑模式
            editStatus.value = false;
            editMobile.value = false;
        } else {
            ElMessage.error(res.msg || '保存失败');
        }
    } catch (error: any) {
        ElMessage.error(error?.msg || '保存失败，请稍后重试');
    } finally {
        saving.value = false;
    }
};

// 暴露保存方法给父组件
defineExpose({
    save: saveUserInfo,
});
</script>
<style scoped lang="scss">
.btn {
    border-radius: 6px;
    background-color: var(--el-fill-color-lighter);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    padding: 9px 16px;
}

.avatar-uploader {
    height: 54px;
    :deep(.el-upload) {
        border: none;
        border-radius: 50%;
        cursor: pointer;
        position: relative;
        overflow: visible;
    }
}

.avatar-wrapper {
    position: relative;
    display: inline-block;
    height: 54px;
}

.edit {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #fff;
    cursor: pointer;
    z-index: 10;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    transition: all 0.2s;
    
    &:hover {
        background-color: #f5f5f5;
        transform: scale(1.1);
    }
    
    .is-loading {
        animation: rotating 2s linear infinite;
    }
}

@keyframes rotating {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}
</style>