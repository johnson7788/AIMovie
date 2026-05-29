<template>
    <el-dialog v-model="dialogVisible" title="音色编辑" width="620px">
        <div class="flex flex-center">
            <div class="bg-overlay rounded-4 p-4 box flex flex-center">
                <div class="record-player" v-if="form.audio">
                    <div class="record-disc" :class="{ 'playing': isAudioPlaying }">
                        <div class="disc-inner">
                            <div class="disc-center"></div>
                        </div>
                    </div>
                    <div class="play-button" @click="handlePlayAudio">
                        <el-icon :size="16" color="var(--el-color-white)">
                            <IconPlay1 v-if="!isAudioPlaying" />
                            <IconPause v-else />
                        </el-icon>
                    </div>
                </div>
                <div v-else class="empty-audio">
                    <el-icon :size="16" color="var(--el-text-color-secondary)">
                        <Picture />
                    </el-icon>
                    <span class="empty-text">暂无音频</span>
                </div>
            </div>
        </div>
        <div class="flex flex-x-space-between grid-gap-4 mt-6">
            <div>
                <el-form :model="form" label-width="100px">
                    <el-row>
                        <el-col :span="24">
                            <el-form-item label="声音名称：">
                                <el-input v-model="form.name" maxlength="20" :show-word-limit="true"
                                    placeholder="请输入声音名称" />
                            </el-form-item>
                        </el-col>
                        <el-col :span="14">
                            <el-form-item label="声音设置：">
                                <el-select v-model="form.gender" placeholder="性别">
                                    <el-option v-for="item in WEBCONFIG?.enum?.actor_gender" :key="item.value"
                                        :label="item.label" :value="item.value" />
                                </el-select>
                            </el-form-item>
                        </el-col>
                        <el-col :span="10">
                            <el-form-item label-width="10px">
                                <el-select v-model="form.age" placeholder="年龄">
                                    <el-option v-for="item in WEBCONFIG?.enum?.actor_age" :key="item.value"
                                        :label="item.label" :value="item.value" />
                                    </el-select>
                                </el-form-item>
                        </el-col>
                    </el-row>
                </el-form>
            </div>
            <el-upload ref="uploadImageRef" :data="{ dir_name: 'voice/image', dir_title: '声音封面照片' }"
                :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')" :headers="$http.getHeaders()"
                accept="image/jpeg,image/png" :limit="1" type="cover" :disabled="uploadLoading"
                :before-upload="() => { uploadLoading = true; return true; }" :on-success="handleUploadSuccess"
                :show-file-list="false" :on-error="() => { uploadLoading = false; handleUploadError() }">
                <div class="upload" v-loading="uploadLoading" v-if="!form.headimg">
                    <el-icon :size="24" v-if="!uploadLoading">
                        <Plus />
                    </el-icon>
                    <span>点击上传</span>
                </div>
                <el-image v-else :src="form.headimg" class="cover-image" fit="cover"></el-image>
            </el-upload>
        </div>
        <template #footer>
            <div class="flex flex-center w-100">
                <el-button color="var(--el-color-white)" @click="dialogVisible = false">取消</el-button>
                <el-button type="success" @click="handleSubmit">确定</el-button>
            </div>
        </template>
    </el-dialog>
</template>
<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { useWebConfigStore, useRefs } from '@/stores';
import { Plus, Picture } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import IconPlay1 from '@/svg/icon/icon-play-1.vue';
import IconPause from '@/svg/icon/icon-pause.vue';

const webConfigStore = useWebConfigStore();
const { WEBCONFIG } = useRefs(webConfigStore);
const dialogVisible = ref(false)
const uploadImageRef = ref<any>(null)
const uploadLoading = ref(false)
const audioElement = ref<HTMLAudioElement | null>(null)
const isAudioPlaying = ref(false)
const emit = defineEmits(['update'])
// 监听对话框关闭，清理音频
watch(dialogVisible, (newVal) => {
    if (!newVal) {
        cleanupAudio()
    }
})

const form = ref<any>({
    id: null,
    name: '',
    headimg: '',
    gender: '',
    age: '',
    audio: ''
})

// 播放/暂停音频
const handlePlayAudio = () => {
    if (!form.value.audio) {
        ElMessage.warning('暂无音频')
        return
    }

    if (!audioElement.value) {
        audioElement.value = new Audio(form.value.audio)
        audioElement.value.onended = () => {
            isAudioPlaying.value = false
        }
        audioElement.value.onpause = () => {
            isAudioPlaying.value = false
        }
        audioElement.value.onplay = () => {
            isAudioPlaying.value = true
        }
        audioElement.value.onerror = () => {
            isAudioPlaying.value = false
            ElMessage.error('音频播放失败')
        }
    }

    if (isAudioPlaying.value) {
        audioElement.value.pause()
    } else {
        audioElement.value.play().catch((error) => {
            console.error('播放失败:', error)
            ElMessage.error('音频播放失败')
        })
    }
}

