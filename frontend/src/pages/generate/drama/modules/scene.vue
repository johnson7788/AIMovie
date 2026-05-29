<script lang="ts" setup>
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { ElMessage } from 'element-plus';
const props = withDefaults(defineProps<{
    modelValue: string | number
    scene: any[]
    drama_id: string | number
    episode_id: string | number
    episodeInfo: any
}>(), {
    modelValue: '',
    scene: () => [],
    drama_id: '',
    episode_id: '',
    episodeInfo: () => ({}),
});
const emit = defineEmits(['update:modelValue', 'update:scene']);
const sceneList = ref<any[]>(props.scene);
const episodeInfo = ref<any>(props.episodeInfo);
watch(() => props.episodeInfo, (newVal) => {
    episodeInfo.value = newVal;
});
watch(sceneList, (newVal) => {
    emit('update:scene', newVal);
});
watch(() => props.scene, (newVal) => {
    sceneList.value = newVal;
});
const currentSceneId = ref(props.modelValue);
watch(currentSceneId, (newVal) => {
    emit('update:modelValue', newVal);
});
watch(() => props.modelValue, (newVal) => {
    currentSceneId.value = newVal;
});
const handleCopySceneLoading = ref(false);

const handleDeleteSceneLoading = ref(false);

const handleDeleteScene = (row: any) => {
    handleDeleteSceneLoading.value = true;

    // 🔥 删除前备份（用于失败回滚）
    const backup = JSON.parse(JSON.stringify(sceneList.value));

    // 当前场景原数据
    const list = sceneList.value;

    // ✨ 1. 乐观更新 UI —— 先删掉
    const newList = list.filter(item => item.id !== row.id);

    // ✨ 2. 只对当前场景的 sort 重新排序
    const sortedSceneList = newList
        .sort((a, b) => a.sort - b.sort)
        .map((item, index) => ({
            ...item,
            sort: index + 1
        }));

    // 合并回原数组
    sceneList.value = newList.map(item => {
        const hit = sortedSceneList.find(i => i.id === item.id);
        return hit ?? item;
    });

    // 🔥 3. 调用服务端删除接口
    return $http.post('/app/shortplay/api/Scene/deleteScene', {
        id: row.id,
        drama_id: props.drama_id,
        episode_id: props.episode_id,
    })
        .then((res: any) => {
            if (res.code === ResponseCode.SUCCESS) {
                ElMessage.success('删除成功');
                if (currentSceneId.value == row.id) {
                    currentSceneId.value = '';
                }
            } else {
                ElMessage.error(res.msg);

                // ❗服务端失败 → 回滚 UI
                sceneList.value = backup;
            }
        })
        .catch(() => {
            ElMessage.error('删除失败');

            // ❗请求失败 → 回滚
            sceneList.value = backup;
        })
        .finally(() => {
            handleDeleteSceneLoading.value = false;
        });
};

