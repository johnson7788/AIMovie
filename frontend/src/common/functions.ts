import { ElMessage } from "element-plus";
import { useWebConfigStore } from "@/stores";
import { i18n } from '@/locale';
const { t } = i18n.global;
/**
 * 节流函数会确保在指定的时间间隔内，函数被调用的次数不超过设定的阈值。
 * @param func 节流函数
 * @param wait 时间（毫秒）
 * @returns function
 */
export function throttle<F extends (...args: any[]) => void>(func: F, wait: number): F {
    let timer: ReturnType<typeof setTimeout> | undefined;
    return function (this: ThisParameterType<F>, ...args: Parameters<F>) {
        if (!timer) {
            timer = setTimeout(() => {
                timer = undefined;
                func.apply(this, args);
            }, wait);
        }
    } as F;
}
/**
 * 防抖函数会延迟函数的执行，直到一定的静默期过去后，才真正执行该函数。
 * @param func 防抖函数
 * @param wait 时间（毫秒）
 * @returns function
 */
export function debounce<F extends (...args: any[]) => void>(func: F, wait: number): F {
    let timer: ReturnType<typeof setTimeout> | undefined;
    return function (this: ThisParameterType<F>, ...args: Parameters<F>) {
        if (timer) {
            clearTimeout(timer);
        }
        timer = setTimeout(() => {
            timer = undefined;
            func.apply(this, args);
        }, wait);
    } as F;
}
/**
 * 监听浏览器滚动
 * @param func 回调函数
 * @param wait 回调频率
 */
export function onScroll<F extends (...args: any[]) => void>(func: F, wait: number = 0): void {
    let event = func;
    if (wait > 0) {
        event = debounce(func, wait);
    }
    const eventScroll = () => {
        const scrollTop = globalThis.pageYOffset || document.documentElement.scrollTop;
        event(scrollTop);
    }
    onMounted(() => {
        globalThis.addEventListener('scroll', eventScroll);
    });
    onUnmounted(() => {
        globalThis.removeEventListener('scroll', eventScroll);
    });
}
/**
 * 监听浏览器尺寸变化
 * @param func 回调函数
 * @param wait 回调频率
 */
export function onWindowResize<F extends (...args: any[]) => void>(func: F, wait: number = 0): void {
    let event = func;
    if (wait > 0) {
        event = debounce(func, wait);
    }
    const eventResize = () => {
        event({ w: globalThis.innerWidth, h: globalThis.innerHeight });
    }
    onMounted(() => {
        globalThis.addEventListener('resize', eventResize);
    });
    onUnmounted(() => {
        globalThis.removeEventListener('resize', eventResize);
    });
}
/**
 * 观察目标元素与其祖先元素或视窗之间的交叉状态。提供一种有效且高性能的方式来检测元素是否进入或离开视图区域。
 * @param el 元素
 * @param func 回调方法
 */
export function onObserve<F extends (...args: any[]) => void>(el: any, func: F): void {
    const done = (target: Element) => {
        observer.unobserve(target);
    }
    const observer = new IntersectionObserver((e) => {
        func(e, done);
    });
    onMounted(() => {
        el.value && observer.observe(el.value);
    });
    onUnmounted(() => {
        el.value && done(el.value);
    });
}
/**
 * 监听storage变化
 * @param key 监听的key
 * @param func 回调方法
 * @returns F() 
 * @example onStoreageChange('key',()=>{})
**/
export function onStoreageChange<F extends (...args: any[]) => void>(key: string, func: F): F {
    const event = (e: StorageEvent): any => {
        if (e.key === null) {
            func();
        } else if (e.key === key) {
            func(e);
        }
    }
    globalThis.addEventListener('storage', event);
    return function () {
        globalThis.removeEventListener('storage', event);
    } as F
}
/**
 * 秒转换为天时分秒
 * @param time 时间（秒）
 * @returns string
 */
