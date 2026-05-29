<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import IconBatchSvg from '@/svg/icon/icon-batch.vue';
import IconModelSvg from '@/svg/icon/icon-model.vue';
import IconReplaceSvg from '@/svg/icon/icon-replace.vue';
import IconPropSvg from '@/svg/icon/icon-prop.vue';
import { useUserStore, useRefs } from '@/stores';
import { useRoute } from 'vue-router';
import { Loading } from '@element-plus/icons-vue';
import { usePush } from '@/composables/usePush';
const route = useRoute();
const userStore = useUserStore();
const { USERINFO } = useRefs(userStore);
const drama_id = ref<string | number>(route.params.drama_id as string | number)
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
const PropSearch = reactive({
    type: 'drama',
    name: '',
    prop_id: '',
    drama_id: drama_id.value
})
const propList = ref<any[]>([]);
const loading = ref(false);
const propCreateRef = ref<any>(null);
const currentProp = ref<any>();
const currentPropForm = ref<any>({
    prop_id: '',
    drama_id: drama_id.value,
    name: '',
    description: '',
    image_model_id: null,
    three_view_model_id: null,
    image_state: false,
    three_view_image_state: false,
    image_reference_state: false,
    reference_image: '',
    image: '',
    three_view_image: '',
});
watch(propList, () => {
    try {
        const find = propList.value.find((item: any) => item.id === currentProp.value?.id);
        if (find) {
            handleCurrentProp(find)
        } else {
            const defaultProp = propList.value[0];
            if (defaultProp) {
                handleCurrentProp(defaultProp);
            } else {
                currentProp.value = undefined;
                currentPropForm.value = {
                    id: '',
                    drama_id: drama_id.value,
                    name: '',
                    description: '',
                    image_model_id: null,
                    three_view_model_id: null,
                    image_state: false,
                    three_view_image_state: false,
                    image_reference_state: false,
                    reference_image: '',
                    image: '',
                    three_view_image: '',
                };
            }
        }
    } catch (error) {
        console.error('watch propList error', error);
    }
})
const getPropList = () => {
    loading.value = true;
    $http.get('/app/shortplay/api/Prop/index', { params: PropSearch }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            propList.value = res.data;
        }
    }).catch((error) => {
        console.error('getPropList error', error);
    }).finally(() => {
        loading.value = false;
    })
}
const previewImageVisible = ref(false);
const imageList = ref<any[]>([]);
/* const handlePreviewImage = (currentItem: any) => {
    if (!currentItem.image && !currentItem.three_view_image) return;
    imageList.value = [currentItem.image, currentItem.three_view_image];
    nextTick(() => {
        previewImageVisible.value = true;
    })
} */
const taskList = ref<any[]>([]);
const taskLoading = ref(false);
const taskSearch = reactive({
    alias_id: '',
    scene: 'prop_image',
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
    }).finally(() => {
        taskLoading.value = false;
    })
}
const handleCurrentProp = (item: any) => {
    currentProp.value = item;
    currentPropForm.value.id = item.id;
    currentPropForm.value.name = item.name;
    currentPropForm.value.description = item.description;
    currentPropForm.value.image = item.image;
    currentPropForm.value.three_view_image = item.three_view_image;
    currentPropForm.value.image_reference_state = false;
    currentPropForm.value.reference_image = '';
    taskSearch.alias_id = item.id;
    getTaskList();
}
const modelPopoverRef = ref<any>(null);
const modelButtonRef = ref<any>(null);
const model = ref<any>({});
const handleModelSelect = (item?: any) => {
    if (item) {
        model.value = item;
        currentPropForm.value.image_state = true;
    } else {
        model.value = {};
        currentPropForm.value.image_model_id = null;
        currentPropForm.value.image_state = false;
    }
    modelPopoverRef.value?.hide();
}
const threeViewModelPopoverRef = ref<any>(null);
const threeViewModelButtonRef = ref<any>(null);
const threeViewModel = ref<any>({});
const handleThreeViewModelSelect = (item?: any) => {
    if (item) {
        threeViewModel.value = item;
        currentPropForm.value.three_view_image_state = true;
    } else {
        threeViewModel.value = {};
        currentPropForm.value.three_view_model_id = null;
        currentPropForm.value.three_view_image_state = false;
    }
    threeViewModelPopoverRef.value?.hide();
}
const generateImageLoading = ref(false);
const handleGenerateImage = () => {
    if (generateImageLoading.value || currentProp.value.status_enum.value === 'pending') return;
    if (!currentPropForm.value.image_model_id && !currentPropForm.value.three_view_model_id) {
        ElMessage.error('请先选择物品图模型或三视图模型');
        return;
    }
    generateImageLoading.value = true;
    $http.post('/app/shortplay/api/Prop/initializing', {
        ...currentPropForm.value,
        image: '',
        three_view_image: ''
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            currentProp.value.status = res.data.status;
            currentProp.value.status_enum = res.data.status_enum;
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
        currentPropForm.value.image_reference_state = true;
        currentPropForm.value.reference_image = response.data.url;
    } else {
        ElMessage.error(response.msg);
    }
    uploadImageRef.value?.clearFiles();
}
const handleUploadReferenceImageError = () => {
    uploadLoading.value = false;
    uploadImageRef.value?.clearFiles();
}
const replacePropLoading = ref(false);
const handleReplaceProp = (item: any) => {
    if (replacePropLoading.value) return;
    replacePropLoading.value = true;
    $http.post('/app/shortplay/api/Prop/ReplaceProp', {
        id: currentProp.value.id,
        task_id: item.id
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            currentProp.value.image = item.result.image_path;
            currentProp.value.status = res.data.status;
            currentProp.value.status_enum = res.data.status_enum;
            currentPropForm.value.image = item.result.image_path;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('替换物品失败');
    }).finally(() => {
        replacePropLoading.value = false;
    })
}
const batchGenerateDialogVisible = ref(false);
const batchGenerateLoading = ref(false);
const batchGenerateLength = ref(0);
const batchGenerateList = ref<any[]>([]);
const handleBatchGenerate = () => {
    batchGenerateDialogVisible.value = true;
    batchGenerateList.value = propList.value.filter((item: any) => item.status === 'initializing')
    batchGenerateLength.value = batchGenerateList.value.length
}
const submitBatchGenerate = () => {
    batchGenerateLoading.value = true;
    Promise.all(batchGenerateList.value.map((item: any) => {
        return $http.post('/app/shortplay/api/Prop/initializing', {
            id: item.id,
            image_reference_state: item.image ? true : false,
            reference_image: item.image ? item.image : '',
            image_state: true,
            three_view_image_state: true,
            image_model_id: model.value.id,
            three_view_model_id: threeViewModel.value.id,
        })
    })).then(() => {
        getPropList();
    }).catch((error) => {
        console.error('submitBatchGenerate error', error);
    }).finally(() => {
        batchGenerateLoading.value = false;
        batchGenerateDialogVisible.value = false;
    })
}
const handleDeleteProp = (item: any) => {
    $http.post('/app/shortplay/api/Prop/delete', {
        id: item.id,
        drama_id: drama_id.value,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            getPropList();
        } else {
            ElMessage.error(res.msg);
        }
    })
}
const { subscribe, unsubscribeAll } = usePush();
const addListener = () => {
    subscribe('private-generatepropimage-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const findItem = propList.value.find((item: any) => item.id === res.id);
        if (findItem) {
            findItem.status_enum = res.status;
            if (res.image) {
                findItem.image = res.image;
            }
        }
        propCreateRef.value?.subscribe?.('generatepropimage', res);
    });
    subscribe('private-generatepropthreeviewimage-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const findItem = propList.value.find((item: any) => item.id === res.id);
        if (findItem) {
            findItem.status_enum = res.status;
            if (res.image) {
                findItem.three_view_image = res.image;
            }
        }
        propCreateRef.value?.subscribe?.('generatepropthreeviewimage', res);
    });
}
onMounted(() => {
    getPropList();
    getDramaInfo();
    addListener();
})
onUnmounted(() => {
    console.log('props unmounted');
    unsubscribeAll();
})
</script>
<template>
    <div class="flex flex-column draw-module">
        <div class="flex-1 flex grid-gap-10 overflow-hidden">
            <div class="flex-1 flex flex-column grid-gap-4 overflow-hidden">
                <el-form class="flex flex-center grid-gap-4" @submit.prevent="getPropList">
                    <el-button type="success" size="small"
                        :disabled="propList.filter((item: any) => item.status === 'initializing').length <= 0"
                        @click="handleBatchGenerate">
                        <el-icon size="16">
                            <IconBatchSvg />
                        </el-icon>
                        <span>批量生成</span>
                    </el-button>
                    <el-form-item class="mb-0">
                        <el-input v-model="PropSearch.name" placeholder="搜索物品" clearable @change="getPropList">
                            <template #suffix>
                                <el-icon>
                                    <Search />
                                </el-icon>
                            </template>
                        </el-input>
                    </el-form-item>
                    <div class="flex-1"></div>
                </el-form>
                <el-scrollbar class="flex-1">
                    <div
                        class="grid-columns-xxl-7 grid-columns-xl-6 grid-columns-lg-5 grid-columns-md-4 grid-columns-sm-3 grid-columns-xs-2 grid-columns-p-1 grid-gap-4">
                        <div class="grid-column-1 rounded-4 p-4 prop-item flex flex-column flex-center grid-gap-4 pointer bg-overlay"
                            @click="propCreateRef?.open?.(null, PropSearch.drama_id)">
                            <el-icon class="rounded-4" size="20"
                                style="height: 40px; width: 40px;background-color: var(--el-fill-color-dark);">
                                <Plus />
                            </el-icon>
                            <span>添加物品</span>
                        </div>
                        <div class="grid-column-1 rounded-4 flex flex-column flex-center grid-gap-2 prop-item bg-overlay border"
                            :class="{ 'border-success': item.id === currentPropForm.id }" v-for="item in propList"
                            :key="item.id">
                            <el-avatar :src="item.image" class="prop-avatar bg-mosaic"
                                :class="{ 'pointer': item.image }" @click="handleCurrentProp(item)" fit="cover">
                                {{ item.name }}
                            </el-avatar>
                            <div class="prop-edit-mask flex flex-column grid-gap-4 flex-center pointer"
                                @click="handleCurrentProp(item)">
                                <div class="flex flex-center bg-overlay rounded-round p-2 pointer grid-gap-2"
                                    @click.stop="propCreateRef?.upload?.(item, PropSearch.drama_id)">
                                    <el-icon size="16">
                                        <UploadFilled />
                                    </el-icon>
                                    <span class="h10">手动上传</span>
                                </div>
                                <el-popconfirm title="确定删除该物品吗？" width="fit-content" @confirm="handleDeleteProp(item)"
                                    placement="bottom-end">
                                    <template #reference>
                                        <div class="flex flex-center bg-overlay rounded-round p-2 pointer grid-gap-2"
                                            @click.stop>
                                            <el-icon size="16">
                                                <Delete />
                                            </el-icon>
                                            <span class="h10">删除物品</span>
                                        </div>
                                    </template>
                                </el-popconfirm>
                            </div>
                            <div class="flex grid-gap-2 prop-status">
                                <div class="flex-1"></div>
                                <div class="flex flex-column flex-y-flex-end grid-gap-2">
                                    <span class="prop-tag" :class="[`prop-tag--` + item.status_enum.props.type]">
                                        {{ item.status_enum.label }}
                                    </span>
                                </div>
                            </div>
                            <div class="flex flex-column grid-gap-2 prop-info">
                                <div class="prop-name flex flex-center grid-gap-1 pointer"
                                    :class="{ 'prop-name--success': item.id === currentPropForm.id }"
                                    @click.stop="propCreateRef?.open?.(item, PropSearch.drama_id)">
                                    <el-icon size="16">
                                        <IconPropSvg />
                                    </el-icon>
                                    <span>{{ item.name }}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </el-scrollbar>
            </div>
            <div class="prop-form-wrapper bg-overlay border rounded-4 prop-form flex flex-column grid-gap-4">
                <template v-if="currentPropForm.id">
                    <div class="border-bottom flex flex-center">
                        <el-input v-model="currentPropForm.name" placeholder="物品物品" size="large"
                            class="prop-form-input flex-1">
                        </el-input>
                    </div>
                    <div class="flex flex-column grid-gap-2 px-4">
                        <span>物品描述</span>
                        <div class="bg rounded-4 p-4 border">
                            <el-input v-model="currentPropForm.description" placeholder="请输入物品描述" size="small"
                                class="prop-form-textarea" type="textarea" :autosize="{ minRows: 6, maxRows: 20 }" />
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
                                        <span class="h10">物品图</span>
                                        <el-icon size="16">
                                            <ArrowDown />
                                        </el-icon>
                                    </template>
                                </div>
                                <div class="bg-overlay rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover"
                                    ref="threeViewModelButtonRef" title="选择使用AI生成三视图">
                                    <template v-if="threeViewModel.id">
                                        <el-avatar :src="threeViewModel.icon" :alt="threeViewModel.name" shape="square"
                                            :size="16"></el-avatar>
                                        <span class="h10 text-ellipsis-1" style="max-width: 60px;">{{
                                            threeViewModel.name }}</span>
                                        <el-icon size="16" class="pointer" @click.stop="handleThreeViewModelSelect()">
                                            <Close />
                                        </el-icon>
                                    </template>
                                    <template v-else>
                                        <el-icon size="16">
                                            <IconModelSvg />
                                        </el-icon>
                                        <span class="h10">三视图</span>
                                        <el-icon size="16">
                                            <ArrowDown />
                                        </el-icon>
                                    </template>
                                </div>
                                <el-upload ref="uploadImageRef" title="添加参考图"
                                    :data="{ dir_name: 'prop/reference', dir_title: '物品参考照片' }"
                                    :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                                    :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1" type="cover"
                                    :disabled="uploadLoading"
                                    :before-upload="() => { uploadLoading = true; return true; }"
                                    :on-success="handleUploadReferenceImageSuccess" :show-file-list="false"
                                    :on-error="handleUploadReferenceImageError">
                                    <div
                                        class="bg-overlay rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover">
                                        <el-popover placement="top" :disabled="!currentPropForm.reference_image"
                                            width="fit-content">
                                            <el-avatar :src="currentPropForm.reference_image" fit="contain" :size="130"
                                                shape="square"></el-avatar>
                                            <template #reference>
                                                <el-icon size="16"
                                                    v-if="!currentPropForm.reference_image || uploadLoading">
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
                                            v-if="generateImageLoading || currentProp.status_enum.value === 'pending'" />
                                        <Top v-else />
                                    </el-icon>
                                </div>
                            </div>
                        </div>
                    </div>
                    <el-popover ref="modelPopoverRef" popper-class="model-popover" :virtual-ref="modelButtonRef"
                        virtual-triggering placement="bottom" width="min(100vw,380px)" trigger="click">
                        <xl-models v-model="currentPropForm.image_model_id" @select="handleModelSelect" no-init
                            scene="prop_image" />
                    </el-popover>
                    <el-popover ref="threeViewModelPopoverRef" popper-class="model-popover"
                        :virtual-ref="threeViewModelButtonRef" virtual-triggering placement="bottom"
                        width="min(100vw,380px)" trigger="click">
                        <xl-models v-model="currentPropForm.three_view_model_id" @select="handleThreeViewModelSelect"
                            no-init scene="prop_three_view_image" />
                    </el-popover>
                    <div class="flex flex-column grid-gap-2 px-4 pt-4">
                        <span>物品原始记录</span>
                    </div>
                    <el-scrollbar class="flex-1">
                        <div class="grid-columns-2 grid-gap-4 p-4" v-if="taskList.length > 0">
                            <div class="grid-column-1 task-item" v-for="item in taskList" :key="item.id">
                                <el-avatar :src="item.result.image_path" fit="contain" shape="square" :size="206">
                                </el-avatar>
                                <div class="flex flex-center grid-gap-2 task-item-replace pointer"
                                    v-if="item.status === 'success' && item.result.image_path !== currentPropForm.image"
                                    @click="handleReplaceProp(item)">
                                    <el-icon>
                                        <Loading class="circular" v-if="replacePropLoading" />
                                        <IconReplaceSvg v-else />
                                    </el-icon>
                                    <span class="h10 text-nowrap">替换原始</span>
                                </div>
                            </div>
                        </div>
                        <el-empty v-else description="暂无原始记录" />
                    </el-scrollbar>
                </template>
                <el-empty v-else description="点击物品名称选择物品" />
            </div>
        </div>
        <el-image-viewer :url-list="imageList" v-if="previewImageVisible" @close="previewImageVisible = false" />
        <xl-prop-create ref="propCreateRef" @success="getPropList" />
        <el-dialog v-model="batchGenerateDialogVisible" class="generate-storyboard-dialog" draggable width="800px">
            <template #header>
                <span class="font-weight-600">批量生成物品</span>
            </template>
            <div class="flex grid-gap-10">
                <xl-models title="模型" v-model="currentPropForm.image_model_id" @select="handleModelSelect" no-init
                    class="flex-1 bg-overlay rounded-4 p-4" scene="prop_image" />
                <xl-models title="三视图模型" v-model="currentPropForm.three_view_model_id"
                    @select="handleThreeViewModelSelect" class="flex-1 bg-overlay rounded-4 p-4" no-init
                    scene="prop_three_view_image" />
            </div>
            <template #footer>
                <el-button type="info" @click="batchGenerateDialogVisible = false"
                    :disabled="batchGenerateLoading">取消</el-button>
                <div class="flex-1"></div>
                <el-button type="success" icon="Check" @click="submitBatchGenerate"
                    :disabled="!currentPropForm.image_model_id || !currentPropForm.three_view_model_id"
                    :loading="batchGenerateLoading">生成</el-button>
            </template>
        </el-dialog>
    </div>
