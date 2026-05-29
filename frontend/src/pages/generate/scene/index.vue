<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import IconPrevStepSvg from '@/svg/icon/icon-prev-step.vue';
import IconNextStepSvg from '@/svg/icon/icon-next-step.vue';
import IconBatchSvg from '@/svg/icon/icon-batch.vue';
import IconModelSvg from '@/svg/icon/icon-model.vue';
import IconReplaceSvg from '@/svg/icon/icon-replace.vue';
import IconUploadImageSvg from '@/svg/icon/icon-upload-image.vue';
import { useUserStore, useRefs } from '@/stores';
import { useRoute } from 'vue-router';
import router from '@/routers';
import { Loading } from '@element-plus/icons-vue';
import { usePush } from '@/composables/usePush';
const route = useRoute();
const userStore = useUserStore();
const { USERINFO } = useRefs(userStore);
const drama_id = ref<string | number>(route.params.drama_id as string | number)
const episode_id = ref<string | number>(route.params.episode_id as string | number)
const emit = defineEmits(['update:drama']);
const dramaInfo = ref<any>({});
const getDramaInfo = () => {
    if (!drama_id.value) return;
    $http.get('/app/shortplay/api/Works/details', { params: { id: drama_id.value } }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            dramaInfo.value = res.data;
            emit('update:drama', dramaInfo.value);
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('获取短剧详情失败');
    })
}
const SceneSearch = reactive({
    type: 'episode',
    name: '',
    drama_id: drama_id.value,
    episode_id: episode_id.value
})
const sceneList = ref<any[]>([]);
const loading = ref(false);
const sceneCreateRef = ref<any>(null);
const currentScene = ref<any>();
const currentSceneForm = ref<any>({
    drama_id: drama_id.value,
    episode_id: episode_id.value,
    id: '',
    title: '',
    description: '',
    scene_location: '',
    scene_space: '',
    scene_time: '',
    scene_weather: '',
    image: '',
    model_id: null,
    reference_image: '',
});
watch(sceneList, () => {
    try {
        const find = sceneList.value.find((item: any) => item.id === currentScene.value?.id);
        if (find) {
            handleCurrentScene(find)
        } else {
            currentScene.value = undefined;
            currentSceneForm.value = {
                drama_id: drama_id.value,
                episode_id: episode_id.value,
                id: '',
                title: '',
                description: '',
                scene_location: '',
                scene_space: '',
                scene_time: '',
                scene_weather: '',
                image: '',
                model_id: null,
                reference_image: '',
            };
        }
    } catch (error) {
        console.error('watch sceneList error', error);
    }
})
const getSceneList = () => {
    loading.value = true;
    $http.get('/app/shortplay/api/Scene/index', { params: SceneSearch }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            sceneList.value = res.data;
            const find = sceneList.value.find((item: any) => item.id === currentScene.value?.id);
            if (!find && sceneList.value.length > 0) {
                handleCurrentScene(sceneList.value[0]);
            }
        }
    }).catch((error) => {
        console.error('getSceneList error', error);
    }).finally(() => {
        loading.value = false;
    })
}
const taskList = ref<any[]>([]);
const taskLoading = ref(false);
const taskSearch = reactive({
    alias_id: '',
    scene: 'scene_image',
    page: 1,
    page_size: 100,
});
let taskController: any = null;
const getTaskList = () => {
    if (taskController) {
        taskController.abort();
    }
    taskController = new AbortController();
    taskLoading.value = true;
    taskList.value = [];
    $http.get('/app/model/api/Task/index', { params: taskSearch, signal: taskController?.signal }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            taskList.value = res.data.data;
        }
    }).catch(() => {
    }).finally(() => {
        taskLoading.value = false;
    })
}
const handleCurrentScene = (item: any) => {
    currentScene.value = item;
    currentSceneForm.value.id = item.id;
    currentSceneForm.value.title = item.title;
    currentSceneForm.value.description = item.description;
    currentSceneForm.value.scene_location = item.scene_location;
    currentSceneForm.value.scene_space = item.scene_space;
    currentSceneForm.value.scene_time = item.scene_time;
    currentSceneForm.value.scene_weather = item.scene_weather;
    currentSceneForm.value.image = item.image;
    currentSceneForm.value.model_id = item.model_id;
    taskSearch.alias_id = item.id;
    getTaskList();
}
const modelPopoverRef = ref<any>(null);
const modelButtonRef = ref<any>(null);
const model = ref<any>({});
const handleModelSelect = (item?: any) => {
    if (item) {
        model.value = item;
    } else {
        model.value = {};
        currentSceneForm.value.model_id = null;
    }
    modelPopoverRef.value?.hide();
}
const generateImageLoading = ref(false);
const handleGenerateImage = () => {
    if (generateImageLoading.value || currentScene.value.image_state) return;
    generateImageLoading.value = true;
    $http.post('/app/shortplay/api/Generate/sceneImage', { ...currentSceneForm.value, model_id: model.value.id }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            currentScene.value.image_state = 1;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('生成图片失败');
    }).finally(() => {
        generateImageLoading.value = false;
    })
}
const uploadImageRef = ref<any>(null);
const uploadLoading = ref(false);
const handleUploadReferenceImageSuccess = (response: any) => {
    uploadLoading.value = false;
    if (response.code === ResponseCode.SUCCESS) {
        currentSceneForm.value.reference_image = response.data.url;
    } else {
        ElMessage.error(response.msg);
    }
    uploadImageRef.value?.clearFiles();
}
const handleUploadReferenceImageError = () => {
    uploadLoading.value = false;
    uploadImageRef.value?.clearFiles();
}
const replaceSceneLoading = ref(false);
const handleReplaceScene = (item: any) => {
    if (replaceSceneLoading.value || item.status !== 'success') return;
    replaceSceneLoading.value = true;
    $http.post('/app/shortplay/api/Scene/update', {
        id: currentScene.value.id,
        drama_id: SceneSearch.drama_id,
        episode_id: SceneSearch.episode_id,
        image: item.result.image_path,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            currentScene.value.image = item.result.image_path;
            currentScene.value.image_state = 0;
            currentSceneForm.value.image = item.result.image_path;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('替换场景失败');
    }).finally(() => {
        replaceSceneLoading.value = false;
    })
}
const batchGenerateDialogVisible = ref(false);
const batchGenerateLoading = ref(false);
const batchGenerateLength = ref(0);
const batchGenerateList = ref<any[]>([]);
const handleBatchGenerate = () => {
    batchGenerateDialogVisible.value = true;
    batchGenerateList.value = sceneList.value.filter((item: any) => !item.image)
    batchGenerateLength.value = batchGenerateList.value.length
}
const submitBatchGenerate = () => {
    batchGenerateLoading.value = true;
    Promise.all(batchGenerateList.value.map((item: any) => {
        return $http.post('/app/shortplay/api/Generate/sceneImage', {
            scene_id: item.id,
            description: item.description,
            model_id: model.value.id,
        })
    })).then(() => {
        getSceneList();
    }).catch((error) => {
        console.error('submitBatchGenerate error', error);
    }).finally(() => {
        batchGenerateLoading.value = false;
        batchGenerateDialogVisible.value = false;
    })
}
const { subscribe, unsubscribeAll } = usePush();
const addListener = () => {
    subscribe('private-generatesceneimage-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const findItem = sceneList.value.find((item: any) => item.id === res.id);
        if (findItem) {
            findItem.image_state = 0;
            if (res.image) {
                findItem.image = res.image;
            }
            getTaskList();
        }
    });
}
const prevStep = () => {
    router.push(`/generate/props/${route.params.drama_id}/${route.params.episode_id}`);
}
const nextStep = () => {
    router.push(`/generate/storyboard/${route.params.drama_id}/${route.params.episode_id}`);
}
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
        drama_id: SceneSearch.drama_id,
        episode_id: SceneSearch.episode_id,
    })
        .then((res: any) => {
            if (res.code === ResponseCode.SUCCESS) {
                ElMessage.success('删除成功');
                if (currentScene.value?.id == row.id) {
                    currentScene.value = undefined;
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
const handleCreateSceneSuccess = (data: any) => {
    const findIndex = sceneList.value.findIndex((item: any) => item.id === data.id);
    if (findIndex !== -1) {
        sceneList.value[findIndex] = data;
    } else {
        sceneList.value.push(data);
    }
    if (currentScene.value?.id === data.id) {
        handleCurrentScene(data);
    }
}
const currentSceneUploadImageRef = ref<any>(null);
const currentSceneUploadLoading = ref(false);
const handleUploadSuccess = (response: any) => {
    currentSceneUploadLoading.value = false;
    if (response.code === ResponseCode.SUCCESS) {
        currentScene.value.image = response.data.url;
        $http.post('/app/shortplay/api/Scene/update', {
            id: currentScene.value.id,
            drama_id: SceneSearch.drama_id,
            episode_id: SceneSearch.episode_id,
            image: response.data.url,
        }).then((res: any) => {
            if (res.code === ResponseCode.SUCCESS) {
                ElMessage.success('保存成功');
            } else {
                ElMessage.error(res.msg);
            }
        })
    } else {
        ElMessage.error(response.msg);
    }
    currentSceneUploadImageRef.value?.clearFiles();
}
const handleUploadError = () => {
    currentSceneUploadLoading.value = false;
    currentSceneUploadImageRef.value?.clearFiles();
}
onMounted(() => {
    getSceneList();
    getDramaInfo();
    addListener();
})
onUnmounted(() => {
    console.log('scenes unmounted');
    unsubscribeAll();
})
</script>
<template>
    <div class="flex flex-column draw-module">
        <div class="flex-1 flex grid-gap-10 overflow-hidden">
            <div class="flex-1 flex flex-column grid-gap-10 overflow-hidden">
                <div class="flex grid-gap-2">
                    <span>{{ currentScene?.title }}</span>
                    <span class="text-success">场景{{ currentScene?.id }}</span>
                </div>
                <el-avatar :src="currentScene?.image_state ? '' : currentScene?.image" fit="contain" class="preview-image bg-mosaic"
                    shape="square">
                    <div v-if="currentScene?.image_state" class="flex flex-center flex-column grid-gap-2 text-info">
                        <el-icon size="64">
                            <Loading class="circular" />
                        </el-icon>
                        <span>场景绘制中...</span>
                    </div>
                    <div v-else class="flex flex-center flex-column grid-gap-2 text-info">
                        <el-icon size="64">
                            <IconUploadImageSvg />
                        </el-icon>
                        <span>在右侧让AI为你生成场景图</span>
                        <div class="flex grid-gap-2">
                            <span>或</span>
                            <el-upload ref="uploadImageRef" :data="{ dir_name: 'scene/image', dir_title: '场景图照片' }"
                                :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                                :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1" type="cover"
                                :disabled="currentSceneUploadLoading"
                                :before-upload="() => { currentSceneUploadLoading = true; return true; }"
                                :on-success="handleUploadSuccess" :show-file-list="false"
                                :on-error="() => { currentSceneUploadLoading = false; handleUploadError() }">
                                <span class="text-text-primary">从本地上传素材</span>
                            </el-upload>
                        </div>
                        <span>图片：JPG/PNG，大于 300px，不超过 10MB</span>
                    </div>
                </el-avatar>

                <div class="montage-storyboard rounded-4 border">
                    <el-scrollbar ref="videoScrollbarRef" class="montage-storyboard-video montage-storyboard-scrollbar"
                        x-scroll :y-scroll="false" wrap-class="montage-storyboard-video-wrap">
                        <div class="montage-storyboard-list">
                            <div class="montage-storyboard-list-item rounded-4" v-for="item in sceneList" :key="item.id"
                                :class="{ 'active': item.id === currentScene?.id }" @click="handleCurrentScene(item)">
                                <div class="flex montage-storyboard-list-item-title grid-gap-2">
                                    <span class="h10 flex-1 text-nowrap text-ellipsis-1">场景{{ item.id }} - {{ item.title
                                        }}</span>
                                    <el-popconfirm title="确定删除该分镜吗？" placement="bottom-end" confirm-button-type="danger"
                                        :teleported="false" width="fit-content" @confirm="handleDeleteScene(item)">
                                        <template #reference>
                                            <el-icon class="icon-button hover-show">
                                                <Delete />
                                            </el-icon>
                                        </template>
                                    </el-popconfirm>
                                </div>
                                <el-avatar class="montage-storyboard-list-item-image bg-mosaic" :src="item.image" :fit="['9:16','16:9'].includes(dramaInfo.aspect_ratio) ? 'contain' : 'cover'"
                                    v-loading="(item.image_state && item.image)" element-loading-text="图片生成中...">
                                    <div class="flex flex-column grid-gap-1 flex-center">
                                        <div class="flex">
                                            <span class="flex flex-center grid-gap-2" v-if="item.image_state">
                                                <el-icon size="20">
                                                    <Loading class="circular" />
                                                </el-icon>
                                                <span class="h10">生成中...</span>
                                            </span>
                                        </div>
                                    </div>
                                </el-avatar>
                            </div>
                            <div class="montage-storyboard-list-item rounded-4 flex flex-column grid-gap-2 flex-center pointer"
                                @click="sceneCreateRef?.open?.({ drama_id: SceneSearch.drama_id, episode_id: SceneSearch.episode_id })">
                                <el-icon size="20">
                                    <Plus />
                                </el-icon>
                                <span class="h10">新增场景</span>
                            </div>
                        </div>
                    </el-scrollbar>
                </div>
            </div>
            <div class="scene-form-wrapper bg-overlay border rounded-4 scene-form flex flex-column grid-gap-4">
                <template v-if="currentSceneForm.id">
                    <div class="border-bottom flex flex-center">
                        <el-input v-model="currentSceneForm.title" placeholder="场景" size="large"
                            class="scene-form-input flex-1">
                            <template #suffix>
                                <el-button type="primary" bg text size="small"
                                    @click="sceneCreateRef?.open?.({ scene: currentScene, drama_id: SceneSearch.drama_id, episode_id: SceneSearch.episode_id })">编辑</el-button>
                            </template>
                        </el-input>
                    </div>

                    <div class="flex flex-column grid-gap-2 px-4">
                        <span>场景</span>
                        <div class="grid-columns-4 grid-gap-2">
                            <el-input v-model="currentSceneForm.scene_location" placeholder="地点"
                                class="grid-column-2 scene-form-input"></el-input>
                            <el-input v-model="currentSceneForm.scene_space" placeholder="内景OR外景"
                                class="grid-column-2 scene-form-input"></el-input>
                            <el-input v-model="currentSceneForm.scene_time" placeholder="大概时间"
                                class="grid-column-2 scene-form-input"></el-input>
                            <el-input v-model="currentSceneForm.scene_weather" placeholder="天气"
                                class="grid-column-2 scene-form-input"></el-input>
                        </div>
                    </div>
                    <div class="flex flex-column grid-gap-2 px-4">
                        <span>场景描述</span>
                        <div class="bg rounded-4 p-4 border">
                            <el-input v-model="currentSceneForm.description" placeholder="请输入场景描述" size="small"
                                class="scene-form-textarea" type="textarea" :autosize="{ minRows: 6, maxRows: 20 }" />
                            <div class="flex flex-y-center grid-gap-2">
                                <div class="bg-overlay rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover"
                                    ref="modelButtonRef" title="选择使用AI生成图">
                                    <template v-if="model.id">
                                        <el-avatar :src="model.icon" :alt="model.name" shape="square"
                                            :size="16"></el-avatar>
                                        <span class="h10 text-ellipsis-1" style="max-width: 60px;">{{ model.name
                                        }}</span>
                                        <el-icon size="16" class="pointer" @click.stop="handleModelSelect()">
                                            <Close />
                                        </el-icon>
                                    </template>
                                    <template v-else>
                                        <el-icon size="16">
                                            <IconModelSvg />
                                        </el-icon>
                                        <span class="h10">场景图</span>
                                        <el-icon size="16">
                                            <ArrowDown />
                                        </el-icon>
                                    </template>
                                </div>
                                <el-upload ref="uploadImageRef" title="添加参考图"
                                    :data="{ dir_name: 'scene/reference', dir_title: '场景参考照片' }"
                                    :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                                    :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1" type="cover"
                                    :disabled="uploadLoading"
                                    :before-upload="() => { uploadLoading = true; return true; }"
                                    :on-success="handleUploadReferenceImageSuccess" :show-file-list="false"
                                    :on-error="handleUploadReferenceImageError">
                                    <div
                                        class="bg-overlay rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover">
                                        <el-popover placement="top" :disabled="!currentSceneForm.reference_image"
                                            width="fit-content">
                                            <el-avatar :src="currentSceneForm.reference_image" fit="contain" :size="130"
                                                shape="square"></el-avatar>
                                            <template #reference>
                                                <el-icon size="16"
                                                    v-if="!currentSceneForm.reference_image || uploadLoading">
                                                    <Loading class="circular" v-if="uploadLoading" />
                                                    <Plus v-else />
                                                </el-icon>
                                                <el-icon size="16" v-else color="var(--el-color-success)">
                                                    <PictureRounded />
                                                </el-icon>
                                            </template>
                                        </el-popover>
                                    </div>
                                </el-upload>
                                <div class="flex-1"></div>
                                <div class="rounded-round p-3 flex flex-center grid-gap-2 pointer"
                                    style="background-color: #FFFFFF;color:#141414;" @click="handleGenerateImage">
                                    <el-icon size="20">
                                        <Loading class="circular"
                                            v-if="generateImageLoading || currentScene.image_state" />
                                        <Top v-else />
                                    </el-icon>
                                </div>
                            </div>
                        </div>
                    </div>
                    <el-popover ref="modelPopoverRef" popper-class="model-popover" :virtual-ref="modelButtonRef"
                        virtual-triggering placement="bottom" width="min(100vw,380px)" trigger="click">
                        <xl-models v-model="currentSceneForm.model_id" @select="handleModelSelect" no-init
                            scene="scene_image" />
                    </el-popover>
                    <div class="flex flex-column grid-gap-2 px-4 pt-4">
                        <span>场景记录</span>
                    </div>
                    <el-scrollbar class="flex-1">
                        <div class="grid-columns-2 grid-gap-4 p-4" v-if="taskList.length > 0">
                            <div class="grid-column-1 task-item" v-for="item in taskList" :key="item.id">
                                <el-avatar :src="item.result.image_path" fit="contain" shape="square" :size="206">
                                </el-avatar>
                                <div class="flex flex-center grid-gap-2 task-item-replace pointer"
                                    v-if="item.status==='success'&&item.result.image_path !== currentSceneForm.image"
                                    @click="handleReplaceScene(item)">
                                    <el-icon>
                                        <Loading class="circular" v-if="replaceSceneLoading" />
                                        <IconReplaceSvg v-else />
                                    </el-icon>
                                    <span class="h10 text-nowrap">替换原始</span>
                                </div>
                            </div>
                        </div>
                        <el-empty v-else description="暂无原始记录" />
                    </el-scrollbar>
                </template>
                <el-empty v-else description="点击场景名称选择场景" />
            </div>
        </div>
        <div class="p-4 w-100 flex grid-gap-4 flex-center">
            <el-button bg text size="large" @click="prevStep">
                <el-icon size="16">
                    <IconPrevStepSvg />
                </el-icon>
                <span>上一步</span>
            </el-button>
            <el-button type="success" size="large"
                :disabled="sceneList.filter((item: any) => item.status === 'initializing').length <= 0"
                @click="handleBatchGenerate">
                <el-icon size="16">
                    <IconBatchSvg />
                </el-icon>
                <span>批量生成</span>
            </el-button>
            <el-button type="success" size="large" @click="nextStep">
                <span>下一步</span>
                <el-icon size="16" class="ml-2">
                    <IconNextStepSvg />
                </el-icon>
            </el-button>
        </div>
        <el-dialog v-model="batchGenerateDialogVisible" class="generate-storyboard-dialog" draggable width="800px">
            <template #header>
                <span class="font-weight-600">批量生成场景</span>
            </template>
            <xl-models title="模型" v-model="currentSceneForm.model_id" @select="handleModelSelect" no-init
                class="flex-1 bg-overlay rounded-4 p-4" scene="scene_image" />
            <template #footer>
                <el-button type="info" @click="batchGenerateDialogVisible = false"
                    :disabled="batchGenerateLoading">取消</el-button>
                <div class="flex-1"></div>
                <el-button type="success" icon="Check" @click="submitBatchGenerate"
                    :disabled="!currentSceneForm.model_id" :loading="batchGenerateLoading">生成</el-button>
            </template>
        </el-dialog>
        <xl-scene-create ref="sceneCreateRef" @success="handleCreateSceneSuccess" />
    </div>
</template>
<style lang="scss" scoped>
.draw-module {
    height: calc(100vh - var(--xl-header-height));
    margin: 0 auto;
    padding: 20px;
    overflow: hidden;

    .preview-image {
        width: 100%;
        flex: 1;
        --el-avatar-bg-color: var(--el-bg-color);

        .input-upload {
            :deep(.el-upload-dragger) {
                border: none;
            }
        }
    }

    .scene-form-wrapper {
        width: 450px;
        height: 100%;
        overflow: hidden;
    }

    .scene-item {
        height: 260px;
        position: relative;
        overflow: hidden;
        box-shadow: inset 0 0 0px 2px transparent;

        &:hover {
            background-color: var(--el-fill-color-dark);

            .scene-delete {
                opacity: 1;
            }
        }

        &.active {
            box-shadow: inset 0 0 0px 2px var(--el-color-success);
        }

        .scene-avatar {
            height: 260px;
            width: 100%;
            border-radius: 0px;
        }

        .scene-status {
            position: absolute;
            top: 0;
            right: 0;
            width: 100%;
            padding: 10px;
            justify-content: flex-start;
            align-items: flex-start;
            z-index: 1;
        }

        .scene-info {
            position: absolute;
            bottom: 0px;
            left: 0;
            width: 100%;
            padding: 10px;
            justify-content: flex-start;
            align-items: flex-start;
            z-index: 1;
        }


        .scene-tag,
        .scene-name {
            background-color: rgba(0, 0, 0, 0.25);
            backdrop-filter: blur(10px);
            color: #FFFFFF;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;

            &--primary {
                color: var(--el-color-primary);
            }

            &--success {
                color: var(--el-color-success);
            }

            &--warning {
                color: var(--el-color-warning);
            }

            &--danger {
                color: var(--el-color-danger);
            }

            &--info {
                color: var(--el-color-info);
            }

            &.pointer:hover {
                background-color: rgba(0, 0, 0, 0.5);
            }
        }

        .scene-delete {
            width: 28px;
            height: 28px;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }


        .scene-name {
            padding: 4px 8px;
            border-radius: 20px;
        }

        .scene-action {
            height: 50px;
            width: 100%;
        }
    }

    .scene-form {
        &-input {
            :deep(.el-input__wrapper) {
                box-shadow: none;
                background-color: var(--el-bg-color);
            }
        }

        &-select {
            :deep(.el-select__wrapper) {
                background-color: var(--el-bg-color);
            }
        }

        &-textarea {
            :deep(.el-textarea__inner) {
                box-shadow: none;
                padding: 0;
                resize: none;
            }
        }
    }

    .task-item {
        position: relative;

        .task-item-replace {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background-color: rgba(0, 0, 0, 0.5);
            padding: 5px 10px;
            border-radius: 99px;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }

        &:hover {
            .task-item-replace {
                opacity: 1;
            }
        }
    }
}

.montage-storyboard {
    --montage-storyboard-height: 187px;
    --montage-storyboard-toolbar-height: 27px;
    height: var(--montage-storyboard-height);
    background: var(--el-bg-color-page);
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 10px 10px 0 10px;

    &-scrollbar {
        flex: 1;
        padding-bottom: 10px;
        transition: flex 0.3s ease-in-out;
    }

    :deep(.montage-storyboard-scrollbar) {
        .montage-storyboard-audio-wrap {
            overflow-y: hidden;
            overflow-x: auto;

        }

        .el-scrollbar__view {
            height: 100%;
        }
    }

    &-list {
        height: 100%;
        display: flex;
        gap: 4px;
    }

    &-list-item {
        flex-shrink: 0;
        width: calc((var(--montage-storyboard-height) - var(--montage-storyboard-toolbar-height) - 10px) / 0.7);
        height: 100%;
        background: var(--el-bg-color-overlay);
        box-shadow: inset 0 0 0 2px transparent;
        display: flex;
        flex-direction: column;
        padding: 6px;
        gap: 6px;
        position: relative;

        &:hover {
            box-shadow: inset 0 0 0 2px var(--el-border-color);

            .hover-show {
                opacity: 1;
            }
        }

        &.active {
            box-shadow: inset 0 0 0 2px var(--el-color-success);
        }

        .icon-button {
            cursor: pointer;
            background-color: rgba(255, 255, 255, 0.15);
            padding: 3px;
            border-radius: 4px;

            &:hover {
                color: var(--el-color-success);
            }

            &[disabled=true] {
                color: var(--el-text-color-disabled);
                cursor: not-allowed;
            }
        }

        .hover-show {
            opacity: 0;
        }

        &-image {
            width: 100%;
            height: 100%;
            border-radius: 4px;
        }

        .button {
            background: rgba(0, 0, 0, 0.15);
            backdrop-filter: blur(2px);
            padding: 6px 10px;
            border-radius: 40px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;

            &:hover {
                color: var(--el-color-success);
            }
        }

        &-toolbar {
            display: flex;
            justify-content: flex-start;
            align-items: flex-start;
            align-content: flex-start;
            gap: 6px;
            flex-wrap: wrap;

            .button {
                background-color: var(--el-bg-color-overlay);
            }
        }

        &-plus {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            right: -17px;
            width: 30px;
            height: 30px;
            z-index: 3000;
            background-color: var(--el-color-success);
            color: var(--el-bg-color);
            border-radius: 4px;
            display: none;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: opacity 0.3s ease-in-out;

            &:hover {
                background-color: var(--el-color-success-dark-2);
            }

            &.active {
                display: flex;
            }
        }
    }
}
</style>