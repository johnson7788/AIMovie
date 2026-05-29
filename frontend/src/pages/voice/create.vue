<template>
    <div class="p-8">
        <div class="flex flex-y-center flex-x-space-between grid-gap-4 p-10">
            <div class="flex-1 flex flex-flex-start">
                <div class="flex grid-gap-4 flex-y-center pointer" @click="router.push('/user')">
                    <el-icon size="18">
                        <Back />
                    </el-icon>
                    <span class="h8 font-weight-600">新增音色</span>
                </div>
            </div>
        </div>
        <div class="flex flex-center">
            <div class="flex  flex-1  grid-gap-4 flex-column box">
                <div class="flex flex-center ">
                    <el-segmented v-model="action" :options="options" class="tabs" />
                </div>
                <div class="h9 text-info bg-overlay mt-8 rounded-4 p-4 flex flex-y-center grid-gap-2">
                    <el-icon size="16">
                        <IconTips />
                    </el-icon>
                    {{ action === 'online' ? '为了获得更理想的效果，安静的环境下录制~' : '请确保上传文件只包含一个人的声音，请尽量保证上传音频的音质和背景干净' }}
                </div>
                <div class="bg-overlay rounded-4 p-4 w-100 mt-6">
                    <p v-if="currentScript?.text" class="script-text">{{ currentScript.text }}</p>
                    <p v-else class="script-text text-secondary">加载中...</p>
                    <div class="flex flex-x-flex-end flex-y-center grid-gap-2 text-success pointer"
                        @click="changeScript" :class="{ 'loading': scriptLoading }">
                        <el-icon size="16" :class="{ 'is-loading': scriptLoading }">
                            <RefreshRight />
                        </el-icon>
                        换一个
                    </div>
                </div>
                <div class="flex ">
                    <div class="flex flex-y-center flex-x-space-between input-button " ref="modelButtonRef">
                        <template v-if="!form.model_id">
                            <div class="flex flex-center grid-gap-2 ">
                                <el-icon size="20" color="var(--el-color-white)">
                                    <IconModel />
                                </el-icon>
                                <span class="h10">选择模型</span>
                            </div>
                        </template>
                        <template v-else>
                            <div class="flex flex-y-center grid-gap-2 flex-1">
                                <el-avatar :src="selectedModel.icon" :alt="selectedModel.name" shape="circle"
                                    class="icon-model"></el-avatar>
                                <span class="h10 text-ellipsis-1">{{ selectedModel.name }}</span>
                            </div>
                            <el-icon size="16" color="var(--el-text-color-secondary)"
                                class="model-item-selected-icon font-weight-600"
                                @click.stop="form.model = ''; selectedModel = { id: '' }">
                                <Close />
                            </el-icon>
                        </template>
                    </div>
                </div>

                <div v-if="action === 'online'" class="w-100">
                    <div class="flex-1 w-100">
                        <ol class="list text-secondary h10 ">
                            <li>请保持周围无噪音和其他声音，录制时长至少10秒；</li>
                            <li>参考文案仅供参考，无需逐字读，可随意发挥；</li>
                        </ol>
                    </div>

                    <div class="flex-1 w-100">
                        <RecordingComponent @success="handleRecordingSuccess" @confirm="handleRecordingConfirm" />
                    </div>
                </div>

                <!-- 上传音频组件 -->
                <div class="flex-1 w-100" v-else>
                    <div class="upload-page">
                        <el-upload class="upload-box" drag v-if="!uploadSuccess.filename" :auto-upload="false"
                            :show-file-list="false" :limit="1" :on-change="handleFileChange" :disabled="uploading">
                            <template v-if="!uploadSuccess.filename">
                                <div v-if="uploading" class="upload-loading">
                                    <el-icon class="upload-loading-icon is-loading">
                                        <Loading />
                                    </el-icon>
                                    <div class="upload-text">正在处理中...</div>
                                    <div class="upload-subtext">请稍候</div>
                                </div>
                                <template v-else>
                                    <el-icon class="upload-icon">
                                        <UploadFilled />
                                    </el-icon>
                                    <div class="upload-text">点击或拖拽上传 MP3/WAV/M4A 音频</div>
                                    <div class="upload-subtext">建议音频时长 10-300s，大小不超过20MB</div>
                                </template>
                            </template>
                        </el-upload>

                        <div class="upload-success" v-else>
                            <button class="audio-btn play-btn" @click="handlePlayAudio">
                                <el-icon size="18" :class="{ 'ml-1': !isAudioPlaying }">
                                    <IconPlay1 v-if="!isAudioPlaying" />
                                    <IconPause v-else />
                                </el-icon>
                            </button>
                            <div class="audio-info">
                                <div class="audio-name">{{ uploadSuccess.filename }}</div>
                                <div class="audio-meta">{{ uploadSuccess.sizeText }} | {{
                                    uploadSuccess.durationText }}</div>
                            </div>
                            <button class="audio-btn delete-btn" @click="handleDeleteAudio">
                                <el-icon>
                                    <Delete />
                                </el-icon>
                            </button>
                        </div>
                        <div class="upload-actions">
                            <el-button class="clone-btn" color="var(--el-color-success)" size="large"
                                :disabled="!canClone" :loading="cloneLoading" @click="handleClone">
                                立即克隆
                            </el-button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <el-popover ref="modelPopoverRef" :show-arrow="false" popper-class="model-popover" :virtual-ref="modelButtonRef"
            virtual-triggering placement="bottom" width="min(100vw,380px)" trigger="click">
            <xl-models v-model="form.model" @select="handleModelSelect" scene="dialogue_voice" />
        </el-popover>
        <Edit ref="editVoiceRef" />
    </div>
