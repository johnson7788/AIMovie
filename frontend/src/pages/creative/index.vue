<script setup lang="ts">
import { ResponseCode } from '@/common/const'
import { $http } from '@/common/http'
import { useRefs, useUserStore, useModelStore } from '@/stores'
import { usePush } from '@/composables/usePush'
import { ElMessage } from 'element-plus'
import UploadSvg from '@/svg/icon/upload.vue'

const userStore = useUserStore()
const modelStore = useModelStore()
const { USERINFO } = useRefs(userStore)

const { subscribe, unsubscribeAll } = usePush()

// 表单
const imageUrl = ref('')
const prompt = ref('')
const duration = ref(5)
const resolution = ref('1080p')
const videoModel = ref<any>(null)
const videoModelId = ref('')
const uploading = ref(false)
const generating = ref(false)

// 任务列表
const taskList = ref<any[]>([])

// 图片上传
const handleUploadSuccess = (response: any) => {
    uploading.value = false
    if (response.code === ResponseCode.SUCCESS) {
        imageUrl.value = response.data.url
    } else {
        ElMessage.error(response.msg || '上传失败')
    }
}
const handleUploadError = () => {
    uploading.value = false
    ElMessage.error('上传失败')
}
const beforeUpload = () => {
    uploading.value = true
    return true
}
const removeImage = () => {
    imageUrl.value = ''
}

// 模型选择
const handleModelSelect = (model: any) => {
    videoModel.value = model
}

// 生成视频
const generate = async () => {
    if (!imageUrl.value) {
        ElMessage.warning('请上传参考图片')
        return
    }
    if (!videoModelId.value) {
        ElMessage.warning('请选择模型')
        return
    }
    generating.value = true
    try {
        const res: any = await $http.post('/app/shortplay/api/Creative/video', {
            image_url: imageUrl.value,
            prompt: prompt.value,
            duration: duration.value,
            resolution: resolution.value,
            model_id: videoModelId.value,
        })
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success('视频生成中，请稍候...')
            fetchTaskList()
        } else {
            ElMessage.error(res.msg || '生成失败')
        }
    } catch (e: any) {
        ElMessage.error(e.message || '生成失败')
    } finally {
        generating.value = false
    }
}

// 获取任务列表
const fetchTaskList = async () => {
    if (!userStore.hasLogin()) return
    try {
        const res: any = await $http.get('/app/model/api/Task/index', {
            params: {
                scene: 'creative_video',
                limit: 20,
            }
        })
        if (res.code === ResponseCode.SUCCESS) {
            taskList.value = res.data.data || []
        }
    } catch (e) {
        console.error(e)
    }
}

// 获取任务状态文本和类型
const getStatusInfo = (status: string) => {
    const map: Record<string, { label: string; type: string }> = {
        wait: { label: '待处理', type: 'info' },
        processing: { label: '生成中', type: 'primary' },
        wait_download: { label: '等待下载', type: 'primary' },
        downloading: { label: '下载中', type: 'primary' },
        uploading: { label: '上传中', type: 'primary' },
        success: { label: '已完成', type: 'success' },
        fail: { label: '失败', type: 'danger' },
    }
    return map[status] || { label: status, type: 'info' }
}

// 获取视频地址
const getVideoUrl = (task: any) => {
    if (task.result?.video_path) {
        return task.result.video_path
    }
    return ''
}

// WebSocket 监听
const addListener = () => {
    if (userStore.hasLogin()) {
        subscribe('private-generatecreativevideo-' + USERINFO.value?.user, (res: any) => {
            fetchTaskList()
        })
    }
}

// 初始化视频模型列表
const initModel = () => {
    const models = modelStore.get('creative_video')
    if (models && models.length > 0 && !videoModelId.value) {
        videoModelId.value = models[0].id
        videoModel.value = models[0]
    }
}

onMounted(() => {
    addListener()
    fetchTaskList()
    nextTick(() => {
        initModel()
    })
})

onUnmounted(() => {
    unsubscribeAll()
})
</script>