export function timetostr(time: number | undefined): string {
    let str = '';
    if (!time) { return str }
    let d = 0, h = 0, m = 0, s = 0;
    if (time >= 3600 * 24) {
        d = Math.floor(time / (3600 * 24));
        time = time % (3600 * 24);
    }
    if (time >= 3600) {
        h = Math.floor(time / (60 * 60));
        time = time % (60 * 60);
    }
    if (time >= 60) {
        m = Math.floor(time / 60);
    }
    s = time % 60;
    if (d > 0) {
        str = d + t('date.day');
    }
    if (d > 0 || h > 0) {
        str += h + t('date.hour');
    }
    if (d > 0 || h > 0 || m > 0) {
        str += m + t('date.minute');
    }
    if (d > 0 || h > 0 || m > 0 || s > 0) {
        str += s + t('date.second');
    }
    return str
}
const copyText = (text: string) => {
    return new Promise<void>((resolve, reject) => {
        let input = document.createElement('input');
        input.value = text;
        document.body.appendChild(input);
        input.select();
        input.setSelectionRange(0, input.value.length);
        if (document.execCommand('Copy')) {
            resolve();
        } else {
            reject();
        }
        input.remove();
    })
}
/**
 * 设置剪切板内容
 * @param text 内容
 * @returns void
 */
export function setClipboard(text: string): void {
    if (navigator.clipboard && globalThis.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            ElMessage.success(t('message.copySuccess'));
        }).catch(() => {
            copyText(text).then(() => {
                ElMessage.success(t('message.copySuccess'));
            }).catch(() => {
                ElMessage.error(t('message.copyFail'));
            });
        });
    } else {
        copyText(text).then(() => {
            ElMessage.success(t('message.copySuccess'));
        }).catch(() => {
            ElMessage.error(t('message.copyFail'));
        });
    }
}
/**
 * 数字转千分位
 * @param num 数字
 * @returns string
 * @example 10000 => 10,000
 * @example 10000.123 => 10,000.123
 * @example 10000.123456 => 10,000.123456
 */
export function toThousands(num: number | string): string {
    let result = '', counter = 0;
    num = (num || 0).toString();
    for (let i = num.length - 1; i >= 0; i--) {
        counter++;
        result = num.charAt(i) + result;
        if (!(counter % 3) && i !== 0) { result = ',' + result; }
    }
    return result;
}
export function getRandomNumber(min: number, max: number): number {
    return Math.floor(Math.random() * (max - min + 1) + min);
}
export function openWin(url: string) {
    globalThis.open(url);
}
/**
 * 替换地址栏#参数不跳转
 * @param key 参数名
 * @param value 参数值
 * @returns void
 * @example replaceUrlParam('key','value')
 */
export function replaceUrlParam(key: string, value: string): void {
    const url = new URL(globalThis.location.href);
    url.searchParams.set(key, value);
    globalThis.history.replaceState({}, '', url.href);
}
/**
 * 批量替换地址栏#参数不跳转
 * @param params 参数对象
 * @returns void
 * @example replaceUrlParams({key1:'value1',key2:'value2'})
 */
export function replaceUrlParams(params: Record<string, string>): void {
    const url = new URL(globalThis.location.href);
    for (const key in params) {
        url.searchParams.set(key, params[key]);
    }
    globalThis.history.replaceState({}, '', url.href);
}
/**
 * 设置网站标题
 * @param title 标题
 * @returns void
 * @example setDocumentTitle('标题')
 */
export function setDocumentTitle(title: string): void {
    const { WEBCONFIG } = useWebConfigStore();
    let webName = WEBCONFIG.web_title;
    let subTitle = '';
    if (webName) {
        subTitle = ` - ${webName}`;
    }
    globalThis.document.title = `${title}${subTitle}`
}
/**
 * 分时函数
 * @param arr 数组
 * @param fn 回调函数
 * @returns {clear:()=>void}
 * @example timeChunk([1,2,3,4,5,6,7,8,9,10],(item)=>{console.log(item)})
 */
export function timeChunk<T>(arr: T[], fn: (item: T) => void): { clear: () => void } {
    let isBreak = false;
    const clear = () => {
        isBreak = true;
    }
    let i = 0;
    function _run() {
        globalThis.requestIdleCallback((idle) => {
            while (idle.timeRemaining() > 0 && i < arr.length) {
                fn(arr[i++]);
            }
            if (i < arr.length && isBreak === false) {
                _run();
            }
        })
    }
    if (arr.length > 0) _run();
    return {
        clear
    }
}
/**
 * 数字金额转中文大写
 * @param num 金额
 * @returns string
 * @example toChineseNumeral(10000) => 壹万
 * @example toChineseNumeral(10000.123) => 壹万零壹角贰分三厘
 */

