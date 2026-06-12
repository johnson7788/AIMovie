<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { useUserStore } from '@/stores';
import { ElMessage } from 'element-plus';

const userStore = useUserStore()
const emit = defineEmits(['success', 'close'])

const close = () => {
    emit('close')
}

const activeTabs = ref<'login' | 'register'>('login')
const tabs = [
    { label: '登录', value: 'login' },
    { label: '注册', value: 'register' },
]

const loginForm = reactive({
    username: '',
    password: '',
})

const registerForm = reactive({
    username: '',
    password: '',
    vpassword: '',
})

const loading = ref(false)

const submitDisabled = computed(() => {
    if (activeTabs.value === 'login') {
        return !loginForm.username.trim() || !loginForm.password
    }
    return !registerForm.username.trim()
        || !registerForm.password
        || !registerForm.vpassword
        || registerForm.password !== registerForm.vpassword
})

const handleLoginSuccess = (data: any) => {
    ElMessage.success('登录成功')
    userStore.setUserInfo(data).then(() => {
        emit('success', { code: ResponseCode.SUCCESS, data })
    }).catch(() => {
        ElMessage.error('登录失败')
    })
}

const login = () => {
    loading.value = true
    $http.post('/app/user/api/Login/login', {
        username: loginForm.username.trim(),
        password: loginForm.password,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            handleLoginSuccess(res.data)
        } else {
            ElMessage.error(res.msg || '登录失败')
        }
    }).finally(() => {
        loading.value = false
    })
}

const registerSubmit = () => {
    loading.value = true
    $http.post('/app/user/api/Login/register', {
        username: registerForm.username.trim(),
        password: registerForm.password,
        vpassword: registerForm.vpassword,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success('注册成功')
            handleLoginSuccess(res.data)
        } else {
            ElMessage.error(res.msg || '注册失败')
        }
    }).finally(() => {
        loading.value = false
    })
}

const handleSubmit = () => {
    if (activeTabs.value === 'register') {
        registerSubmit()
    } else {
        login()
    }
}

</script>

<template>
    <div class="x-login">
        <div class="x-login-form">
            <el-icon class="x-login-form-close" @click="close">
                <Close />
            </el-icon>
            <el-segmented v-model="activeTabs" :options="tabs" class="tabs-segmented border" />
            <div class="x-login-form-content">
                <template v-if="activeTabs === 'login'">
                    <el-input
                        v-model="loginForm.username"
                        placeholder="请输入账号"
                        @keyup.enter="login"
                    >
                        <template #prepend>
                            <el-icon size="20" color="var(--el-bg-color)">
                                <User />
                            </el-icon>
                        </template>
                    </el-input>
                    <el-input
                        type="password"
                        v-model="loginForm.password"
                        placeholder="请输入密码"
                        show-password
                        @keyup.enter="login"
                    >
                        <template #prepend>
                            <el-icon size="20" color="var(--el-bg-color)">
                                <Lock />
                            </el-icon>
                        </template>
                    </el-input>
                </template>
                <template v-else>
                    <el-input
                        v-model="registerForm.username"
                        placeholder="请输入用户名（4-30位字母数字或下划线）"
                        @keyup.enter="registerSubmit"
                    >
                        <template #prepend>
                            <el-icon size="20" color="var(--el-bg-color)">
                                <User />
                            </el-icon>
                        </template>
                    </el-input>
                    <el-input
                        type="password"
                        v-model="registerForm.password"
                        placeholder="请输入密码（5-30位）"
                        show-password
                        @keyup.enter="registerSubmit"
                    >
                        <template #prepend>
                            <el-icon size="20" color="var(--el-bg-color)">
                                <Lock />
                            </el-icon>
                        </template>
                    </el-input>
                    <el-input
                        type="password"
                        v-model="registerForm.vpassword"
                        placeholder="请确认密码"
                        show-password
                        @keyup.enter="registerSubmit"
                    >
                        <template #prepend>
                            <el-icon size="20" color="var(--el-bg-color)">
                                <Lock />
                            </el-icon>
                        </template>
                    </el-input>
                </template>
                <el-button
                    color="var(--el-bg-color)"
                    @click="handleSubmit"
                    class="x-login-form-login-button"
                    :disabled="submitDisabled"
                    :loading="loading"
                >
                    <span>{{ activeTabs === 'register' ? '确认注册' : '确认登录' }}</span>
                </el-button>
            </div>
            <div class="x-login-form-agreement">
                <span>登录即代表阅读并同意</span>
                <el-link href="/#/article/user" type="success" target="_blank" underline="never">《用户协议》</el-link>
                <span>和</span>
                <el-link href="/#/article/privacy" type="success" target="_blank" underline="never">《隐私政策》</el-link>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
.x-login {
    width: 100%;
    height: var(--el-messagebox-height);
    display: flex;
    align-items: center;
    justify-content: center;

    .x-login-form {
        width: 100%;
        max-width: 420px;
        height: 100%;
        background-color: #FFFFFF;
        position: relative;
        padding: 24px 28px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 20px;

        .tabs-segmented {
            --el-border-radius-base: 6px;
            --el-segmented-bg-color: var(--el-bg-color-overlay);
            --el-segmented-padding: 4px;
            --el-segmented-item-selected-bg-color: #FFFFFF;
            --el-segmented-item-selected-color: var(--el-bg-color);
            font-weight: 600;

            :deep(.el-segmented__item) {
                padding: 8px 0;
                width: 95px;
            }

            :deep(.el-segmented__group) {
                gap: 10px;
            }
        }

        .x-login-form-close {
            position: absolute;
            top: 10px;
            right: 10px;
            cursor: pointer;
            font-size: 20px;
            color: rgba(60, 60, 67, 0.60);
            background-color: rgba(116, 116, 128, 0.08);
            border-radius: 50%;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;

            &:hover {
                background-color: rgba(116, 116, 128, 0.16);
            }
        }

        .x-login-form-content {
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 20px;

            :deep(.el-input) {
                --el-input-bg-color: rgba(247, 247, 247, 1);
                --el-input-border-color: rgba(247, 247, 247, 1);
                --el-input-height: 50px;
                --el-input-border-radius: 12px;
                --el-input-focus-border-color: var(--el-border-color-hover);
                --el-input-text-color: #141414;
                --el-font-size-base: 16px;

                .el-input__inner {
                    font-weight: 600;
                    letter-spacing: 2px;

                    &::placeholder {
                        font-weight: 400;
                        font-size: 14px;
                    }
                }

                .el-input-group__append,
                .el-input-group__prepend {
                    background-color: var(--el-input-bg-color);
                }
            }

            .x-login-form-login-button {
                width: 100%;
                height: 50px;
                line-height: 50px;
                border-radius: 12px;
            }
        }

        .x-login-form-agreement {
            font-size: 12px;
            color: rgba(60, 60, 67, 0.60);
            text-align: center;

            :deep(.el-link) {
                --el-link-font-size: 12px;
                vertical-align: unset;
            }
        }
    }
}
</style>