<template>
    <div class="creative-page">
        <div class="creative-page-header">
            <h1>创意圈</h1>
        </div>
        <div class="creative-page-content">
            <!-- 左栏：输入面板 -->
            <div class="creative-input-panel">
                <!-- 图片上传 -->
                <div class="creative-section">
                    <div class="creative-section-title">参考图片</div>
                    <div class="creative-upload-area">
                        <el-upload
                            v-if="!imageUrl"
                            class="creative-upload"
                            drag
                            :data="{ dir_name: 'creative/image', dir_title: '创意参考图' }"
                            :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                            :headers="$http.getHeaders()"
                            accept="image/jpeg,image/png,image/webp"
                            :limit="1"
                            :before-upload="beforeUpload"
                            :on-success="handleUploadSuccess"
                            :on-error="handleUploadError"
                            :show-file-list="false"
                        >
                            <div class="creative-upload-inner" v-loading="uploading">
                                <el-icon size="40" color="var(--el-color-primary)"><UploadSvg /></el-icon>
                                <p>拖拽或点击上传图片</p>
                            </div>
                        </el-upload>
                        <div v-else class="creative-image-preview">
                            <el-image :src="imageUrl" fit="contain" class="creative-preview-img" />
                            <div class="creative-preview-actions">
                                <el-button type="danger" size="small" @click="removeImage" circle>
                                    <el-icon><Close /></el-icon>
                                </el-button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 提示词 -->
                <div class="creative-section">
                    <div class="creative-section-title">提示词</div>
                    <el-input
                        v-model="prompt"
                        type="textarea"
                        :rows="4"
                        placeholder="描述你想要的视频效果，例如：无人机以极快速度穿越复杂障碍或自然奇观，带来沉浸式飞行体验"
                    />
                </div>

                <!-- 参数设置 -->
                <div class="creative-section">
                    <div class="creative-section-title">参数设置</div>
                    <div class="creative-params">
                        <div class="creative-param-item">
                            <span class="creative-param-label">时长</span>
                            <el-radio-group v-model="duration" size="small">
                                <el-radio-button :value="5">5秒</el-radio-button>
                                <el-radio-button :value="10">10秒</el-radio-button>
                            </el-radio-group>
                        </div>
                        <div class="creative-param-item">
                            <span class="creative-param-label">分辨率</span>
                            <el-radio-group v-model="resolution" size="small">
                                <el-radio-button value="1080p">1080p</el-radio-button>
                                <el-radio-button value="720p">720p</el-radio-button>
                            </el-radio-group>
                        </div>
                    </div>
                </div>

                <!-- 模型选择 -->
                <div class="creative-section">
                    <div class="creative-section-title">选择模型</div>
                    <xl-models
                        v-model="videoModelId"
                        @select="handleModelSelect"
                        scene="creative_video"
                        title="视频生成模型"
                    />
                </div>

                <!-- 生成按钮 -->
                <div class="creative-section creative-generate-bar">
                    <el-button
                        type="primary"
                        size="large"
                        :loading="generating"
                        :disabled="!imageUrl || !videoModelId"
                        @click="generate"
                        class="creative-generate-btn"
                    >
                        {{ generating ? '生成中...' : '生成视频' }}
                    </el-button>
                </div>
            </div>

            <!-- 右栏：结果面板 -->
            <div class="creative-result-panel">
                <div class="creative-section-title">生成记录</div>
                <div class="creative-task-list" v-if="taskList.length > 0">
                    <div
                        v-for="task in taskList"
                        :key="task.id"
                        class="creative-task-item"
                    >
                        <div class="creative-task-header">
                            <el-tag :type="getStatusInfo(task.status).type as any" size="small">
                                {{ getStatusInfo(task.status).label }}
                            </el-tag>
                            <span class="creative-task-time">{{ task.created_at }}</span>
                        </div>
                        <div class="creative-task-body">
                            <!-- 生成中 -->
                            <div v-if="['processing', 'wait', 'wait_download', 'downloading', 'uploading'].includes(task.status)" class="creative-task-progress">
                                <el-icon class="is-loading"><Loading /></el-icon>
                                <span>视频生成中，请耐心等待...</span>
                            </div>
                            <!-- 成功 - 播放视频 -->
                            <div v-else-if="task.status === 'success' && getVideoUrl(task)" class="creative-task-video">
                                <video
                                    :src="getVideoUrl(task)"
                                    controls
                                    class="creative-video-player"
                                    preload="metadata"
                                />
                            </div>
                            <!-- 失败 -->
                            <div v-else-if="task.status === 'fail'" class="creative-task-fail">
                                <span>{{ task.result?.message || '生成失败' }}</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div v-else class="creative-empty">
                    <el-empty description="暂无生成记录，上传图片开始创作" />
                </div>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.creative-page {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;

    &-header {
        padding: 16px 20px;
        flex-shrink: 0;

        h1 {
            margin: 0;
            font-size: 20px;
            font-weight: 600;
        }
    }

    &-content {
        flex: 1;
        display: flex;
        gap: 16px;
        padding: 0 20px 20px;
        overflow: hidden;
    }
}

.creative-input-panel {
    width: 420px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow-y: auto;
    padding-right: 8px;
}

.creative-result-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.creative-section {
    &-title {
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 8px;
    }
}

.creative-upload-area {
    .creative-upload {
        width: 100%;

        :deep(.el-upload) {
            width: 100%;
        }

        :deep(.el-upload-dragger) {
            width: 100%;
            padding: 24px;
            background: rgba(0, 0, 0, 0.04);
            border: 1px dashed rgba(0, 0, 0, 0.12);
            border-radius: 8px;
        }
    }

    .creative-upload-inner {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        color: var(--el-text-color-secondary);

        p {
            margin: 0;
            font-size: 13px;
        }
    }
}

.creative-image-preview {
    position: relative;
    border-radius: 8px;
    overflow: hidden;
    background: rgba(0, 0, 0, 0.2);

    .creative-preview-img {
        width: 100%;
        max-height: 280px;
    }

    .creative-preview-actions {
        position: absolute;
        top: 8px;
        right: 8px;
    }
}

.creative-params {
    display: flex;
    flex-direction: column;
    gap: 10px;

    &-item {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    &-label {
        font-size: 13px;
        color: var(--el-text-color-regular);
        width: 50px;
        flex-shrink: 0;
    }
}

.creative-generate-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 8px;

    .creative-points-info {
        font-size: 13px;
        color: var(--el-text-color-secondary);
    }

    .creative-points-value {
        color: var(--el-color-warning);
        font-weight: 600;
    }

    .creative-generate-btn {
        min-width: 120px;
    }
}

.creative-task-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.creative-task-item {
    background: rgba(0, 0, 0, 0.04);
    border-radius: 8px;
    padding: 12px;
    border: 1px solid rgba(0, 0, 0, 0.06);

    .creative-task-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;

        .creative-task-time {
            font-size: 12px;
            color: var(--el-text-color-secondary);
        }
    }

    .creative-task-progress {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 16px 0;
        color: var(--el-color-primary);
        font-size: 13px;
    }

    .creative-task-fail {
        padding: 8px 0;
        color: var(--el-color-danger);
        font-size: 13px;
    }

    .creative-task-video {
        border-radius: 6px;
        overflow: hidden;

        .creative-video-player {
            width: 100%;
            max-height: 360px;
            border-radius: 6px;
        }
    }
}

.creative-empty {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
}
</style>