</template>
<script setup lang="ts">
import { useRouter } from 'vue-router'
import IconTips from '@/svg/icon/icon-tips.vue'
import { RefreshRight, UploadFilled, Delete, Loading } from '@element-plus/icons-vue'
import { $http } from '@/common/http'
import { ResponseCode } from '@/common/const'
import { ElLoading, ElMessage } from 'element-plus'
import RecordingComponent from './modules/recording.vue'
import IconPlay1 from '@/svg/icon/icon-play-1.vue'
import IconPause from '@/svg/icon/icon-pause.vue'
import IconModel from '@/svg/icon/icon-model.vue'
import { usePush } from '@/composables/usePush'
import { useUserStore, useRefs } from '@/stores'
import Edit from './modules/edit.vue'
const router = useRouter()
const userStore = useUserStore()
const { USERINFO } = useRefs(userStore)
const { subscribe, unsubscribeAll } = usePush()
let uuids: string[] = []
const action = ref('online')
const options = ref([
    { label: '在线录制', value: 'online' },
    { label: '上传音频', value: 'upload' },
])
const form = ref<any>({
    model_id: '',
    text_id: '',
    file: null,
    voice_id: null
})
// 上传音频
const uploadSuccess = ref<{ url?: string; filename?: string; size?: number; sizeText?: string; duration?: number; durationText?: string; localUrl?: string }>({})
const cloneLoading = ref(false)
const isAudioPlaying = ref(false)
const audioElement = ref<HTMLAudioElement | null>(null)
const uploading = ref(false) // 上传中状态（用于获取时长时的loading）
const canClone = computed(() => !!form.value.file)
const editVoiceRef = ref<any>(null)


const modelButtonRef = ref();
const modelPopoverRef = ref();
const selectedModel = ref<any>({});
const handleModelSelect = (item: any) => {
    selectedModel.value = item;
    form.value.model_id = item?.id || '';
    modelPopoverRef.value?.hide();
}

const fileSizeToStr = (size: number) => {
    if (!size && size !== 0) return ''
    const mb = size / 1024 / 1024
    if (mb >= 1) return `${mb.toFixed(2)}MB`
    const kb = size / 1024
    return `${kb.toFixed(0)}KB`
}