// 上传成功回调
const handleUploadSuccess = (response: any) => {
    uploadLoading.value = false
    if (response.code === ResponseCode.SUCCESS) {
        form.value.headimg = response.data.url
        uploadImageRef.value?.clearFiles()
        ElMessage.success('上传成功')
    } else {
        ElMessage.error(response.msg || '上传失败')
    }
}

// 上传失败回调
const handleUploadError = () => {
    uploadImageRef.value?.clearFiles()
    ElMessage.error('上传失败，请稍后重试')
}

// 清理音频资源
const cleanupAudio = () => {
    if (audioElement.value) {
        audioElement.value.pause()
        audioElement.value = null
    }
    isAudioPlaying.value = false
}

defineExpose({
    open: (id: any) => {
        form.value.id = id;
        // 清理之前的音频
        cleanupAudio()
        // 获取声音详情，填充表单数据
        if (id) {
            $http.get(`/app/model/api/Voice/detail`, { params: { id } }).then((res: any) => {
                if (res.code === ResponseCode.SUCCESS && res.data) {
                    form.value.name = res.data.name || ''
                    form.value.headimg = res.data.headimg || ''
                    form.value.gender = res.data.gender || ''
                    form.value.age = res.data.age || ''
                    form.value.audio = res.data.audio || ''
                }
            }).catch(() => {
                ElMessage.error('获取声音详情失败')
            })
        }
        dialogVisible.value = true
    }
})

// 组件卸载时清理音频资源
onUnmounted(() => {
    cleanupAudio()
})

const handleSubmit = () => {
    $http.post('/app/model/api/Voice/update', form.value).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg)
            dialogVisible.value = false
            emit('update')
        } else {
            ElMessage.error(res.msg)
        }
    }).catch(() => {
        ElMessage.error('修改失败')
    })
}
</script>
<style lang="scss" scoped>
.box {
    width: 185px;
    height: 224px;
    position: relative;
    overflow: hidden;
}

.record-player {
    position: relative;
    width: 85px;
    height: 85px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.record-disc {
    width: 85px;
    height: 85px;
    border-radius: 50%;
    // background: radial-gradient(circle, #2d2d2d 0%, #1f1f1f 50%, #151515 100%);
    border:4px solid #272727;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.3s ease;

    &.playing {
        animation: rotate 10s linear infinite;
    }

    .disc-inner {
        width: 75px;
        height: 75px;
        border-radius: 50%;
        background: linear-gradient(to bottom, #373737 0%, #B3B3B3 50%, #373737 100%);
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;

        .disc-center {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            // background: radial-gradient(circle, #2a2a2a 0%, #1a1a1a 50%, #0f0f0f 100%);
            position: relative;
        }
    }
}

.play-button {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.3s ease;
    z-index: 10;

    &:hover {
        background: rgba(0, 0, 0, 0.6);
        transform: translate(-50%, -50%) scale(1.05);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    }

    &:active {
        transform: translate(-50%, -50%) scale(0.98);
    }

    .el-icon {
        color: #ffffff;
        filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
    }
}

.empty-audio {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    width: 100%;
    height: 100%;

    .empty-text {
        font-size: 14px;
        color: var(--el-text-color-secondary);
    }
}

@keyframes rotate {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}

:deep(.el-input__wrapper) {
    --el-input-bg-color: #1e1e1e;
    --el-input-border-color: #1e1e1e;
    --el-input-focus-border-color: #1e1e1e;
    --el-input-border-radius: 8px;
    --el-border-radius-base: 8px;
    padding: 6px 8px;
}

:deep(.el-select__wrapper) {
    --el-fill-color-blank: #1e1e1e;
    --el-select-border-color: #1e1e1e;
    --el-color-primary: #1e1e1e;
    --el-select-border-radius: 8px;
    --el-border-radius-base: 8px;
    padding: 14px 16px;
}

.cover-image {
    width: 116px;
    height: 116px;
    object-fit: cover;
    border-radius: 8px;
}

.empty-cover {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
}

.upload {
    width: 120px;
    height: 120px;
    background-color: var(--el-bg-color-overlay);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    cursor: pointer;
    transition: all 0.3s;

    &:hover {
        background-color: var(--el-fill-color-dark);
    }

    span {
        font-size: 12px;
        color: var(--el-text-color-secondary);
    }
}

.el-button {
    --el-border-radius-base: 6px;
    padding: 16px 52px;
}
</style>