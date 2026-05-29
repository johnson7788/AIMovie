<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { useUserStore } from '@/stores';
import { ElMessage } from 'element-plus';
import IconStyleSvg from '@/svg/icon/icon-style.vue'
import IconUploadImageSvg from '@/svg/icon/icon-upload-image.vue';
const userStore = useUserStore();
const props = withDefaults(defineProps<{
    find: any
}>(), {
    find: () => ({}),
});
const emit = defineEmits(['update']);
const find = ref<any>(props.find);
watch(() => props.find, (newVal) => {
    find.value = newVal;
    form.id = newVal.id;
    form.title = newVal.title;
    form.aspect_ratio = newVal.aspect_ratio;
    form.style_id = newVal.style_id;
    form.overall_hook = newVal.overall_hook;
    form.core_catharsis_mechanism = newVal.core_catharsis_mechanism;
    form.main_conflict = newVal.main_conflict;
    form.relationship_mainline = newVal.relationship_mainline;
    form.description = newVal.description;
    form.background_description = newVal.background_description;
    form.outline = newVal.outline;
    styleFind.value = newVal.style;
});
const uploadCoverDialogVisible = ref(false);
const uploadCoverRef = ref();
const uploadCoverSuccess = ref<any>({});
const openUploadCoverDialog = () => {
    uploadCoverDialogVisible.value = true;
}
const uploadCoverLoading = ref(false);
const beforeUpload = (_file: File) => {
    if (!userStore.hasLogin()) {
        uploadCoverRef.value?.clearFiles();
        return false;
    }
    uploadCoverLoading.value = true;
    return true;
}
const handleUploadSuccess = (response: any) => {
    if (response.code === ResponseCode.SUCCESS) {
        switch (response.data.dir_name) {
            case 'drama/cover':
                uploadCoverSuccess.value = response.data;
                uploadCoverRef.value?.clearFiles();
                $http.post('/app/shortplay/api/Works/updateCover', {
                    id: props.find.id,
                    cover: response.data.url,
                }).then((res: any) => {
                    if (res.code === ResponseCode.SUCCESS) {
                        ElMessage.success('上传封面成功');
                    } else {
                        ElMessage.info(res.msg);
                    }
                }).catch(() => {
                    ElMessage.error('上传封面失败');
                }).finally(() => {
                    uploadCoverDialogVisible.value = false;
                    uploadCoverLoading.value = false;
                    emit('update');
                });
                break;
        }
    } else {
        ElMessage.error(response.msg);
        uploadCoverLoading.value = false;
    }
}
const handleUploadError = () => {
    uploadCoverRef.value?.clearFiles();
    uploadCoverLoading.value = false;
}
const modelButtonRef = ref();
const modelPopoverRef = ref();
const modelPopover = ref(false);
const selectedModel = ref<any>({ id: '' });
const modelLoading = ref(false);
const handleModelSelect = (item: any) => {
    selectedModel.value = item;
    modelLoading.value = true;
    $http.post('/app/shortplay/api/Generate/dramaCover', {
        id: props.find.id,
        model_id: selectedModel.value.id,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            find.value.cover = null;
            find.value.cover_state = 1;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('生成封面失败');
    }).finally(() => {
        modelLoading.value = false;
        modelPopoverRef.value?.hide();
    });
}
const openGenerateCover = (e: Event) => {
    if (modelLoading.value) return;
    modelButtonRef.value = e.target;
    nextTick(() => {
        modelPopover.value = true;
    })
}
const viewAction = ref('view');
const form = reactive<any>({
    id: '',
    title: '',
    aspect_ratio: '',
    style_id: '',
    overall_hook: '',
    core_catharsis_mechanism: '',
    main_conflict: '',
    relationship_mainline: '',
    description: '',
    background_description: '',
    outline: '',
});
const styleFind = ref<any>({ id: '' });
const styleButtonRef = ref();
const stylePopoverRef = ref();
const handleStyleSelect = (item: any) => {
    styleFind.value = item;
    stylePopoverRef.value?.hide();
}
const loading = ref(false);
const handleSave = () => {
    if (loading.value) return;
    loading.value = true;
    $http.post('/app/shortplay/api/Drama/update', form).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success('保存成功');
            viewAction.value = 'view';
            emit('update');
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('保存失败');
    }).finally(() => {
        loading.value = false;
    });
}
onMounted(() => {
    if (props.find.id) {
        form.id = props.find.id;
        form.title = props.find.title;
        form.aspect_ratio = props.find.aspect_ratio;
        form.style_id = props.find.style_id;
        form.overall_hook = props.find.overall_hook;
        form.core_catharsis_mechanism = props.find.core_catharsis_mechanism;
        form.main_conflict = props.find.main_conflict;
        form.relationship_mainline = props.find.relationship_mainline;
        form.description = props.find.description;
        form.background_description = props.find.background_description;
        form.outline = props.find.outline;
        styleFind.value = props.find.style;
    }
})
</script>
<template>
    <div class="flex drama-details">
        <div class="drama-image">
            <el-image :src="find.cover" class="drama-image" :preview-src-list="[find.cover]">
                <template #placeholder>
                    <div class="flex flex-center h-100 bg rounded-4">
                        <div class="flex flex-column grid-gap-1 flex-center" v-if="find.cover_state">
                            <el-icon size="40">
                                <Loading class="circular" />
                            </el-icon>
                            <span class="h10 font-weight-600 text-success">AI正在生成封面...</span>
                        </div>
                        <div class="flex flex-column grid-gap-1" v-else>
                            <span>{{ find.title }}</span>
                        </div>
                    </div>
                </template>
            </el-image>
            <div class="drama-image-action flex flex-center">
                <div class="h10 flex grid-gap-2 action-cover" v-if="!modelLoading">
                    <el-button type="success" @click.stop="openGenerateCover($event)" size="small">AI生成</el-button>
                    <el-button type="info" @click.stop="openUploadCoverDialog()" size="small">上传</el-button>
                </div>
                <div class="h10 flex grid-gap-2 action-cover" v-else-if="modelLoading">
                    <span class="text-success">提交中...</span>
                </div>
            </div>
        </div>
        <div class="flex flex-center grid-gap-4 position-edit" @click="viewAction = 'edit'"
            v-if="viewAction === 'view'">
            <el-icon>
                <Edit />
            </el-icon>
            <span>编辑</span>
        </div>
        <div class="flex flex-column grid-gap-4 flex-1" v-if="viewAction === 'view'">
            <div class="flex grid-gap-1 rounded-4 p-4 hover-bg-page">
                <span class="font-weight-600 text-nowrap">剧名：</span>
                <span>{{ find.title }}</span>
            </div>
            <div class="flex grid-gap-1 rounded-4 p-4 hover-bg-page">
                <span class="font-weight-600 text-nowrap">集数：</span>
                <span>全 {{ find.episode_sum }} 集，</span>
                <span>更新至 {{ find.episode_num }} 集</span>
            </div>
            <div class="flex grid-gap-1 rounded-4 p-4 hover-bg-page">
                <span class="font-weight-600 text-nowrap">时长：</span>
                <span>每集 {{ find.episode_duration }} 秒</span>
            </div>
            <div class="flex grid-gap-1 rounded-4 p-4 hover-bg-page flex-y-center">
                <span class="font-weight-600 text-nowrap">画面：</span>
                <span class="icon-aspect-ratio" :view="find.aspect_ratio"></span>
                <el-tag type="success" size="small">{{ find.aspect_ratio }}</el-tag>
            </div>
            <div class="flex grid-gap-1 rounded-4 p-4 hover-bg-page">
                <span class="font-weight-600 text-nowrap">画风：</span>
                <el-tag type="warning" size="small">{{ find.style.name }}</el-tag>
            </div>
            <div class="flex grid-gap-1 rounded-4 p-4 hover-bg-page">
                <span class="font-weight-600 text-nowrap">创建：</span>
                <span class="text-secondary">{{ find.create_time }}</span>
            </div>
            <div class="flex grid-gap-1 rounded-4 p-4 hover-bg-page">
                <span class="font-weight-600 text-nowrap">卖点：</span>
                <span class="text-info text-pre">{{ find.overall_hook }}</span>
            </div>
            <div class="flex grid-gap-1 rounded-4 p-4 hover-bg-page">
                <span class="font-weight-600 text-nowrap">爽点：</span>
                <span class="text-info text-pre">{{ find.core_catharsis_mechanism }}</span>
            </div>
            <div class="flex grid-gap-1 rounded-4 p-4 hover-bg-page">
                <span class="font-weight-600 text-nowrap">主线：</span>
                <span class="text-info text-pre">{{ find.main_conflict }}</span>
            </div>
            <div class="flex grid-gap-1 rounded-4 p-4 hover-bg-page">
                <span class="font-weight-600 text-nowrap">关系：</span>
                <span class="text-info text-pre">{{ find.relationship_mainline }}</span>
            </div>
            <div class="flex grid-gap-1 rounded-4 p-4 hover-bg-page">
                <span class="font-weight-600 text-nowrap">描述：</span>
                <span class="text-info text-pre">{{ find.description }}</span>
            </div>
            <div class="flex grid-gap-1 rounded-4 p-4 hover-bg-page">
                <span class="font-weight-600 text-nowrap">背景：</span>
                <span class="text-info text-pre">{{ find.background_description }}</span>
            </div>
            <div class="flex grid-gap-1 rounded-4 p-4 hover-bg-page">
                <span class="font-weight-600 text-nowrap">大纲：</span>
                <span class="text-secondary text-pre">{{ find.outline }}</span>
            </div>
        </div>
        <el-form v-else size="large" class="flex-1" :model="form" :disabled="loading">
            <el-form-item label="剧名">
                <el-input v-model="form.title" class="input-textarea" />
            </el-form-item>
            <el-form-item label="画面">
                <xl-aspect-ratio v-model="form.aspect_ratio" />
            </el-form-item>
            <el-form-item label="画风">
                <div class="flex flex-center grid-gap-2 input-button rounded-4 py-2 px-6" ref="styleButtonRef">
                    <template v-if="!styleFind.id">
                        <el-icon alt="风格" class="icon-style">
                            <IconStyleSvg />
                        </el-icon>
                        <span class="h10">风格</span>
                    </template>
                    <template v-else>
                        <el-avatar :src="styleFind.image" :alt="styleFind.name" class="icon-style"></el-avatar>
                        <span class="h10">{{ styleFind.name }}</span>
                    </template>
                </div>
            </el-form-item>
            <el-form-item label="卖点">
                <el-input v-model="form.overall_hook" type="textarea" :autosize="{ minRows: 4, maxRows: 20 }"
                    class="input-textarea" />
            </el-form-item>
            <el-form-item label="爽点">
                <el-input v-model="form.core_catharsis_mechanism" type="textarea" :autosize="{ minRows: 4, maxRows: 20 }"
                    class="input-textarea" />
            </el-form-item>
            <el-form-item label="主线">
                <el-input v-model="form.main_conflict" type="textarea" :autosize="{ minRows: 4, maxRows: 20 }"
                    class="input-textarea" />
            </el-form-item>
            <el-form-item label="关系">
                <el-input v-model="form.relationship_mainline" type="textarea" :autosize="{ minRows: 4, maxRows: 20 }"
                    class="input-textarea" />
            </el-form-item>
            <el-form-item label="描述">
                <el-input v-model="form.description" type="textarea" :autosize="{ minRows: 4, maxRows: 20 }"
                    class="input-textarea" />
            </el-form-item>
            <el-form-item label="背景">
                <el-input v-model="form.background_description" type="textarea" :autosize="{ minRows: 4, maxRows: 20 }"
                    class="input-textarea" />
            </el-form-item>
            <el-form-item label="大纲">
                <el-input v-model="form.outline" type="textarea" :autosize="{ minRows: 10, maxRows: 50 }"
                    class="input-textarea" />
            </el-form-item>
            <div class="flex flex-x-flex-end flex-y-center grid-gap-4">
                <el-button type="info" bg text @click="viewAction = 'view'" :disabled="loading">取消</el-button>
                <el-button type="success" bg text @click="handleSave" :loading="loading">保存</el-button>
            </div>
        </el-form>
        <el-popover ref="stylePopoverRef" :virtual-ref="styleButtonRef" virtual-triggering placement="bottom-start"
            width="min(100vw,880px)" trigger="click">
            <xl-style v-model="form.style" @select="handleStyleSelect" />
        </el-popover>
        <el-dialog v-model="uploadCoverDialogVisible" class="drama-dialog" draggable>
            <template #header>
                <span class="font-weight-600">《{{ find.title }}》上传封面</span>
            </template>
            <el-upload ref="uploadCoverRef" class="input-upload flex-1" drag v-loading="uploadCoverLoading"
                :data="{ dir_name: 'drama/cover', dir_title: '剧本封面' }"
                :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')" :before-upload="beforeUpload"
                :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1" type="cover"
                :on-success="handleUploadSuccess" :show-file-list="false" :on-error="handleUploadError">
                <template v-if="!uploadCoverSuccess.url">
                    <el-icon class="el-icon--upload">
                        <IconUploadImageSvg />
                    </el-icon>
                    <div class="el-upload__text">
                        <span class="h10">拖拽剧本封面到此处或</span>
                        <span class="h10">点击上传</span>
                    </div>
                    <div class="el-upload__text">
                        <span class="h10">支持上传格式：</span>
                        <span class="h10">PNG, JPG, JPEG</span>
                    </div>
                    <div class="el-upload__text">
                        <span class="h10">封面比例：</span>
                        <span class="h10">4:3</span>
                    </div>
                </template>
                <template v-else>
                    <el-image :src="uploadCoverSuccess.url" class="image-cover" fit="contain"></el-image>
                </template>
            </el-upload>
        </el-dialog>
        <el-popover v-model:visible="modelPopover" ref="modelPopoverRef" :virtual-ref="modelButtonRef"
            virtual-triggering placement="bottom-start" width="min(100vw,380px)" trigger="click">
            <xl-models v-model="selectedModel.id" @select="handleModelSelect" scene="drama_cover" no-init
                v-loading="modelLoading" />
        </el-popover>
    </div>
