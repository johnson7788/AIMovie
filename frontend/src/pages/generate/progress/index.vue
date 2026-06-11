<template>
    <div class="progress-page">
        <!-- Header -->
        <div class="progress-header">
            <div class="header-left">
                <el-button @click="goBack" :icon="'ArrowLeft'" text>返回</el-button>
                <div class="task-info">
                    <h2>生成进度</h2>
                    <el-tag size="small" :type="statusTagType">{{ statusText }}</el-tag>
                    <span class="elapsed-time">{{ formattedElapsed }}</span>
                </div>
            </div>
            <div class="header-right">
                <span class="task-id">Task: {{ taskId?.substring(0, 8) }}...</span>
            </div>
        </div>

        <!-- Overall Progress -->
        <div class="progress-bar-wrap" v-if="overallProgress > 0">
            <el-progress :percentage="Math.min(overallProgress, 99)" :status="isComplete ? 'success' : undefined" :stroke-width="8" />
        </div>

        <!-- Main Content -->
        <div class="progress-content" v-loading="isConnecting && logs.length === 0" element-loading-text="正在连接...">
            <!-- Left: Stage Timeline + Logs -->
            <div class="left-panel">
                <!-- Stage Timeline -->
                <el-card shadow="never" class="stage-card" v-if="stages.length > 0">
                    <template #header>
                        <span>阶段进度</span>
                    </template>
                    <div class="stage-list">
                        <div v-for="stage in stages" :key="stage.name" class="stage-item" :class="stage.status">
                            <el-icon v-if="stage.status === 'done'" class="stage-icon done"><CircleCheckFilled /></el-icon>
                            <el-icon v-else-if="stage.status === 'running'" class="stage-icon running"><Loading /></el-icon>
                            <el-icon v-else class="stage-icon pending"><Clock /></el-icon>
                            <span class="stage-name">{{ stage.label }}</span>
                            <span class="stage-duration" v-if="stage.duration">{{ stage.duration }}</span>
                        </div>
                    </div>
                </el-card>

                <!-- Log Viewer -->
                <el-card shadow="never" class="log-card">
                    <template #header>
                        <div class="log-header">
                            <span>生成日志</span>
                            <el-button size="small" text @click="autoScroll = !autoScroll">
                                {{ autoScroll ? '自动滚动: 开' : '自动滚动: 关' }}
                            </el-button>
                        </div>
                    </template>
                    <div class="log-viewer" ref="logViewerRef">
                        <div v-if="logs.length === 0 && !isConnecting" class="log-empty">
                            等待日志输出...
                        </div>
                        <div v-for="(log, idx) in logs" :key="idx" class="log-line" :class="`log-${log.level?.toLowerCase()}`">
                            <span class="log-time">{{ log.time }}</span>
                            <span class="log-level">[{{ log.level }}]</span>
                            <span class="log-msg">{{ log.message }}</span>
                        </div>
                    </div>
                </el-card>
            </div>

            <!-- Right: Artifacts -->
            <div class="right-panel">
                <el-card shadow="never" class="artifacts-card" v-if="artifacts.length > 0 || isConnecting">
                    <template #header>
                        <span>生成产物 ({{ artifacts.length }})</span>
                    </template>
                    <div class="artifacts-list" v-if="artifacts.length > 0">
                        <div v-for="(item, idx) in artifacts" :key="idx" class="artifact-item">
                            <!-- Text artifacts -->
                            <template v-if="item.file_type === 'text' || item.file_type === 'json'">
                                <div class="artifact-header">
                                    <el-tag size="small" type="info">{{ item.stage }}</el-tag>
                                    <span class="artifact-name">{{ item.file_path }}</span>
                                </div>
                                <div class="artifact-text-preview" v-if="item.content_preview">
                                    <pre>{{ item.content_preview }}</pre>
                                </div>
                            </template>

                            <!-- Image artifacts -->
                            <template v-else-if="item.file_type === 'image'">
                                <div class="artifact-header">
                                    <el-tag size="small" type="success">{{ item.stage }}</el-tag>
                                    <span class="artifact-name">{{ item.character_name || item.frame_type || item.file_path }}</span>
                                </div>
                                <el-image
                                    :src="buildFileUrl(item.url || item.file_path)"
                                    fit="contain"
                                    :preview-src-list="[buildFileUrl(item.url || item.file_path)]"
                                    class="artifact-image"
                                    lazy
                                >
                                    <template #error>
                                        <div class="image-error">加载失败</div>
                                    </template>
                                </el-image>
                            </template>

                            <!-- Video artifacts -->
                            <template v-else-if="item.file_type === 'video'">
                                <div class="artifact-header">
                                    <el-tag size="small" type="warning">{{ item.stage }}</el-tag>
                                    <span class="artifact-name">{{ item.file_path }}</span>
                                </div>
                                <video
                                    :src="buildFileUrl(item.url || item.file_path)"
                                    controls
                                    class="artifact-video"
                                    preload="metadata"
                                />
                            </template>
                        </div>
                    </div>
                    <div v-else-if="!isConnecting" class="artifacts-empty">
                        等待产物生成...
                    </div>
                </el-card>
            </div>
        </div>

        <!-- Error state -->
        <div v-if="errorMessage" class="error-section">
            <el-alert :title="'生成失败'" :description="errorMessage" type="error" show-icon :closable="false" />
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { CircleCheckFilled, Loading, Clock } from '@element-plus/icons-vue';
import { useSSE, type SSEEvent } from '@/composables/useSSE';

