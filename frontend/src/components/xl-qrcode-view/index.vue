<script lang="ts" setup>
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const props = withDefaults(defineProps<{
    qrcode?: any,
    url?: string,
    check?: string,
    size?: number | string
}>(), {
    size: 200
});
const emit = defineEmits(['success', 'retry']);
const form = ref({
    id: ''
});
const qrcode_content = ref();
let Inter: any;
const expire = ref();
const getQrcode = () => {
    if (!props.url) {
        return;
    }
    showError.value = undefined;
    $http.get(props.url).then((res: any) => {
        if (res.code === 200) {
            form.value.id = res.data.id;
            qrcode_content.value = res.data.qrcode;
            if (res.data.expire) {
                expire.value = new Date(res.data.expire * 1000).getTime();
            }
        } else {
            setQrcodeExpire(res.msg);
        }
    }).catch(() => {
        setQrcodeExpire(t('message.getQrcodeFail'));
    });
}
let timer: any;
const check = ref(false);
const checkLogin = () => {
    if (!props.check || check.value) {
        return;
    }
    if (timer) {
        clearTimeout(timer);
    }
    timer = undefined;
    $http.post(props.check, form.value).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            check.value = true;
            emit('success', res);
        } else if (res.code === ResponseCode.WAIT) {
            timer = setTimeout(() => {
                checkLogin();
            }, 1000);
        } else {
            check.value = true;
            setQrcodeExpire(res.msg);
        }
    }).catch((error) => {
        if (error.code != 'ERR_CANCELED') {
            setQrcodeExpire(error.message);
        }
    });
}
const showError = ref();
const setQrcodeExpire = (msg: string) => {
    expire.value = undefined;
    showError.value = msg;
}
const retry = () => {
    if (props.url) {
        getQrcode();
    } else {
        emit('retry');
    }
}
onMounted(() => {
    if (props.url) {
        getQrcode();
    } else if (props.qrcode) {
        form.value.id = props.qrcode.id;
        qrcode_content.value = props.qrcode.qrcode;
        if (props.qrcode.expire) {
            expire.value = new Date(props.qrcode.expire * 1000).getTime();
        }
    }
});
onUnmounted(() => {
    if (timer) {
        clearTimeout(timer);
    }
    if (Inter) {
        clearInterval(Inter);
    }
    qrcode_content.value = undefined;
});
</script>
<template>
    <div class="flex flex-column flex-y-center">
        <div class="qrcode" :style="[`width:${props.size}px;height:${props.size}px;`]">
            <xl-qrcode :text="qrcode_content" :size="Number(props.size)" @update="checkLogin"></xl-qrcode>
            <div class="error flex flex-column flex-center grid-gap-4" :class="{ 'show': showError }">
                <el-icon size="40" color="var(--el-color-danger)">
                    <CircleClose />
                </el-icon>
                <div class="text-white text-break-all">{{ showError }}</div>
                <el-link type="primary" @click="retry" underline="never">
                    {{ t('button.retryText') }}
                </el-link>
            </div>
        </div>
        <el-countdown class="flex flex-column flex-center" :title="t('message.qrcodeWillExpireTitle')" :value="expire"
            @finish="() => setQrcodeExpire(t('message.qrcodeExpireContent'))" v-if="expire" />
    </div>
</template>
<style lang="scss" scoped>
.qrcode {
    position: relative;
}

.error {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.75);
    display: none;

    &.show {
        display: flex;
    }
}
</style>