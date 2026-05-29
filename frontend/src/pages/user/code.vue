<template>
    <div class="container">
        <div class="stars small" ref="smallStars"></div>
        <div class="stars big" ref="bigStars"></div>

        <div class="h1 font-weight-bold">填写邀请码</div>
        <div class="mt-7">
            <span>请输入邀请码</span>
        </div>
        <div class="grid-columns-6 grid-gap-6 mt-10 content" @click="handleContainerClick" @paste="handlePaste">
            <div v-for="(char, index) in codeArray" :key="index" class="flex flex-center flex-column item"
                :class="{ active: currentIndex === index }" @click="focusInput(index)">
                <input ref="inputRefs" v-model="codeArray[index]" type="text" maxlength="1" class="code-input"
                    @input="handleInput(index, $event)" @keydown="handleKeydown(index, $event)" @paste="handlePaste"
                    @focus="currentIndex = index" @blur="handleBlur" />
                <span class="code-char">{{ char || '' }}</span>
                <span v-if="currentIndex === index && !char" class="cursor"></span>
            </div>
        </div>
        <el-button class="btn" round color="var(--el-color-success)" size="large" :loading="loading"
            :disabled="!isCodeComplete" @click="handleSubmit">
            确定
        </el-button>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { $http } from '@/common/http'
import { ResponseCode } from '@/common/const'
import { useUserStore } from '@/stores' 
const router = useRouter()
const bigStars = ref<HTMLDivElement | null>(null)
const smallStars = ref<HTMLDivElement | null>(null)
const inputRefs = ref<(HTMLInputElement | null)[]>([])
const codeArray = ref<string[]>(['', '', '', '', '', ''])
const currentIndex = ref<number>(0)
const loading = ref(false)
const isPasting = ref(false)

const isCodeComplete = computed(() => {
    return codeArray.value.every(char => char.trim() !== '')
})

const generateStars = (count: number, width: number, height: number) => {
    return Array.from({ length: count }, () =>
        `${Math.random() * width}px ${Math.random() * height}px white`
    ).join(',')
}

const initStars = () => {
    const w = window.innerWidth
    const h = window.innerHeight

    if (bigStars.value) {
        bigStars.value.style.boxShadow = generateStars(50, w, h)
    }
    if (smallStars.value) {
        smallStars.value.style.boxShadow = generateStars(100, w, h)
    }
}

const focusInput = (index: number) => {
    currentIndex.value = index
    nextTick(() => {
        const input = inputRefs.value[index]
        if (input) {
            input.focus()
        }
    })
}

const handleContainerClick = (e: MouseEvent) => {
    const target = e.target as HTMLElement
    // 如果点击的是输入框本身，不需要处理
    if (target.classList.contains('code-input')) {
        return
    }
    // 如果点击的是容器内的其他元素，找到对应的item
    const item = target.closest('.item') as HTMLElement
    if (item) {
        const index = Array.from(item.parentElement?.children || []).indexOf(item)
        if (index !== -1) {
            focusInput(index)
        }
    }
}

const handleInput = (index: number, event: Event) => {
    // 如果正在处理粘贴，跳过单个输入处理
    if (isPasting.value) {
        return
    }

    const input = event.target as HTMLInputElement
    let value = input.value.toUpperCase().replace(/[^A-Z0-9]/g, '')

    if (value.length > 1) {
        value = value.slice(0, 1)
    }

    codeArray.value[index] = value
    input.value = value

    // 自动聚焦下一个输入框
    if (value && index < 5) {
        nextTick(() => {
            focusInput(index + 1)
        })
    }
}

const handleKeydown = (index: number, event: KeyboardEvent) => {
    const key = event.key

    // 检测 Ctrl+V 或 Cmd+V (Mac)
    if ((event.ctrlKey || event.metaKey) && key === 'v') {
        // 允许粘贴事件处理，不阻止默认行为（粘贴事件会处理）
        return
    }

    if (key === 'Backspace') {
        if (codeArray.value[index]) {
            codeArray.value[index] = ''
        } else if (index > 0) {
            focusInput(index - 1)
            codeArray.value[index - 1] = ''
        }
        event.preventDefault()
    } else if (key === 'ArrowLeft' && index > 0) {
        focusInput(index - 1)
        event.preventDefault()
    } else if (key === 'ArrowRight' && index < 5) {
        focusInput(index + 1)
        event.preventDefault()
    } else if (key === 'Delete') {
        codeArray.value[index] = ''
        event.preventDefault()
    } else if (key.length === 1 && /[A-Z0-9]/i.test(key) && !event.ctrlKey && !event.metaKey) {
        // 允许输入字母和数字，但排除 Ctrl/Cmd 组合键
        const value = key.toUpperCase()
        codeArray.value[index] = value
        if (index < 5) {
            nextTick(() => {
                focusInput(index + 1)
            })
        }
        event.preventDefault()
    }
}