const route = useRoute();
const router = useRouter();
const { connect, disconnect } = useSSE();

const taskId = computed(() => route.params.task_id as string);
const mode = computed(() => route.query.mode as string || 'idea2video');

// State
const logs = ref<Array<{ time: string; level: string; message: string }>>([]);
const artifacts = ref<Array<SSEEvent>>([]);
const stages = reactive<Array<{ name: string; label: string; status: 'pending' | 'running' | 'done'; duration?: string }>>([]);
const isConnecting = ref(true);
const isComplete = ref(false);
const errorMessage = ref<string | null>(null);
const overallProgress = ref(0);
const elapsedSeconds = ref(0);
const autoScroll = ref(true);
const logViewerRef = ref<HTMLElement | null>(null);

let elapsedTimer: ReturnType<typeof setInterval> | null = null;

// Computed
const statusText = computed(() => {
    if (errorMessage.value) return '失败';
    if (isComplete.value) return '完成';
    if (isConnecting.value && logs.value.length === 0) return '连接中...';
    return '生成中...';
});

const statusTagType = computed(() => {
    if (errorMessage.value) return 'danger';
    if (isComplete.value) return 'success';
    return 'warning';
});

const formattedElapsed = computed(() => {
    const mins = Math.floor(elapsedSeconds.value / 60);
    const secs = elapsedSeconds.value % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
});

// Stage definitions for different modes
const stageDefinitions: Record<string, Array<{ name: string; label: string }>> = {
    idea2video: [
        { name: 'story', label: '故事创作' },
        { name: 'characters', label: '角色提取' },
        { name: 'character_portraits', label: '角色画像' },
        { name: 'script', label: '剧本编写' },
        { name: 'scene_0', label: '场景处理' },
        { name: 'concatenate', label: '视频合成' },
    ],
    script2video: [
        { name: 'characters', label: '角色提取' },
        { name: 'character_portraits', label: '角色画像' },
        { name: 'storyboard', label: '分镜设计' },
        { name: 'visual_descriptions', label: '视觉描述' },
        { name: 'camera_tree', label: '机位构建' },
        { name: 'frames', label: '画面生成' },
        { name: 'concatenate', label: '视频合成' },
    ],
    scene_image: [
        { name: 'scene_image', label: '场景图片生成' },
    ],
    storyboard_image: [
        { name: 'storyboard_image', label: '分镜图片生成' },
    ],
};

// Initialize stage list based on mode
const initStages = () => {
    const defs = stageDefinitions[mode.value] || stageDefinitions.idea2video;
    stages.length = 0;
    stages.push(...defs.map(d => ({
        name: d.name,
        label: d.label,
        status: 'pending' as const,
    })));
};

