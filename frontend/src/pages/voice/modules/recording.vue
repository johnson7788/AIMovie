<template>
    <div class="recording-container">
        <!-- 录制状态 -->
        <div v-if="recordingState === 'idle' || recordingState === 'recording'" class="recording-section">
            <!-- 录制按钮 -->
            <div class="record-button-wrapper">
                <button class="record-button" :class="{ 'recording': recordingState === 'recording' }"
                    @click="handleRecordClick" :disabled="!isHTTPS || !hasMicrophonePermission">
                    <el-icon v-if="recordingState === 'idle'" class="mic-icon">
                        <Microphone />
                    </el-icon>
                    <div v-else class="stop-icon"></div>
                </button>
            </div>

            <!-- 提示文字 -->
            <div class="record-tip" v-if="recordingState === 'idle'">
                点击开始录制
            </div>

            <!-- 计时器 -->
            <div class="timer" v-if="recordingState === 'recording'">
                {{ formatTime(recordingTime) }}
            </div>

            <!-- 协议文本 -->
            <div class="agreement-text">
                我已阅读并同意
                <el-link type="success" @click="showProtocol" class="protocol-link">
                    《声音克隆协议》
                </el-link>
            </div>
        </div>

        <!-- 试听状态 -->
        <div v-else-if="recordingState === 'review'" class="review-section">
            <div class="review-buttons">
                <!-- 重录按钮 -->
                <button class="review-btn" @click="handleRerecord">
                    <el-icon>
                        <RefreshRight />
                    </el-icon>
                </button>

                <!-- 播放按钮 -->
                <button class="review-btn play-btn" @click="handlePlay">
                    <el-icon size="30" :class="{ 'ml-1': !isPlaying }" color="#000">
                        <IconPlay1 v-if="!isPlaying" />
                        <IconPause v-else />
                    </el-icon>
                </button>

                <!-- 确认按钮 -->
                <button class="review-btn" @click="handleConfirm">
                    <el-icon size="20">
                        <Check />
                    </el-icon>
                </button>
            </div>

            <!-- 协议文本 -->
            <div class="agreement-text">
                我已阅读并同意
                <el-link type="success" @click="showProtocol" class="protocol-link">
                    《声音克隆协议》
                </el-link>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import IconPause from '@/svg/icon/icon-pause.vue'
import IconPlay1 from '@/svg/icon/icon-play-1.vue'
import { Microphone, RefreshRight } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const emit = defineEmits(['success', 'confirm'])

// 录制状态：idle(待录制) | recording(录制中) | review(试听)
const recordingState = ref<'idle' | 'recording' | 'review'>('idle')
const recordingTime = ref(0) // 录制时长（秒）
const isPlaying = ref(false)
const audioBlob = ref<Blob | null>(null)
const audioUrl = ref<string>('')
const audioElement = ref<HTMLAudioElement | null>(null)

let mediaRecorder: MediaRecorder | null = null
let audioStream: MediaStream | null = null
let timerInterval: NodeJS.Timeout | null = null

// HTTPS 检测
const isHTTPS = computed(() => {
    return location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1'
})

// 麦克风权限检测
const hasMicrophonePermission = ref(false)

// 检查麦克风权限
const checkMicrophonePermission = async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach(track => track.stop()) // 立即停止，只是检查权限
        hasMicrophonePermission.value = true
    } catch (error: any) {
        console.error('麦克风权限检查失败:', error)
        hasMicrophonePermission.value = false
        if (error.name === 'NotAllowedError') {
            ElMessage.warning('请允许访问麦克风权限')
        } else if (error.name === 'NotFoundError') {
            ElMessage.warning('未检测到麦克风设备')
        } else {
            ElMessage.warning('无法访问麦克风，请检查设备设置')
        }
    }
}

// 开始录制
const startRecording = async () => {
    try {
        // 检查 HTTPS
        if (!isHTTPS.value) {
            ElMessage.error('录音功能需要在 HTTPS 环境下使用')
            return
        }

        // 获取麦克风权限
        audioStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        })

        // 创建 MediaRecorder
        const chunks: BlobPart[] = []
        mediaRecorder = new MediaRecorder(audioStream, {
            mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
        })

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                chunks.push(event.data)
            }
        }

        mediaRecorder.onstop = () => {
            audioBlob.value = new Blob(chunks, { type: mediaRecorder?.mimeType || 'audio/webm' })
            audioUrl.value = URL.createObjectURL(audioBlob.value)
            recordingState.value = 'review'
        }

        // 开始录制
        mediaRecorder.start()
        recordingState.value = 'recording'
        recordingTime.value = 0

        // 启动计时器
        timerInterval = setInterval(() => {
            recordingTime.value++
            // 检查是否达到最小录制时长（10秒）
            if (recordingTime.value >= 10 && !mediaRecorder?.state.includes('recording')) {
                // 可以自动停止或提示
            }
        }, 1000)

    } catch (error: any) {
        console.error('开始录制失败:', error)
        ElMessage.error('开始录制失败，请检查麦克风权限')
        recordingState.value = 'idle'
    }
}

// 停止录制
const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop()
    }

    if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop())
        audioStream = null
    }

    if (timerInterval) {
        clearInterval(timerInterval)
        timerInterval = null
    }

    // 检查录制时长（至少10秒）
    if (recordingTime.value < 10) {
        ElMessage.warning('录制时长至少需要10秒，请重新录制')
        recordingState.value = 'idle'
        recordingTime.value = 0
        if (audioUrl.value) {
            URL.revokeObjectURL(audioUrl.value)
            audioUrl.value = ''
        }
        audioBlob.value = null
        return
    }
}