// 处理文件选择（不实际上传，只保存到本地）
const handleFileChange = async (uploadFile: any) => {
    const file = uploadFile.raw || uploadFile

    if (!file || !(file instanceof File)) {
        ElMessage.error('无法获取文件信息')
        return
    }

    // 验证文件类型和大小
    // const maxSizeMb = 20
    // const okSize = file.size / 1024 / 1024 <= maxSizeMb
    const okType = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 'audio/mp4', 'audio/x-m4a', 'audio/aac', 'audio/webm'].includes(file.type)
        || /\.(mp3|wav|m4a)$/i.test(file.name)

    if (!okType) {
        ElMessage.error('仅支持上传 MP3/WAV/M4A 音频')
        return
    }
    // if (!okSize) {
    //     ElMessage.error(`音频大小不能超过 ${maxSizeMb}MB`)
    //     return
    // }

    // 保存文件对象到 form.file
    form.value.file = file

    // 创建本地URL用于预览
    const localUrl = URL.createObjectURL(file)

    // 显示loading，获取音频时长
    uploading.value = true
    let duration = 0
    let durationText = '00:00'
    try {
        duration = await getAudioDuration(file)
        durationText = formatDuration(duration)
    } catch (error) {
        console.error('获取音频时长失败:', error)
    } finally {
        uploading.value = false
    }

    // 保存文件信息到本地
    uploadSuccess.value = {
        localUrl, // 本地URL用于预览播放
        filename: file.name,
        size: file.size,
        sizeText: fileSizeToStr(file.size),
        duration,
        durationText,
    }

    ElMessage.success('文件已选择，点击"立即克隆"提交')
}

// 获取音频时长
const getAudioDuration = (file: File | Blob): Promise<number> => {
    return new Promise((resolve, reject) => {
        // 验证文件对象
        if (!file || !(file instanceof File) && !(file instanceof Blob)) {
            reject(new Error('无效的文件对象'))
            return
        }

        try {
            const audio = new Audio()
            const objectUrl = URL.createObjectURL(file)
            audio.src = objectUrl

            const cleanup = () => {
                URL.revokeObjectURL(objectUrl)
                audio.removeEventListener('loadedmetadata', onLoaded)
                audio.removeEventListener('error', onError)
            }

            const onLoaded = () => {
                const duration = Math.floor(audio.duration) || 0
                cleanup()
                resolve(duration)
            }

            const onError = (error: any) => {
                console.error('加载音频元数据失败:', error)
                cleanup()
                resolve(0) // 失败时返回0，不抛出错误
            }

            audio.addEventListener('loadedmetadata', onLoaded, { once: true })
            audio.addEventListener('error', onError, { once: true })

            // 设置超时，避免长时间等待
            setTimeout(() => {
                if (audio.readyState === 0) {
                    cleanup()
                    resolve(0)
                }
            }, 5000)
        } catch (error) {
            reject(error)
        }
    })
}

// 格式化时长
const formatDuration = (seconds: number): string => {
    if (!seconds || seconds === 0) return '00:00'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

// 播放/暂停音频
const handlePlayAudio = () => {
    const audioUrl = uploadSuccess.value.localUrl || uploadSuccess.value.url
    if (!audioUrl) return

    if (!audioElement.value) {
        audioElement.value = new Audio(audioUrl)
        audioElement.value.onended = () => {
            isAudioPlaying.value = false
        }
        audioElement.value.onpause = () => {
            isAudioPlaying.value = false
        }
        audioElement.value.onplay = () => {
            isAudioPlaying.value = true
        }
    }

    if (isAudioPlaying.value) {
        audioElement.value.pause()
    } else {
        audioElement.value.play()
    }
}

// 删除音频
const handleDeleteAudio = () => {
    ElMessageBox.confirm('确定要删除该音频吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
    }).then(() => {
        if (audioElement.value) {
            audioElement.value.pause()
            audioElement.value = null
        }
        isAudioPlaying.value = false
        // 释放本地URL
        if (uploadSuccess.value.localUrl) {
            URL.revokeObjectURL(uploadSuccess.value.localUrl)
        }
        uploadSuccess.value = {}
        form.value.file = null // 清除保存的文件对象
        ElMessage.success('已删除')
    }).catch(() => { })
}
const voice_id = ref(0)
let loadingInstance: any = null

// 添加事件监听
const addListener = () => {
    subscribe('private-clonevoice-' + USERINFO.value?.user, (res: any) => {
        if (uuids.includes(res.id)) {
            if (res.status === 'success') {
                ElMessage.success(res.msg || '克隆成功')
                editVoiceRef.value.open(res.id)
                voice_id.value = 0;
                form.value = {
                    model_id: '',
                    text_id: '',
                    file: null,
                    voice_id: null
                }
                if (loadingInstance) {
                    loadingInstance.close()
                    loadingInstance = null
                }
            } else if (res.status === 'fail') {
                ElMessage.error(res.msg || '克隆失败')
                if (loadingInstance) {
                    loadingInstance.close()
                    loadingInstance = null
                }
            }
        }
    })
}

const handleClone = async () => {
    if (!canClone.value || !form.value.file) return
    await handleCloneWithFile(form.value.file)
}

