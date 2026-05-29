<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { useVcode } from '@/composables/useVcode';
import { useUserStore, useWebConfigStore, useRefs } from '@/stores';
import { ElMessage } from 'element-plus';
import IconLoginPhoneSvg from '@/svg/icon/icon-login-phone.vue';
import IconLoginWechatSvg from '@/svg/icon/icon-login-wechat.vue';
import IconSecuritySvg from '@/svg/icon/icon-security.vue';
const userStore = useUserStore()
const webConfigStore = useWebConfigStore()
const { WEBCONFIG } = useRefs(webConfigStore)
const vcode = useVcode()
const mobileVcode = useVcode() // 用于补充手机号的验证码
const emit = defineEmits(['success', 'close'])
const close = () => {
    emit('close')
}
const activeTabs = ref('login')
const tabs = ref([
    { label: '账号密码', value: 'login' },
    { label: '手机号登录', value: 'vcode' },
    { label: '账号注册', value: 'register' },
])
const form = reactive({
    phoneCountryCode: '+86',
    username: '',
    password: '',
    vcode: '',
    token: null
})
const registerForm = reactive({
    username: '',
    password: '',
    vpassword: '',
})
// 补充手机号的表单
const mobileForm = reactive({
    phoneCountryCode: '+86',
    username: '',
    vcode: '',
    token: null
})
const needMobile = ref(false) // 是否需要补充手机号
const phoneCountryCodeOptions = ref([
    { label: '+86', value: '+86' },
    { label: '+852', value: '+852' },
    { label: '+853', value: '+853' },
    { label: '+855', value: '+855' },
    { label: '+856', value: '+856' },
])
const loading = ref(false)
const registerLoading = ref(false)
const mobileLoading = ref(false) // 补充手机号的loading状态

// 切换到二维码登录时，重置状态
const switchToQrcode = () => {
    needMobile.value = false
    qrcodeLoginData.value = null
    qrcodeToken.value = null
    activeTabs.value = 'qrcode'
}

// 切换到其他登录方式时，重置状态
const switchToLogin = () => {
    needMobile.value = false
    qrcodeLoginData.value = null
    qrcodeToken.value = null
    activeTabs.value = 'login'
}
const login = () => {
    loading.value = true
    $http.post('/app/user/api/Login/' + activeTabs.value, form).then(LoginRes).finally(() => {
        loading.value = false
    })
}
const registerSubmit = () => {
    registerLoading.value = true
    $http.post('/app/user/api/Login/register', registerForm).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success('注册成功');
            userStore.setUserInfo(res.data).then(() => {
                emit('success', res)
            }).catch(() => {
                ElMessage.error('登录失败')
            })
        } else {
            ElMessage.error(res.msg)
        }
    }).finally(() => {
        registerLoading.value = false
    })
}
const handleSubmit = () => {
    if (activeTabs.value === 'register') {
        registerSubmit()
    } else {
        login()
    }
}
const vcodeBtnDisabled = computed(() => {
    return vcode.btnDisabled.value || form.username.length !== 11
})
const mobileVcodeBtnDisabled = computed(() => {
    return mobileVcode.btnDisabled.value || mobileForm.username.length !== 11
})
const submitDisabled = computed(() => {
    switch (activeTabs.value) {
        case 'login':
            return !form.username.length || !form.password.length
        case 'vcode':
            return !form.username.length || !form.vcode.length
        case 'register':
            return !registerForm.username.length || !registerForm.password.length || !registerForm.vpassword.length || registerForm.password !== registerForm.vpassword
    }
    return false;
})
const mobileSubmitDisabled = computed(() => {
    return !mobileForm.username.length || !mobileForm.vcode.length
})
// 检查手机号是否为空
const isMobileEmpty = (mobile: any): boolean => {
    return mobile === null || mobile === undefined || mobile === '' || String(mobile).trim() === ''
}