const handlePaste = (event: ClipboardEvent) => {
    event.preventDefault()
    event.stopPropagation()

    isPasting.value = true

    const pastedText = event.clipboardData?.getData('text') || ''
    if (!pastedText) {
        isPasting.value = false
        return
    }

    const cleanText = pastedText.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6)

    if (!cleanText) {
        isPasting.value = false
        return
    }

    // 清空所有输入框
    codeArray.value = ['', '', '', '', '', '']

    // 填充粘贴的内容
    for (let i = 0; i < cleanText.length && i < 6; i++) {
        codeArray.value[i] = cleanText[i]
    }

    // 同步更新所有输入框的值
    nextTick(() => {
        inputRefs.value.forEach((input, index) => {
            if (input) {
                input.value = codeArray.value[index] || ''
            }
        })

        // 聚焦到最后一个已输入的框或第一个空框
        const nextIndex = Math.min(cleanText.length, 5)
        focusInput(nextIndex)

        // 重置粘贴标志
        setTimeout(() => {
            isPasting.value = false
        }, 200)
    })
}

const handleBlur = () => {
    // 延迟清除焦点索引，以便点击事件能正常触发
    setTimeout(() => {
        // 如果当前没有输入框获得焦点，则清除当前索引
        const activeElement = document.activeElement
        if (!activeElement || !activeElement.classList.contains('code-input')) {
            // 不清除，保持显示光标效果
        }
    }, 100)
}

const handleSubmit = async () => {
    if (!isCodeComplete.value) {
        ElMessage.warning('请输入完整的邀请码')
        return
    }

    const code = codeArray.value.join('')
    loading.value = true

    try {
        const res: any = await $http.post('/app/user/api/User/bindInvitationCode', { code })
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg || '邀请码使用成功');
            $http.get('/app/user/api/User/info').then((res: any) => {
                if (res.code === ResponseCode.SUCCESS) {
                    const userStore = useUserStore();
                    userStore.setUserInfo(res.data as UserInfoInterface);
                } else {
                }
            })
            // 延迟跳转，让用户看到成功消息
            setTimeout(() => {
                router.replace('/')
            }, 500)
        } else {
            ElMessage.error(res.msg || '邀请码使用失败')
        }
    } catch (error: any) {
        ElMessage.error(error?.msg || '邀请码使用失败，请稍后重试')
    } finally {
        loading.value = false
    }
}

const handleGlobalPaste = (event: ClipboardEvent) => {
    // 检查是否在邀请码输入区域内
    const activeElement = document.activeElement
    const target = event.target as HTMLElement
    const container = document.querySelector('.content')

    // 如果焦点在容器内，或者目标在容器内，则处理粘贴
    if (container && (
        (activeElement && container.contains(activeElement)) ||
        (target && container.contains(target)) ||
        (!activeElement && !target)
    )) {
        handlePaste(event)
    }
}

onMounted(() => {
    initStars()
    // 自动聚焦第一个输入框
    nextTick(() => {
        focusInput(0)
    })

    // 添加全局粘贴事件监听
    document.addEventListener('paste', handleGlobalPaste)
})

onUnmounted(() => {
    // 移除全局粘贴事件监听
    document.removeEventListener('paste', handleGlobalPaste)
})
</script>

<style scoped lang="scss">
.container {
    position: relative;
    width: 100vw;
    height: 100dvh;
    overflow: hidden;
    color: #fff;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;

    .btn {
        padding: 8px 100px;
        margin-top: 60px;
        transition: all 0.3s ease;

        &:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
    }

    .content {
        margin-top: 60px;
    }

    .item {
        position: relative;
        width: 71px;
        height: 71px;
        background: #1E1E1E;
        border-radius: 12px;
        border: 1px solid #272727;
        font-size: 29px;
        font-weight: 600;
        color: #FFFFFF;
        text-align: center;
        line-height: 71px;
        cursor: pointer;
        transition: all 0.3s ease;

        &:hover {
            background: #272727;
            border-color: #3a3a3a;
        }

        &.active {
            border-color: var(--el-color-success);
            background: #272727;
            box-shadow: 0 0 0 2px rgba(103, 194, 58, 0.2);
        }

        .code-input {
            position: absolute;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
            opacity: 0;
            cursor: pointer;
            border: none;
            background: transparent;
            color: transparent;
            caret-color: transparent;
            font-size: 0;
            z-index: 1;
        }

        .code-char {
            position: relative;
            z-index: 0;
            user-select: none;
        }

        .cursor {
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            width: 2px;
            height: 35px;
            background: var(--el-color-success);
            animation: blink 1s infinite;
            z-index: 2;
            pointer-events: none;
        }
    }
}

.stars {
    position: absolute;
    inset: 0;
    background: white;
    border-radius: 50%;
}

.stars.small {
    width: 1px;
    height: 1px;
    filter: blur(0.5px);
}

.stars.big {
    width: 2px;
    height: 2px;
    filter: blur(0.8px);
}

@keyframes blink {

    0%,
    50% {
        opacity: 1;
    }

    51%,
    100% {
        opacity: 0;
    }
}
</style>