</template>
<style lang="scss" scoped>
.draw-module {
    height: calc(100vh - var(--xl-header-height) - 105px);
    margin: 0 auto;
    padding: 20px;
    overflow: hidden;

    .prop-form-wrapper {
        width: 450px;
        height: 100%;
        overflow: hidden;
    }

    .prop-item {
        height: 260px;
        position: relative;
        overflow: hidden;
        box-shadow: inset 0 0 0px 2px transparent;

        &:hover {
            background-color: var(--el-fill-color-dark);

            .prop-delete {
                opacity: 1;
            }
        }

        &.active {
            box-shadow: inset 0 0 0px 2px var(--el-color-success);
        }

        .prop-avatar {
            height: 260px;
            width: 100%;
            border-radius: 0px;
        }

        .bg-overlay {
            background-color: rgba(0, 0, 0, 0.5);
        }

        .prop-edit-mask {
            position: absolute;
            top: 0;
            left: 0;
            height: 260px;
            width: 100%;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;

            &:hover {
                opacity: 1;
            }
        }

        .prop-status {
            position: absolute;
            top: 0;
            right: 0;
            width: 100%;
            padding: 10px;
            justify-content: flex-start;
            align-items: flex-start;
            z-index: 1;
        }

        .prop-info {
            position: absolute;
            bottom: 0px;
            left: 0;
            width: 100%;
            padding: 10px;
            justify-content: flex-start;
            align-items: flex-start;
            z-index: 1;
        }


        .prop-tag,
        .prop-name {
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

        .prop-delete {
            width: 28px;
            height: 28px;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }


        .prop-name {
            padding: 4px 8px;
            border-radius: 20px;
        }

        .prop-action {
            height: 50px;
            width: 100%;
        }
    }

    .prop-form {
        &-input {
            :deep(.el-input__wrapper) {
                box-shadow: none;
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
</style>