</template>
<style lang="scss" scoped>
@media only screen and (max-width: 1280px) {
    .drama-details {
        flex-direction: column;
    }

}

.drama-details {
    width: min(100%, 1280px);
    margin: 0 auto;
    padding: 20px;
    background-color: var(--el-bg-color-overlay);
    border-radius: 8px;
    box-shadow: 0 0 10px 0 rgba(0, 0, 0, 0.1);
    display: flex;
    gap: 20px;
    position: relative;

    .drama-image {
        width: 200px;
        height: 300px;
        border-radius: 8px;
        position: relative;

        .drama-image-action {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
            padding: 10px;

            .el-button+.el-button {
                margin-left: 0;
            }
        }

        :deep(img) {
            transition: transform 0.15s;
            transform: scale(1);
        }

        &:hover {
            .drama-image-action {
                opacity: 1;
            }
        }
    }

    .text-pre {
        white-space: pre-wrap;
    }

    .position-edit {
        position: absolute;
        top: 10px;
        right: 10px;
        background-color: var(--el-bg-color-overlay);
        padding: 10px;
        border-radius: 8px;
        box-shadow: 0 0 10px 0 rgba(0, 0, 0, 0.1);
        cursor: pointer;
        transition: all 0.3s ease-in-out;
        opacity: 0;

        &:hover {
            background-color: var(--el-bg-color-page);
        }
    }

    &:hover {
        .position-edit {
            opacity: 1;
        }
    }

    .input-textarea {
        --el-input-bg-color: var(--el-bg-color-page);
        --el-input-border: none;

        :deep(.el-textarea__inner) {
            box-shadow: none;
            resize: none;
        }

        :deep(.el-input__wrapper) {
            box-shadow: none;
        }
    }

    .input-button {
        background-color: var(--el-fill-color-darker);
        cursor: pointer;

        &:hover {
            background-color: var(--el-fill-color-dark);
        }
    }

    .icon-actor,
    .icon-style,
    .icon-model {
        font-size: 20px;
        width: 22px;
        height: 22px;
    }

}
</style>