export function toChineseNumeral(num: number): string {
    if (!num) {
        return '零元整';
    }
    const fraction = ['角', '分', '厘'];
    const digit = [
        '零', '壹', '贰', '叁', '肆',
        '伍', '陆', '柒', '捌', '玖'
    ];
    const unit = [
        ['元', '万 ', '亿 '],
        ['', '拾', '佰', '仟']
    ];
    let head = num < 0 ? '欠' : '';
    num = Math.abs(num);
    let s = '';
    for (let i = 0; i < fraction.length; i++) {
        s += (digit[Math.floor(num * 10 * Math.pow(10, i)) % 10] + fraction[i]).replace(/零./, '');
    }
    num = Math.floor(num);
    for (let i = 0; i < unit[0].length && num > 0; i++) {
        let p = '';
        for (let j = 0; j < unit[1].length && num > 0; j++) {
            p = digit[num % 10] + unit[1][j] + p;
            num = Math.floor(num / 10);
        }
        s = p.replace(/(零.)*零$/, '').replace(/^$/, '零') + unit[0][i] + s;
    }
    return head + s.replace(/(零.)*零元/, '元')
        .replace(/(零.)+/g, '零')
        .replace(/^整$/, '零元整');
}
export const getRoundImage = () => {
    return new Promise((resolve, reject) => {
        try {
            const xhr = new XMLHttpRequest();
            xhr.open('GET', 'https://picsum.photos/1920/1080?random', true);
            xhr.responseType = 'blob';
            xhr.onload = function () {
                if (this.status === 200) {
                    const blob = this.response;
                    return resolve({ blob: URL.createObjectURL(blob) });
                }
                reject();
            }
            xhr.send();
        } catch (e) {
            reject();
        }
    });
}
export const hasWhere = (extra: any, form: any): boolean => {
    if (!extra?.where) return true;
    // 把每一种比较集中到一个函数里，便于复用
    const match = (field: string, exp: string, value: any): boolean => {
        const formValue = getTableValue(form, field);
        if (Array.isArray(formValue) && Array.isArray(value)) {
            switch (exp) {
                case '=': return value.every(item => formValue.includes(item));
                case '!=': return !value.every(item => formValue.includes(item));
                case 'in': return value.some(item => formValue.includes(item));
                case 'not in': return !value.some(item => formValue.includes(item));
                default: return false;
            }
        } else if (Array.isArray(formValue)) {
            switch (exp) {
                case 'in': return formValue.includes(value);
                case 'not in': return !formValue.includes(value);
                default: return false;
            }
        } else {
            switch (exp) {
                case '=': return formValue === value;
                case '!=': return formValue !== value;
                case '>': return formValue > value;
                case '>=': return formValue >= value;
                case '<': return formValue < value;
                case '<=': return formValue <= value;
                case 'in': return Array.isArray(value) && value.includes(formValue);
                case 'not in': return Array.isArray(value) && !value.includes(formValue);
                case 'like': return typeof formValue === 'string' && formValue.includes(value);
                case 'not like': return typeof formValue === 'string' && !formValue.includes(value);
                case 'between': return formValue >= value[0] && formValue <= value[1];
                case 'not between': return formValue < value[0] || formValue > value[1];
                case 'null': return formValue === null;
                case 'not null': return formValue !== null;
                default: return false;
            }
        }
    };

    for (const condition of extra.where) {
        const [field] = condition;

        // --- AND 情况（field 是字符串） ---
        if (typeof field === 'string') {
            if (!match(field, condition[1], condition[2])) return false;
            continue;
        }

        // --- OR 情况（field 不是字符串）---
        // condition 形如：[[f1, op1, v1], [f2, op2, v2], ...]
        let anyPassed = false;
        for (const [subField, subExp, subVal] of condition as Array<[string, string, any]>) {
            if (match(subField, subExp, subVal)) {
                anyPassed = true;
                break;
            }
        }
        if (!anyPassed) return false;   // 整组 OR 都未命中
    }

    return true;  // 所有 AND/OR 条件全部满足
};