const handleMouseEnterScene = (item: any) => {
    if (item.editMode || item.saveLoading) return
    item.component = 'form'
    // 深拷贝原始数据，用于取消
    item.originData = JSON.parse(JSON.stringify(item))
}
const handleCancel = (item: any) => {
    const origin = item.originData
    if (origin) {
        Object.assign(item, origin)
    }

    item.originData = null
    item.editMode = false
    item.component = 'view'
}
const handleSave = (item: any) => {
    if (!item.editMode) return
    item.saveLoading = true
    $http.post('/app/shortplay/api/Scene/update', item).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            item.editMode = false
            item.originData = null
            item.component = 'view'
        } else {
            ElMessage.error(res.msg)
        }
    }).catch(() => {
        ElMessage.error('保存失败')
    }).finally(() => {
        item.saveLoading = false
    })
}
const initLoading = ref<any>(false);
const initForm = reactive({
    model_id: '',
});
const generateSceneDialogVisible = ref(false);
const openGenerateSceneDialog = () => {
    generateSceneDialogVisible.value = true;
}
const handleGenerateSceneCancel = () => {
    generateSceneDialogVisible.value = false;
}
const handleGenerateScene = () => {
    if (initLoading.value) return;
    initLoading.value = true;
    $http.post('/app/shortplay/api/Generate/scene', {
        ...initForm,
        drama_id: props.drama_id,
        episode_id: props.episode_id,
    }).then((res: any) => {
        initLoading.value = false;
        if (res.code === ResponseCode.SUCCESS) {
            episodeInfo.value.init_scene_state = true;
            generateSceneDialogVisible.value = false;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        initLoading.value = false;
        ElMessage.error('绘制场景失败');
    }).finally(() => {
        initLoading.value = false;
    });
}
const currentItem = ref<any>({});
const currentItemIndex = ref();
const generateImageDialogVisible = ref(false);
const modelLoading = ref(false);
const openGenerateImage = (item?: any, index?: number) => {
    if (item) {
        if (modelLoading.value || item.image_state) return;
        currentItem.value = item;
        currentItemIndex.value = index;
    } else {
        if (initLoading.value) return;
        currentItem.value = {};
        currentItemIndex.value = undefined;
    }
    nextTick(() => {
        generateImageDialogVisible.value = true;
    })
}
const sceneCreateRef = ref<any>(null);
const openCreateScene = () => {
    sceneCreateRef.value?.open?.({drama_id: props.drama_id, episode_id: props.episode_id});
}
const handleCreateSceneSuccess = (data: any) => {
    sceneList.value.push({
        ...data,
        component: 'view',
        saveLoading: false
    });
}
defineExpose({
    openCreateScene,
    openGenerateImage,
    openGenerateSceneDialog
})
</script>
<template>
    <el-scrollbar class="p-4" v-loading="handleCopySceneLoading || handleDeleteSceneLoading">
        <div class="scene-list pb-10">
            <el-empty v-if="sceneList.length === 0" description="暂无场景">
                <el-dialog v-model="generateSceneDialogVisible" class="generate-scene-dialog" draggable>
                    <template #header>
                        <span class="font-weight-600">AI绘制场景</span>
                    </template>
                    <el-alert title="当前分集尚未创建场景和分镜，是否使用AI绘制？" type="warning" :closable="false" />
                    <xl-models v-model="initForm.model_id" scene="creative_scenes" no-init />
                    <template #footer>
                        <div class="flex flex-center grid-gap-2">
                            <el-button type="info" @click="handleGenerateSceneCancel"
                                :disabled="initLoading">取消</el-button>
                            <el-button type="success" icon="Check" @click="handleGenerateScene"
                                :disabled="!initForm.model_id || initLoading" :loading="initLoading">绘制</el-button>
                        </div>
                    </template>
                </el-dialog>
            </el-empty>
            <template v-else>
                <div class="p-6 bg-gray rounded-4 flex flex-column grid-gap-4 scene-item"
                    v-for="item in sceneList" :class="{ 'scene-item-current': item.id === currentSceneId }"
                    :key="item.id">
                    <div class="flex grid-gap-4 flex-center">
                        <span class="text-dark h10 font-weight-600 py-4">#{{ item.id }}</span>
                        <div class="flex-1"></div>
                        <div class="flex flex-center grid-gap-2 scene-item-copy"
                            @click.stop="handleMouseEnterScene(item)">
                            <el-icon size="16">
                                <Edit />
                            </el-icon>
                            <span class="text-nowrap">编辑</span>
                        </div>
                        <el-popconfirm icon="Delete" title="确定删除该场景吗？" placement="bottom-end"
                            confirm-button-type="danger" width="fit-content" @confirm="handleDeleteScene(item)">
                            <template #reference>
                                <div class="flex flex-center grid-gap-2 scene-item-delete">
                                    <el-icon size="16">
                                        <Delete />
                                    </el-icon>
                                    <span class="text-nowrap">删除</span>
                                </div>
                            </template>
                        </el-popconfirm>
                    </div>
                    <div class="flex flex-column grid-gap-4 position-relative" v-if="item.component === 'view'">
                        <div class="flex flex-center">
                            <span class="scene-item-label">场景：</span>
                            <div class="flex-1">
                                <span class="text-text-primary">{{ item.title }}</span>
                            </div>
                        </div>
                        <div class="flex flex-center">
                            <span class="scene-item-label">地点：</span>
                            <div class="flex-1">
                                <span class="text-text-primary">{{ item.scene_space }}·{{ item.scene_location }}·{{
                                    item.scene_time }}·{{ item.scene_weather }}</span>
                            </div>
                        </div>
                        <div class="mt-4">
                            <span class="text-info">{{ item.description }}</span>
                        </div>
                    </div>
                    <el-form v-else-if="item.component === 'form'" class=" flex flex-column grid-gap-4"
                        :disabled="item.saveLoading">
                        <div class="flex grid-gap-2">
                            <span class="scene-item-label pt-3">地点：</span>
                            <div class="flex-1 grid-columns-2 grid-gap-2">
                                <el-input v-model="item.scene_space" placeholder="内景OR外景"
                                    class="scene-item-input grid-column-1 w-100" @input="item.editMode = true" />
                                <el-input v-model="item.scene_location" placeholder="地点"
                                    class="scene-item-input grid-column-1" @input="item.editMode = true" />
                                <el-input v-model="item.scene_time" placeholder="大概时间"
                                    class="scene-item-input grid-column-1" @input="item.editMode = true" />
                                <el-input v-model="item.scene_weather" placeholder="天气"
                                    class="scene-item-input grid-column-1" @input="item.editMode = true" />
                            </div>
                        </div>
                        <div class="flex grid-gap-2">
                            <span class="scene-item-label pt-3">描述：</span>
                            <el-input v-model="item.description" type="textarea" :autosize="{ minRows: 1, maxRows: 10 }"
                                placeholder="请输入描述" class="scene-item-textarea" @input="item.editMode = true" />
                        </div>
                        <div class="flex flex-x-flex-end">
                            <el-button type="info" @click.stop="handleCancel(item)">取消</el-button>
                            <el-button type="success" icon="Check" @click.stop="handleSave(item)"
                                :disabled="!item.editMode" :loading="item.saveLoading">保存</el-button>
                        </div>
                    </el-form>
                </div>
            </template>
        </div>
        <div class="loading-mask" v-if="episodeInfo.init_scene_state" v-loading="episodeInfo.init_scene_state"
            element-loading-text="绘制场景中..."></div>
        <xl-scene-create ref="sceneCreateRef" @success="handleCreateSceneSuccess" />
    </el-scrollbar>
</template>
<style lang="scss" scoped>
.loading-mask {
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    z-index: 1;
}

.scene-list {
    display: flex;
    flex-direction: column;
    height: fit-content;
    gap: 10px;

    .scene-item:last-child {
        margin-bottom: 50px;
    }

    .scene-item {
        position: relative;

        &-current {
            box-shadow: inset 0 0 0 2px var(--el-color-success);
        }

        .scene-item-add {
            position: absolute;
            top: calc(100% - 10px);
            left: 50%;
            transform: translateX(-50%);
            z-index: 1;
            height: 30px;
            width: 30px;
            font-size: 20px;
        }

        &-copy,
        &-delete {
            display: none;
            cursor: pointer;
            color: var(--el-text-color-secondary);

            &:hover {
                color: var(--el-text-color-primary);
            }
        }

        &:hover {

            .scene-item-copy,
            .scene-item-delete {
                display: flex;
            }
        }

        &-delete:hover {
            color: var(--el-color-danger);
        }

        &-delete-confirm {
            :deep(.el-popper) {
                width: fit-content;
                background: var(--el-bg-color-page);
                border: 1px solid var(--el-border-color);
                border-radius: 6px;
            }
        }

        .scene-item-image {
            border-radius: 0px;
            --el-avatar-size: 260px;
            width: 100%;
        }

        .image-modal {
            position: absolute;
            top: 5px;
            right: 5px;
            z-index: 1;
            display: none;

            &-loading {
                left: 0;
                top: 0;
                right: 0;
                bottom: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 10px;
                background-color: var(--el-mask-color-extra-light);
            }
        }

        &:hover {
            .image-modal {
                display: flex;
            }
        }
    }

    .scene-item-label {
        color: var(--el-text-color-primary);
    }

    .icon-actor {
        width: 20px;
        height: 20px;
    }

    .scene-item-textarea {
        width: fit-content;
        flex:1;
        --el-input-bg-color: var(--el-bg-color);
        --el-input-border-color: var(--el-bg-color);
        --el-input-border-radius: 6px;
        --el-input-focus-border-color: var(--el-bg-color);
        --el-input-text-color: var(--el-text-color-primary);
        --el-input-placeholder-color: var(--el-text-color-placeholder);
        --el-input-focus-text-color: var(--el-text-color-primary);
        --el-input-focus-placeholder-color: var(--el-text-color-placeholder);
        --el-input-focus-border-color: var(--el-bg-color);
        --el-input-hover-border-color: var(--el-bg-color);

        :deep(.el-textarea__inner) {
            resize: none;
            padding: 10px;
        }
    }

    .scene-item-input {
        --el-input-bg-color: var(--el-bg-color);
        --el-input-border-color: var(--el-bg-color);
        --el-input-border-radius: 6px;
        --el-input-focus-border-color: var(--el-bg-color);
        --el-input-text-color: var(--el-text-color-primary);
        --el-input-placeholder-color: var(--el-text-color-placeholder);
        --el-input-focus-text-color: var(--el-text-color-primary);
        --el-input-focus-placeholder-color: var(--el-text-color-placeholder);
        --el-input-focus-border-color: var(--el-bg-color);
        --el-input-hover-border-color: var(--el-bg-color);

        :deep(.el-textarea__inner) {
            resize: none;
            padding: 10px;
        }
    }

    .dialogue-item-input {
        --el-input-bg-color: var(--el-bg-color);
        --el-input-border-color: var(--el-bg-color);
        --el-input-border-radius: 6px;
        --el-input-focus-border-color: var(--el-bg-color);
        --el-input-text-color: var(--el-text-color-primary);
        --el-input-placeholder-color: var(--el-text-color-placeholder);
        --el-input-focus-text-color: var(--el-text-color-primary);
        --el-input-focus-placeholder-color: var(--el-text-color-placeholder);
        --el-input-focus-border-color: var(--el-bg-color);
        --el-input-hover-border-color: var(--el-bg-color);
    }
}

.scene-item-select {
    width: 180px;
    --el-select-bg-color: var(--el-bg-color);
    --el-select-input-focus-border-color: var(--el-color-success);
}

</style>