// Build file URL from relative path or event URL
const buildFileUrl = (filePath: string) => {
    if (!filePath) return '';
    if (filePath.startsWith('/api/')) {
        const baseURL = import.meta.env.DEV ? '/local' : '';
        return baseURL + filePath;
    }
    // Assume it's a relative path from the task files endpoint
    const baseURL = import.meta.env.DEV ? '/local' : '';
    return `${baseURL}/api/tasks/${taskId.value}/files/${filePath}`;
};

const goBack = () => {
    router.back();
};

// Auto-scroll log viewer
watch(logs, async () => {
    if (autoScroll.value) {
        await nextTick();
        if (logViewerRef.value) {
            logViewerRef.value.scrollTop = logViewerRef.value.scrollHeight;
        }
    }
}, { deep: false });

// Update stage status based on events
const updateStageStatus = (event: SSEEvent) => {
    const stageName = event.stage;
    if (!stageName) return;

    // Find or create stage entry
    let stage = stages.find(s => s.name === stageName);
    if (!stage && event.type === 'stage_start') {
        stage = { name: stageName, label: stageName, status: 'running' };
        stages.push(stage);
    }

    if (stage) {
        if (event.type === 'stage_start') {
            stage.status = 'running';
        } else if (event.type === 'stage_end') {
            stage.status = 'done';
            if (event.duration_ms) {
                stage.duration = `${(event.duration_ms / 1000).toFixed(1)}s`;
            }
        }
    }

    // Update overall progress based on completed stages
    const totalStages = stages.length || 1;
    const completedStages = stages.filter(s => s.status === 'done').length;
    const runningStageIdx = stages.findIndex(s => s.status === 'running');
    if (runningStageIdx >= 0) {
        overallProgress.value = Math.round(((completedStages + 0.5) / totalStages) * 100);
    } else {
        overallProgress.value = Math.round((completedStages / totalStages) * 100);
    }
};

// Handle SSE events
const handleEvent = (event: SSEEvent) => {
    isConnecting.value = false;

    switch (event.type) {
        case 'log':
            logs.value.push({
                time: new Date().toLocaleTimeString(),
                level: event.level || 'INFO',
                message: event.message || '',
            });
            // Keep only last 500 log lines
            if (logs.value.length > 500) {
                logs.value = logs.value.slice(-500);
            }
            break;

        case 'stage_start':
        case 'stage_end':
            updateStageStatus(event);
            logs.value.push({
                time: new Date().toLocaleTimeString(),
                level: 'INFO',
                message: `[${event.stage}] ${event.message || (event.type === 'stage_start' ? '开始' : '完成')}`,
            });
            break;

        case 'artifact':
            artifacts.value.push(event);
            logs.value.push({
                time: new Date().toLocaleTimeString(),
                level: 'INFO',
                message: `[${event.stage}] 产物: ${event.file_path}`,
            });
            break;

        case 'progress':
            logs.value.push({
                time: new Date().toLocaleTimeString(),
                level: 'INFO',
                message: `[${event.stage}] ${event.message || `进度: ${event.current}/${event.total}`}`,
            });
            break;

        case 'error':
            errorMessage.value = event.error || '未知错误';
            logs.value.push({
                time: new Date().toLocaleTimeString(),
                level: 'ERROR',
                message: `生成失败: ${event.error}`,
            });
            break;

        case 'complete':
            isComplete.value = true;
            overallProgress.value = 100;
            logs.value.push({
                time: new Date().toLocaleTimeString(),
                level: 'INFO',
                message: `生成完成! 结果: ${event.result || '见产物列表'}`,
            });
            break;
    }
};

const handleError = (err: Error) => {
    isConnecting.value = false;
    errorMessage.value = err.message || '连接失败';
};

const handleComplete = () => {
    isConnecting.value = false;
};

onMounted(() => {
    initStages();

    // Start elapsed timer
    elapsedTimer = setInterval(() => {
        if (!isComplete.value) {
            elapsedSeconds.value++;
        }
    }, 1000);

    // Connect to SSE
    connect(taskId.value, {
        onEvent: handleEvent,
        onError: handleError,
        onComplete: handleComplete,
    });
});