// 处理录制按钮点击
const handleRecordClick = () => {
    if (recordingState.value === 'idle') {
        startRecording()
    } else if (recordingState.value === 'recording') {
        stopRecording()
    }
}

// 格式化时间
const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

// 重录
const handleRerecord = () => {
    ElMessageBox.confirm('确定要重新录制吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
    }).then(() => {
        // 清理资源
        if (audioUrl.value) {
            URL.revokeObjectURL(audioUrl.value)
            audioUrl.value = ''
        }
        if (audioElement.value) {
            audioElement.value.pause()
            audioElement.value = null
        }
        isPlaying.value = false
        audioBlob.value = null
        recordingTime.value = 0
        recordingState.value = 'idle'
    }).catch(() => { })
}

// 播放/暂停
const handlePlay = () => {
    if (!audioUrl.value) return

    if (!audioElement.value) {
        audioElement.value = new Audio(audioUrl.value)
        audioElement.value.onended = () => {
            isPlaying.value = false
        }
        audioElement.value.onpause = () => {
            isPlaying.value = false
        }
        audioElement.value.onplay = () => {
            isPlaying.value = true
        }
    }

    if (isPlaying.value) {
        audioElement.value.pause()
    } else {
        audioElement.value.play()
    }
}

// 确认
const handleConfirm = () => {
    if (!audioBlob.value) {
        ElMessage.warning('请先完成录制')
        return
    }

    // 将 Blob 转换为 File 对象
    const fileName = `recording_${Date.now()}.${mediaRecorder?.mimeType?.includes('webm') ? 'webm' : 'mp4'}`
    const audioFile = new File([audioBlob.value], fileName, {
        type: mediaRecorder?.mimeType || 'audio/webm',
        lastModified: Date.now()
    })

    emit('confirm', {
        blob: audioBlob.value,
        file: audioFile,
        url: audioUrl.value,
        duration: recordingTime.value
    })
    emit('success', {
        blob: audioBlob.value,
        file: audioFile,
        url: audioUrl.value,
        duration: recordingTime.value
    })
}

// 显示协议
const showProtocol = () => {
    // TODO: 打开协议弹窗或跳转到协议页面
    ElMessage.info('协议功能待实现')
}

// 组件卸载时清理资源
onUnmounted(() => {
    if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop())
    }
    if (timerInterval) {
        clearInterval(timerInterval)
    }
    if (audioUrl.value) {
        URL.revokeObjectURL(audioUrl.value)
    }
    if (audioElement.value) {
        audioElement.value.pause()
        audioElement.value = null
    }
})

// 初始化时检查权限
onMounted(() => {
    checkMicrophonePermission()
})
</script>

<style scoped lang="scss">
.recording-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.recording-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
    width: 100%;
}

.record-button-wrapper {
    display: flex;
    justify-content: center;
    align-items: center;
}

.record-button {
    width: 65px;
    height: 65px;
    border-radius: 50%;
    border: none;
    background: var(--el-color-success);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s;
    box-shadow: 0 4px 20px rgba(103, 194, 58, 0.3);

    &:hover:not(:disabled) {
        transform: scale(1.05);
        box-shadow: 0 6px 25px rgba(103, 194, 58, 0.4);
    }

    &:active:not(:disabled) {
        transform: scale(0.95);
    }

    &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    &.recording {
        background: rgba(13, 242, 131, 0.08);
        animation: pulse 2s infinite;
    }

    .mic-icon {
        font-size: 38px;
        color: #000;
    }

    .stop-icon {
        width: 16px;
        height: 16px;
        background: var(--el-color-success);
        border-radius: 4px;
    }
}

@keyframes pulse {

    0%,
    100% {
        box-shadow: 0 4px 20px rgba(13, 242, 131, 0.3);
    }

    50% {
        box-shadow: 0 4px 30px rgba(13, 242, 131, 0.7);
    }
}

.record-tip {
    font-size: 16px;
    color: #fff;
    text-align: center;
}

.timer {
    font-size: 16px;
    color: #fff;
    font-variant-numeric: tabular-nums;
    letter-spacing: 2px;
}

.review-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 32px;
    width: 100%;
}

.review-title {
    font-size: 20px;
    font-weight: 600;
    color: #fff;
    text-align: center;
}

.review-buttons {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 24px;
}

.review-btn {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: none;
    background: rgba(255, 255, 255, 0.1);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s;
    color: #fff;

    &:hover {
        background: rgba(255, 255, 255, 0.2);
        transform: scale(1.1);
    }

    &:active {
        transform: scale(0.95);
    }

    .el-icon {
        font-size: 24px;
    }

    &.play-btn {
        width: 65px;
        height: 65px;
        background: var(--el-color-success);

        .el-icon {
            font-size: 32px;
        }

        &:hover {
            background: var(--el-color-success-dark-2);
        }
    }
}

.agreement-text {
    font-size: 14px;
    color: #fff;
    text-align: center;
    opacity: 0.8;

    .protocol-link {
        color: var(--el-color-success) !important;
        font-weight: 500;
        margin-left: 4px;

        &:hover {
            opacity: 0.8;
        }
    }
}
</style>