// 文案相关
const scriptList = ref<any[]>([]) // 保存完整的文案对象列表
const currentScript = ref<any>(null) // 保存当前选择的文案对象（包含id和text）
const scriptLoading = ref(false)

// 获取文案列表
const getScriptList = async () => {
    try {
        scriptLoading.value = true
        const res: any = await $http.get('/app/model/api/VoiceText/index')
        if (res.code === ResponseCode.SUCCESS) {
            const data = res.data || []
            // 处理不同的数据格式：可能是字符串数组或对象数组
            if (Array.isArray(data)) {
                scriptList.value = data.map((item: any) => {
                    // 如果是字符串，转换为对象格式
                    if (typeof item === 'string') {
                        return { id: null, text: item }
                    }
                    // 如果是对象，保持原样（应该包含id和text/content等字段）
                    return {
                        id: item.id,
                        text: item.text || item.content || item.script || item.name || ''
                    }
                }).filter((item: any) => item.text)
            } else {
                scriptList.value = []
            }

            if (scriptList.value.length > 0) {
                // 随机选择一个文案
                changeScript()
            } else {
                currentScript.value = null
            }
        } else {
            ElMessage.error(res.msg || '获取文案列表失败')
            currentScript.value = null
        }
    } catch (error: any) {
        console.error('获取文案列表失败:', error)
        ElMessage.error('获取文案列表失败')
        currentScript.value = null
    } finally {
        scriptLoading.value = false
    }
}

// 切换文案
const changeScript = () => {
    if (scriptList.value.length === 0) {
        ElMessage.warning('暂无可用文案')
        return
    }

    if (scriptList.value.length === 1) {
        currentScript.value = scriptList.value[0]
        return
    }

    // 随机选择一个文案，确保与当前文案不同
    let newScript = currentScript.value
    let attempts = 0
    while (newScript?.id === currentScript.value?.id && attempts < 10) {
        const randomIndex = Math.floor(Math.random() * scriptList.value.length)
        newScript = scriptList.value[randomIndex]
        attempts++
    }
    currentScript.value = newScript
    form.value.text_id = newScript?.id || ''
}

// 处理录音成功
const handleRecordingSuccess = (data: any) => {
    console.log('录音成功:', data)
}

// 处理录音确认并克隆
const handleRecordingConfirm = async (data: any) => {
    if (!data || !data.file) {
        ElMessage.error('录音数据无效')
        return
    }

    // 验证文件大小
    // const maxSizeMb = 20
    // const fileSizeMb = data.file.size / 1024 / 1024
    // if (fileSizeMb > maxSizeMb) {
    //     ElMessage.error(`音频大小不能超过 ${maxSizeMb}MB`)
    //     return
    // }

    // 验证录制时长（至少10秒）
    if (data.duration < 5) {
        ElMessage.warning('录制时长至少需要10秒，请重新录制')
        return
    }

    // 保存文件到 form
    form.value.file = data.file
    form.value.text_id = form.value.text_id || currentScript.value?.id || ''

    // 调用克隆方法
    await handleCloneWithFile(data.file)
}

// 通用的克隆方法（支持文件和录音）
const handleCloneWithFile = async (file: File) => {
    if (!file) {
        ElMessage.error('请先选择或录制音频文件')
        return
    }

    cloneLoading.value = true

    loadingInstance = ElLoading.service({
        lock: true,
        text: '克隆中...',
        background: 'rgba(0, 0, 0, 0.7)',
    })

    try {
        // 创建FormData，包含文件和表单数据
        const formData = new FormData()
        formData.append('file', file)
        formData.append('text_id', form.value.text_id || '')
        
        // 如果有 model_id，也添加到表单中
        if (form.value.model_id) {
            formData.append('model_id', String(form.value.model_id))
        }

        // 提交到后端
        const res: any = await $http.post('/app/model/api/Voice/submit', formData)

        if (res.code === ResponseCode.SUCCESS) {
            uuids.push(res.data.voice_id)
            form.value.voice_id = res.data.voice_id
        } else {
            if (loadingInstance) {
                loadingInstance.close()
                loadingInstance = null
            }
            ElMessage.error(res.msg || '克隆失败')
        }
    } catch (error: any) {
        console.error('克隆失败:', error)
        if (loadingInstance) {
            loadingInstance.close()
            loadingInstance = null
        }
        ElMessage.error(error?.response?.data?.msg || error?.msg || '克隆失败，请稍后重试')
    } finally {
        cloneLoading.value = false
    }
}