onUnmounted(() => {
    disconnect();
    if (elapsedTimer) {
        clearInterval(elapsedTimer);
    }
});
</script>

<style scoped lang="scss">
.progress-page {
    padding: 16px 20px;
    height: calc(100vh - 60px);
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    .header-left {
        display: flex;
        align-items: center;
        gap: 12px;
        .task-info {
            display: flex;
            align-items: center;
            gap: 8px;
            h2 {
                margin: 0;
                font-size: 18px;
            }
            .elapsed-time {
                font-family: monospace;
                font-size: 14px;
                color: var(--el-text-color-secondary);
            }
        }
    }
    .header-right {
        .task-id {
            font-size: 12px;
            color: var(--el-text-color-disabled);
            font-family: monospace;
        }
    }
}

.progress-bar-wrap {
    padding: 0 4px;
}

.progress-content {
    flex: 1;
    display: flex;
    gap: 12px;
    min-height: 0;
    overflow: hidden;
}

.left-panel {
    flex: 3;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
    overflow: hidden;
}

.right-panel {
    flex: 2;
    min-width: 280px;
    max-width: 450px;
    overflow: hidden;
}

.stage-card {
    flex-shrink: 0;
    .stage-list {
        display: flex;
        flex-wrap: wrap;
        gap: 4px 12px;
    }
    .stage-item {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 13px;
        padding: 2px 0;
        .stage-icon {
            font-size: 14px;
            &.done { color: #67c23a; }
            &.running { color: #e6a23c; animation: spin 1.5s linear infinite; }
            &.pending { color: var(--el-text-color-disabled); }
        }
        .stage-name { color: var(--el-text-color-primary); }
        .stage-duration { color: var(--el-text-color-secondary); font-size: 11px; }
        &.pending .stage-name { color: var(--el-text-color-disabled); }
    }
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.log-card {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
    :deep(.el-card__body) {
        flex: 1;
        min-height: 0;
        overflow: hidden;
        padding: 0;
        display: flex;
        flex-direction: column;
    }
}

.log-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.log-viewer {
    flex: 1;
    overflow-y: auto;
    background: #1e1e1e;
    color: #d4d4d4;
    font-family: 'Courier New', Courier, monospace;
    font-size: 12px;
    padding: 8px 12px;
    line-height: 1.6;
    min-height: 200px;

    .log-empty {
        color: #808080;
        padding: 20px;
        text-align: center;
    }

    .log-line {
        white-space: pre-wrap;
        word-break: break-all;
        .log-time { color: #569cd6; margin-right: 8px; }
        .log-level { margin-right: 8px; }
        &.log-info .log-level { color: #6a9955; }
        &.log-warning .log-level { color: #ce9178; }
        &.log-error .log-level { color: #f44747; }
        &.log-debug .log-level { color: #808080; }
    }
}

.artifacts-card {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
    :deep(.el-card__body) {
        flex: 1;
        overflow-y: auto;
        padding: 8px;
    }
}

.artifacts-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.artifacts-empty {
    color: var(--el-text-color-secondary);
    text-align: center;
    padding: 20px;
}

.artifact-item {
    border: 1px solid #ebeef5;
    border-radius: 4px;
    padding: 8px;

    .artifact-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
        .artifact-name {
            font-size: 12px;
            color: var(--el-text-color-regular);
            word-break: break-all;
        }
    }

    .artifact-text-preview {
        background: var(--el-fill-color-light);
        border-radius: 4px;
        padding: 8px;
        max-height: 200px;
        overflow-y: auto;
        pre {
            margin: 0;
            font-size: 12px;
            white-space: pre-wrap;
            word-break: break-all;
        }
    }

    .artifact-image {
        width: 100%;
        max-height: 300px;
        border-radius: 4px;
        :deep(img) {
            object-fit: contain;
            max-height: 300px;
        }
    }

    .artifact-video {
        width: 100%;
        max-height: 300px;
        border-radius: 4px;
    }

    .image-error {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 120px;
        color: var(--el-text-color-secondary);
        background: var(--el-fill-color-light);
        border-radius: 4px;
    }
}

.error-section {
    flex-shrink: 0;
}
</style>