const LoginRes = (res: any) => {
    console.log(res);
    if (res.code === ResponseCode.SUCCESS) {
        // 检查手机号是否为空
        if (isMobileEmpty(res.data?.mobile)) {
            // 需要补充手机号
            needMobile.value = true
            // 保存登录返回的数据和token，补充手机号后使用
            qrcodeLoginData.value = res.data
            qrcodeToken.value = res.data?.token || null
        } else {
            ElMessage.success('登录成功');
            // 手机号不为空，正常登录
            userStore.setUserInfo(res.data).then(() => {
                emit('success', res)
            }).catch(() => {
                ElMessage.error('登录失败')
            })
        }
    } else {
        ElMessage.error(res.msg)
    }
}

// 保存扫码登录返回的数据
const qrcodeLoginData = ref<any>(null)
// 保存扫码登录返回的token，用于绑定手机号接口
const qrcodeToken = ref<string | null>(null)

// 获取补充手机号的验证码
const getMobileVcode = () => {
    const headers = {
        ...$http.getHeaders(),
        Authorization: qrcodeToken.value as string
    }
    mobileVcode.open({ username: mobileForm.username, countryCode: mobileForm.phoneCountryCode, scene: 'bind_mobile', headers: headers }).then((res: any) => {
        mobileForm.vcode = ''
        mobileForm.token = res.token
    }).catch(() => {
    })
}

// 提交补充手机号
const submitMobile = () => {
    mobileLoading.value = true
    const baseHeaders = $http.getHeaders()
    if (qrcodeToken.value) {
        baseHeaders['Authorization'] = qrcodeToken.value
    }

    $http.axios.post('/app/user/api/User/bindMobile', mobileForm, {
        headers: {
            ...baseHeaders,
            Authorization: qrcodeToken.value as string
        },
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success('登录成功');
            const finalData = {
                ...qrcodeLoginData.value,
                mobile: mobileForm.username
            }
            userStore.setUserInfo(finalData).then(() => {
                needMobile.value = false
                qrcodeToken.value = null
                emit('success', finalData)
            }).catch(() => {
                ElMessage.error('登录失败')
            })
        } else {
            ElMessage.error(res.msg)
        }
    }).catch((error: any) => {
        const res = error?.response?.data || error
        ElMessage.error(res?.msg || '绑定手机号失败')
    }).finally(() => {
        mobileLoading.value = false
    })
}
const getVcode = () => {
    vcode.open({ username: form.username, countryCode: form.phoneCountryCode, scene: 'signup' }).then((res: any) => {
        form.vcode = ''
        form.token = res.token
    }).catch(() => {
    })
}

