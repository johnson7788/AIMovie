import { buildApiUrl, getApiBaseUrl } from "./apiBaseUrl";
import { ElMessageBox } from "element-plus";
import { useStorage } from "@/composables/useStorage";
import axios, { AxiosResponse, AxiosError } from "axios";
import { useRefs, useStateStore, useUserStore, useWebConfigStore } from "@/stores";
import { getRoundImage } from "@/common/functions";
import { i18n } from '@/locale';
import { ResponseCode } from "./const";
import { useLogin } from "@/composables/useLogin";
const { t } = i18n.global;
const baseURL = getApiBaseUrl();
const getCompleteUrl = (path: string) => {
    return buildApiUrl(path);
}
const getHeaders = () => {
    const headers: any = {};
    const { hasLogin, getToken } = useUserStore();
    if (hasLogin()) {
        headers['Authorization'] = getToken();
    }
    const storage = useStorage();
    if (storage.get('ICODE')) {
        headers['X-ICODE'] = storage.get('ICODE') as string;
    }
    headers['X-Platform'] = 'pc';
    const stateStore = useStateStore();
    const { STATE } = useRefs(stateStore);
    const lang = STATE.value.language;
    headers['Accept-Language'] = lang;
    headers['lang'] = lang;
    if (import.meta.env.DEV) {
        headers['X-developer'] = 'true';
    }
    return headers;
}
axios.interceptors.request.use((_config) => {
    const headers = getHeaders();
    Object.keys(headers).forEach((key) => {
        _config.headers.set(key, headers[key as keyof typeof headers]);
    });
    _config.baseURL = baseURL;
    _config.timeout = 600000;
    return _config;
}, (error) => {
    return Promise.reject(error);
});
axios.interceptors.response.use((response: AxiosResponse) => {
    if (response?.data !== undefined) {
        const userStore = useUserStore()
        switch (response?.data?.code) {
            case ResponseCode.NEED_LOGIN:
                userStore.clearUserInfo();
                useLogin().open();
                break;
            case ResponseCode.SUCCESS_EVENT_PUSH:
                response.data.code = ResponseCode.SUCCESS;
                if (response.data.data.event) {
                    if (Array.isArray(response.data.data.event)) {
                        response.data.data.event.forEach((e: string) => {
                            $eventBus.emit(e);
                        })
                    } else {
                        $eventBus.emit(response.data.data.event);
                    }
                }
                break;
            case ResponseCode.NO_PERMISSION:
                showErrorBox(response.data);
                break;
        }
        return response.data;
    }
}, (error: AxiosError) => {
    if (import.meta.env.DEV && error.code != 'ERR_CANCELED') {
        showErrorBox({
            code: error.code,
            msg: error.message,
            data: {
                method: error.config?.method,
                url: error.config?.url,
            }
        });
    }
    return Promise.reject(error);
});
export const $http = {
    getCompleteUrl,
    getHeaders,
    getApiBaseUrl,
    buildApiUrl,
    get: axios.get,
    post: axios.post,
    axios
}
type EventListenerEntry = { callback: Function; wrapper: (e: Event) => void };
const eventListeners = new Map<string, Set<EventListenerEntry>>();
const eventOn = (event: string, callback: Function) => {
    if (!eventListeners.has(event)) {
        eventListeners.set(event, new Set());
    }
    const wrapper = (e: Event) => {
        callback((e as CustomEvent).detail);
    };
    eventListeners.get(event)!.add({ callback, wrapper });
    globalThis.addEventListener(event, wrapper);
}
const eventRemove = (event: string, callback: Function) => {
    const entries = eventListeners.get(event);
    if (!entries) return;
    for (const entry of entries) {
        if (entry.callback === callback) {
            globalThis.removeEventListener(event, entry.wrapper);
            entries.delete(entry);
        }
    }
}
const eventEmit = (event: string, data?: any) => {
    globalThis.dispatchEvent(new CustomEvent(event, { detail: data }))
}
export const $eventBus = {
    on: eventOn,
    emit: eventEmit,
    remove: eventRemove
}
export const showErrorBox = (res: any) => {
    if (import.meta.env.PROD) return;
    const content = [];
    if (res.code) {
        content.push(h('div', { class: 'flex py-2' }, [
            h('div', { class: 'text-grey text-right mr-2', style: { width: '100px' } }, t('message.error_code')),
            h('div', {}, res.code)
        ]))
    }
    content.push(h('div', { class: 'flex py-2' }, [
        h('div', { class: 'text-grey text-right mr-2', style: { width: '100px' } }, t('message.error_text')),
        h('div', {}, res.msg)
    ]))
    if (res.data) {
        for (const key in res.data) {
            if (Object.prototype.hasOwnProperty.call(res.data, key)) {
                const value = res.data[key];
                content.push(h('div', { class: 'flex py-2' }, [
                    h('div', { class: 'text-grey text-right mr-2', style: { width: '100px' } }, key),
                    h('div', { class: 'text-break-all' }, value)
                ]))
            }
        }
    }
    ElMessageBox({
        title: t('message.error'),
        message: h('div', {}, content),
    })
}
export const useLoginImageBuild = () => {
    const webConfigStore = useWebConfigStore();
    const { WEBCONFIG } = useRefs(webConfigStore);
    const Image = ref<string>(WEBCONFIG.value.login?.image);
    const BgImage = ref<string>('/static/bg.jpg');
    let BgImageEr: NodeJS.Timeout | undefined;
    const getLoginBg = () => {
        getRoundImage().then((res: any) => {
            BgImage.value = res.blob;
        })
    }
    onMounted(() => {
        switch (WEBCONFIG.value.login?.bg_image) {
            case 'off':
                BgImage.value = '';
                break;
            case 'auto':
                BgImageEr = setInterval(() => {
                    getLoginBg();
                }, 30000)
                break;
            default:
                if (WEBCONFIG.value.login) {
                    if (Array.isArray(WEBCONFIG.value.login?.bg_image)) {
                        BgImageEr = setInterval(() => {
                            if (WEBCONFIG.value.login) {
                                BgImage.value = WEBCONFIG.value.login?.bg_image[Math.floor(Math.random() * WEBCONFIG.value.login?.bg_image.length)];
                            }
                        }, 30000)
                    } else {
                        BgImage.value = WEBCONFIG.value.login?.bg_image;
                    }
                }
                break;
        }
    })
    onUnmounted(() => {
        clearTimer();
    })
    const clear = () => {
        BgImage.value = '';
    }
    const clearTimer = () => {
        if (BgImageEr) {
            clearInterval(BgImageEr);
            BgImageEr = undefined;
        }
    }
    return {
        BgImage,
        Image,
        clear
    };
}