// 页面加载时获取文案列表和添加事件监听
onMounted(() => {
    getScriptList()
    addListener()
})

// 组件卸载时清理音频资源和取消订阅
onUnmounted(() => {
    if (audioElement.value) {
        audioElement.value.pause()
        audioElement.value = null
    }
    // 释放本地URL
    if (uploadSuccess.value.localUrl) {
        URL.revokeObjectURL(uploadSuccess.value.localUrl)
    }
    // 关闭 loading
    if (loadingInstance) {
        loadingInstance.close()
        loadingInstance = null
    }
    // 取消所有订阅
    unsubscribeAll()
})
</script>
<style scoped lang="scss">
.el-segmented {
    --el-segmented-item-selected-color: var(--el-color-black);
    --el-segmented-item-selected-bg-color: var(--el-color-white);
    --el-border-radius-base: 8px;
    font-weight: bold;
}

:deep(.el-segmented__item) {
    padding: 4px 25px;
    font-size: 18px;
}

.box {
    max-width: 1000px;
}

.text-info {
    color: #ED9B43;
    display: inline-flex;
    width: 100%;
}

.script-text {
    line-height: 1.6;
    word-break: break-word;
    white-space: pre-wrap;
    min-height: 60px;
}

.pointer {
    cursor: pointer;
    transition: opacity 0.3s;

    &:hover {
        opacity: 0.8;
    }

    &.loading {
        opacity: 0.6;
        cursor: not-allowed;
    }
}

.upload-page {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.upload-box {
    width: 100%;
    border-radius: 12px;
    overflow: hidden;
    padding: 31px auto;

    :deep(.el-upload-dragger) {
        width: 100%;
        background: rgba(255, 255, 255, 0.06);
        border: 1px dashed rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        padding: 26px 12px;
    }

    .upload-icon {
        font-size: 26px;
        color: rgba(255, 255, 255, 0.8);
        margin-bottom: 16px;
    }

    .upload-text {
        color: rgba(255, 255, 255, 0.9);
        font-size: 14px;
        margin-bottom: 16px;
    }

    .upload-subtext {
        color: rgba(255, 255, 255, 0.6);
        font-size: 12px;
    }

    .upload-loading {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 20px 0;

        .upload-loading-icon {
            font-size: 32px;
            color: var(--el-color-success);
            margin-bottom: 16px;
            animation: rotating 2s linear infinite;
        }

        .upload-text {
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            margin-bottom: 8px;
        }

        .upload-subtext {
            color: rgba(255, 255, 255, 0.6);
            font-size: 12px;
        }
    }
}

@keyframes rotating {
    0% {
        transform: rotate(0deg);
    }

    100% {
        transform: rotate(360deg);
    }
}

.upload-success {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-direction: row;
    gap: 16px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    width: 100%;

    .audio-btn {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        border: none;
        background: rgba(0, 0, 0, 0.4);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        transition: all 0.3s;
        color: #fff;

        &:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: scale(1.05);
        }

        &:active {
            transform: scale(0.95);
        }

        .el-icon {
            font-size: 18px;
        }

        &.play-btn {
            .el-icon {
                font-size: 16px;
            }
        }

        &.delete-btn {
            margin-left: auto;
        }
    }

    .audio-info {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;
        min-width: 0;

        .audio-name {
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .audio-meta {
            color: rgba(255, 255, 255, 0.6);
            font-size: 12px;
        }
    }
}

.upload-label {
    color: rgba(255, 255, 255, 0.9);
    font-weight: 600;
    margin-top: 4px;
}

.trial-textarea {
    :deep(.el-textarea__inner) {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: rgba(255, 255, 255, 0.9);
        border-radius: 12px;
    }
}

.upload-actions {
    display: flex;
    justify-content: center;
    margin-top: 10px;
}

.clone-btn {
    width: 220px;
    border-radius: 12px;
    font-weight: 700;
}

.input-button {
    background: rgba(255, 255, 255, 0.08);
    cursor: pointer;
    border-radius: 30px;
    width: 251px;
    padding: 12px 20px;
    &:hover {
        background: rgba(255, 255, 255, 0.16);
    }
}

.icon-model {
    width: 20px;
    height: 20px;
}
</style>