/**
 * 截取指定长度字符串
 * @param str 字符串
 * @param length 长度
 * @returns string
 * @example truncate('1234567890',5) => '12345'
 * @example truncate('abcdefg',3)=>'abc'
 * @example truncate('你好，世界！',1)=>'你'
 */
export function truncate(str: string, length: number, start: number = 0): string {
    if (!str) return '';
    // 如果长度大于字符串长度，则返回字符串
    if (length >= str.length) return str;
    // 如果取值不完整，则返回截取后的字符串
    return [...str].slice(start, start + length).join('');
}
/**
 * 递归取值
 * @param data 数据集（可以是任意层级的对象 / 数组）
 * @param keys 键数组——按顺序描述要深入的属性/索引路径
 * @returns 对应层级上的值；若路径不存在则返回 undefined | null
 */
export function deepGet<
    T = any,
    K extends ReadonlyArray<string | number | symbol> = Array<string | number | symbol>
>(data: any, keys: K): T | undefined | null {
    // ① 递归出口：keys 已取完，直接返回当前 data
    if (keys.length === 0) {
        return data as T;
    }

    // ② 安全判空：中途遇到 null / undefined 立即返回 undefined
    if (data === null) {
        return null;
    }
    if (data === undefined) {
        return undefined;
    }

    // ③ 递归深入：取出首键，继续在剩余子集上查找
    const [firstKey, ...restKeys] = keys;
    // 使用 `as any` 避免 TS “索引类型” 报错
    return deepGet<T>((data as any)[firstKey], restKeys);
}
/**
 * 根据点路径/下标递归取值
 * @param obj  任意对象/数组
 * @param path 如 'apps.title' | 'tags[0]'
 * @returns    对应值，路径不存在返 undefined
 */
export function getTableValue<T = any>(obj: any, path: string): T | undefined {
    if (!path) return obj as T;

    // 先把 tags[0] 这类写法转成 tags.0，便于统一 split
    const segments = path
        .replace(/\[(\d+)\]/g, '.$1')    // 把 [index] 转成 .index
        .split('.')
        .filter(Boolean);                // 过滤空串，防止连点

    let cur: any = obj;
    for (const key of segments) {
        if (cur == null) return undefined; // 短路判空
        cur = cur[key as keyof typeof cur];
    }
    return cur as T;
}
/**
 * 文件大小转换
 * @param size 文件大小
 * @returns string
 * @example fileSizeToStr(1024) => '1KB'
 * @example fileSizeToStr(1024*1024) => '1MB'
 * @example fileSizeToStr(1024*1024*1024) => '1GB'
 */
export function fileSizeToStr(size: number): string {
    if (size < 1024) {
        return size + 'B';
    }
    if (size < 1024 * 1024) {
        return (size / 1024).toFixed(2) + 'KB';
    }
    if (size < 1024 * 1024 * 1024) {
        return (size / 1024 * 1024).toFixed(2) + 'MB';
    }
    return (size / 1024 * 1024 * 1024).toFixed(2) + 'GB';
}
/**
 * 生成唯一ID
 * @param prefix 前缀
 * @param moreEntropy 是否更多熵
 * @returns string
 * @example uniqid() => '1719090240_abcdefg'
 * @example uniqid('prefix_') => 'prefix_1719090240_abcdefg'
 * @example uniqid('prefix_', true) => 'prefix_1719090240_abcdefg_hijklmn'
 */
export function uniqid(prefix: string = "", moreEntropy: boolean = false): string {
    return prefix + Date.now().toString(16) + (moreEntropy ? Math.random().toString(36).substring(2, 15) : '') + Math.random().toString(36).substring(2, 15);
}
/**
 * 格式化时间
 * @param ms 毫秒
 * @returns string
 * @example formatDuration(60) => '01:00'
 * @example formatDuration(60*60) => '01:00:00'
 */
export function formatDuration(ms: number): string {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const remainingSeconds = seconds % 60;
    const remainingMinutes = minutes % 60;
    const strArr = [remainingMinutes.toString().padStart(2, '0'), remainingSeconds.toString().padStart(2, '0')];
    if (hours) {
        strArr.unshift(hours.toString().padStart(2, '0'));
    }
    return strArr.join(':');
}