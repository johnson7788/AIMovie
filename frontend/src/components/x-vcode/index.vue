<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { ElMessage } from 'element-plus';

const props = withDefaults(defineProps<{
    data: any
}>(), {
    data: () => ({}),
});

const emit = defineEmits(['success', 'close'])
const close = () => {
    emit('close')
}
const form = reactive({
    username: '',
    captcha: '',
    token: null,
    ...props.data,
})
const captcha = ref('')
const getCaptcha = () => {
    $http.get('/app/user/api/Captcha/captcha_json').then((res: any) => {
        if (res.code === 200) {
            captcha.value = res.data.base64
            form.token = res.data.token
        }
    })
}
const loading = ref(false)
const sendCode = () => {
    loading.value = true
    console.log(props.data.headers)
    const headers = {
        ...props.data.headers
    }
    $http.post('/app/control/api/Public/getSmsVcode', form, { headers: headers }).then((res: any) => {
            if (res.code === ResponseCode.SUCCESS) {
                emit('success', { token: form.token })
                ElMessage.success(res.msg)
            } else {
                ElMessage.error(res.msg)
            }
        }).finally(() => {
            loading.value = false
        })
}
onMounted(() => {
    getCaptcha()
})
</script>
<template>
    <div class="x-vcode">
        <div class="x-vcode-form">
            <span>发送至：{{ data.countryCode }} {{ data.username }}</span>
            <el-input v-model="form.captcha" placeholder="请输入图形验证码" @keyup.enter="sendCode" :disabled="loading">
                <template #append>
                    <el-image :src="captcha" class="x-login-form-captcha-img" alt="验证码" title="点击更换验证码"
                        @click="getCaptcha" />
                </template>
            </el-input>
        </div>
        <div>
            <el-button @click="close" :disabled="loading">取消</el-button>
            <el-button type="primary" @click="sendCode" :loading="loading">获取验证码</el-button>
        </div>
    </div>
</template>
<style scoped lang="scss">
.x-vcode {
    width: 100%;
    height: var(--el-messagebox-height);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 20px;
    padding: 20px;

    .x-vcode-form {
        flex: 1;
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        justify-content: center;
        gap: 20px;
    }

    :deep(.el-input) {
        --el-input-height: 50px;
        --el-input-border-radius: 12px;
        font-weight: 600;

        .x-login-form-captcha-img {
            width: 100%;
            height: 48px;
        }
    }
}
</style>