// 动态获取登录背景图片URL
const loginBackgroundImageUrl = computed(() => {
    return WEBCONFIG.value?.login_background_image_url || '/aimovie/static/image/login-image.png'
})
</script>
<template>
    <div class="x-login">
        <div class="x-login-image">
            <el-image :src="loginBackgroundImageUrl" class="x-login-image-img" />
        </div>
        <div class="x-login-form">
            <el-icon class="x-login-form-close" @click="close">
                <Close />
            </el-icon>
            <template v-if="activeTabs !== 'qrcode'">
                <el-segmented v-model="activeTabs" :options="tabs" class="tabs-segmented border" />
                <div class="x-login-form-content">
                    <template v-if="activeTabs === 'login'">
                        <el-input v-model="form.username" placeholder="账号/手机号/邮箱" @keyup.enter="login">
                            <template #prepend>
                                <el-icon size="20" color="var(--el-bg-color)">
                                    <User />
                                </el-icon>
                            </template>
                        </el-input>
                        <el-input type="password" v-model="form.password" placeholder="请输入密码" @keyup.enter="login">
                            <template #prepend>
                                <el-icon size="20" color="var(--el-bg-color)">
                                    <Lock />
                                </el-icon>
                            </template>
                        </el-input>
                    </template>
                    <template v-else-if="activeTabs === 'vcode'">
                        <el-input v-model="form.username" placeholder="手机号" @keyup.enter="login" :maxlength="11">
                            <template #prepend>
                                <el-select v-model="form.phoneCountryCode"
                                    popper-style="--el-bg-color-overlay:rgba(247, 247, 247, 1);--el-border-color-light:rgba(247, 247, 247, 1);--el-text-color-regular:rgba(14, 14, 14, 1);--el-fill-color-light:var(--el-text-color-primary);">
                                    <el-option v-for="item in phoneCountryCodeOptions" :key="item.value"
                                        :label="item.label" :value="item.value" />
                                </el-select>
                            </template>
                        </el-input>
                        <el-input v-model="form.vcode" placeholder="请输入验证码" @keyup.enter="login" :maxlength="6">
                            <template #prepend>
                                <el-icon size="20" color="var(--el-bg-color)">
                                    <IconSecuritySvg />
                                </el-icon>
                            </template>
                            <template #append>
                                <el-button type="primary" class="vcode-button" :disabled="vcodeBtnDisabled"
                                    @click="getVcode">{{
                                        vcode.btnText }}</el-button>
                            </template>
                        </el-input>
                    </template>
                    <template v-else-if="activeTabs === 'register'">
                        <el-input v-model="registerForm.username" placeholder="请输入用户名（4-30位字母数字）" @keyup.enter="registerSubmit">
                            <template #prepend>
                                <el-icon size="20" color="var(--el-bg-color)">
                                    <User />
                                </el-icon>
                            </template>
                        </el-input>
                        <el-input type="password" v-model="registerForm.password" placeholder="请输入密码（5-30位）" @keyup.enter="registerSubmit">
                            <template #prepend>
                                <el-icon size="20" color="var(--el-bg-color)">
                                    <Lock />
                                </el-icon>
                            </template>
                        </el-input>
                        <el-input type="password" v-model="registerForm.vpassword" placeholder="请确认密码" @keyup.enter="registerSubmit">
                            <template #prepend>
                                <el-icon size="20" color="var(--el-bg-color)">
                                    <Lock />
                                </el-icon>
                            </template>
                        </el-input>
                    </template>
                    <el-button color="var(--el-bg-color)" @click="handleSubmit" class="x-login-form-login-button"
                        :disabled="submitDisabled" :loading="activeTabs === 'register' ? registerLoading : loading">
                        <span>{{ activeTabs === 'register' ? '确认注册' : '确认登录' }}</span>
                    </el-button>
                    <div class="x-login-other">
                        <div class="x-login-other-line"></div>
                        <span>其他方式登录</span>
                        <div class="x-login-other-line right"></div>
                    </div>
                    <div class="x-login-other-icons">
                        <el-icon alt="微信登录" class="x-login-other-icons-img" @click="switchToQrcode"
                            color="var(--el-color-success)">
                            <IconLoginWechatSvg />
                        </el-icon>
                    </div>
                </div>
            </template>
            <template v-else-if="activeTabs === 'qrcode' && !needMobile">
                <xl-qrcode-view url="/app/user/api/Login/qrcode" check="/app/user/api/Login/checkQrcode"
                    class="qrcode-view" @success="LoginRes" />
                <div class="x-login-other">
                    <div class="x-login-other-line"></div>
                    <span>其他方式登录</span>
                    <div class="x-login-other-line right"></div>
                </div>
                <div class="x-login-other-icons">
                    <el-icon alt="手机号登录" class="x-login-other-icons-img" @click="switchToLogin"
                        color="var(--el-bg-color)">
                        <IconLoginPhoneSvg />
                    </el-icon>
                </div>
            </template>
            <template v-else>
                <div class="x-login-form-content">
                    <div class="x-login-mobile-title">请补充手机号</div>
                    <el-input v-model="mobileForm.username" placeholder="手机号" @keyup.enter="submitMobile"
                        :maxlength="11">
                        <template #prepend>
                            <el-select v-model="mobileForm.phoneCountryCode"
                                popper-style="--el-bg-color-overlay:rgba(247, 247, 247, 1);--el-border-color-light:rgba(247, 247, 247, 1);--el-text-color-regular:rgba(14, 14, 14, 1);--el-fill-color-light:var(--el-text-color-primary);">
                                <el-option v-for="item in phoneCountryCodeOptions" :key="item.value" :label="item.label"
                                    :value="item.value" />
                            </el-select>
                        </template>
                    </el-input>
                    <el-input v-model="mobileForm.vcode" placeholder="请输入验证码" @keyup.enter="submitMobile"
                        :maxlength="6">
                        <template #prepend>
                            <el-icon size="20" color="var(--el-bg-color)">
                                <IconSecuritySvg />
                            </el-icon>
                        </template>
                        <template #append>
                            <el-button type="primary" class="vcode-button" :disabled="mobileVcodeBtnDisabled"
                                @click="getMobileVcode">{{
                                    mobileVcode.btnText }}</el-button>
                        </template>
                    </el-input>
                    <el-button color="var(--el-bg-color)" @click="submitMobile" class="x-login-form-login-button"
                        :disabled="mobileSubmitDisabled" :loading="mobileLoading">
                        <span>确认</span>
                    </el-button>
                </div>
            </template>
            <div class="x-login-form-agreement">
                <span>登录即代表阅读并同意</span>
                <el-link href="/#/article/user"  type="success" target="_blank" underline="never">《用户协议》</el-link>
                <span>和</span>
                <el-link href="/#/article/privacy"  type="success" target="_blank" underline="never">《隐私政策》</el-link>
            </div>
        </div>
    </div>
</template>
<style scoped lang="scss">
.x-login {
    width: 100%;
    height: var(--el-messagebox-height);
    display: flex;
    --x-login-image-width: 375px;

    .x-login-image {
        width: var(--x-login-image-width);
        height: 100%;

        .x-login-image-img {
            width: 100%;
            height: 100%;
        }
    }

    .x-login-form {
        width: calc(100% - var(--x-login-image-width));
        height: 100%;
        background-color: #FFFFFF;
        position: relative;
        padding: 20px;
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

        .x-login-other {
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;

            .x-login-other-line {
                flex: 1;
                height: 1px;
                background-color: rgba(60, 60, 67, 0.12);
                background: linear-gradient(to right, rgba(60, 60, 67, 0), rgba(60, 60, 67, 0.12));

                &.right {
                    background: linear-gradient(to right, rgba(60, 60, 67, 0.12), rgba(60, 60, 67, 0));
                }
            }

            span {
                font-size: 12px;
                color: rgba(60, 60, 67, 0.60);
            }

        }

        .x-login-other-icons {
            .x-login-other-icons-img {
                font-size: 50px;
                width: 60px;
                height: 60px;
                cursor: pointer;
            }
        }

        .x-login-form-content {
            flex: 1;
            width: 315px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 20px;

            .x-login-mobile-title {
                font-size: 18px;
                font-weight: 600;
                color: var(--el-color-black);
                margin-bottom: 10px;
            }

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

                .el-select {
                    width: 65px;

                    .el-select__suffix {
                        display: none;
                    }
                }
            }

            .x-login-form-login-button {
                width: 100%;
                height: 50px;
                line-height: 50px;
                border-radius: 12px;
            }

            .vcode-button {
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 2px;
                color: var(--el-bg-color-overlay);

                &.disabled,
                &:disabled {
                    color: var(--el-text-color-disabled);
                }
            }
        }

        .x-login-form-agreement {
            font-size: 12px;
            color: rgba(60, 60, 67, 0.60);
            text-align: center;

            :deep(.el-link) {
                // --el-link-text-color: rgba(60, 60, 67, 0.60);
                --el-link-font-size: 12px;
                vertical-align: unset;
            }
        }
    }

    .qrcode-view {
        --el-text-color-primary: var(--el-bg-color);
    }
}
</style>