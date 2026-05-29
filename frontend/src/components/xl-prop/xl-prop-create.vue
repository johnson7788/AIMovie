<script setup lang="ts">
import { $http } from '@/common/http';
import { ResponseCode } from '@/common/const';
import { ElMessage } from 'element-plus';
import IconModelSvg from '@/svg/icon/icon-model.vue';
import IconPropSvg from '@/svg/icon/icon-actor.vue';
import IconPropThreeViewSvg from '@/svg/icon/icon-actor-three-view.vue';
import IconImageSvg from '@/svg/icon/icon-image.vue';
import IconUploadImageSvg from '@/svg/icon/icon-upload-image.vue';
const emit = defineEmits(['success']);
const propDialogVisible = ref(false);
const propForm = reactive<any>({
    id: '',
    drama_id: '',
    episode_id: '',
    image_state: false,
    image_model_id: '',
    three_view_image_state: false,
    three_view_model_id: '',
    status_enum: { value: 'initializing', label: '待初始化' },
    name: '',
    image: '',
    three_view_image: '',
    description: '',
    image_reference_state: false,
    reference_image: '',
})
const propFormRef = ref<any>(null);
const propLoading = ref(false);
const propFormRules = reactive({
    image_model_id: [{ required: true, message: '请选择图片模型', trigger: 'change' }],
    three_view_model_id: [{ required: true, message: '请选择三维模型', trigger: 'change' }],
    description: [{ required: true, message: '请输入备注', trigger: 'change' }],
})
const showForm = ref(false);
const openPropCreateDialog = (prop?: any, drama_id?: string | number, episode_id?: string | number) => {
    propDialogVisible.value = true;
    showForm.value = true;
    propImageModel.value = 'description';
    nextTick(() => {
        if (prop) {
            propForm.id = prop.id;
            propForm.image = prop.image;
            propForm.three_view_image = prop.three_view_image;
            propForm.name = prop.name;
            propForm.description = prop.description;
            propForm.drama_id = drama_id;
            propForm.episode_id = episode_id;
        } else {
            propForm.drama_id = drama_id;
            propForm.episode_id = episode_id;
        }
    })
}
const uploadProp = (prop?: any, drama_id?: string | number, episode_id?: string | number) => {
    propDialogVisible.value = true;
    showForm.value = false;
    propImageModel.value = 'upload';
    nextTick(() => {
        if (prop) {
            propForm.id = prop.id;
            propForm.image = prop.image;
            propForm.three_view_image = prop.three_view_image;
            propForm.name = prop.name;
            propForm.description = prop.description;
            propForm.drama_id = drama_id;
            propForm.episode_id = episode_id;
        } else {
            propForm.drama_id = drama_id;
            propForm.episode_id = episode_id;
        }
    })
}
const cancelPropDialog = () => {
    propFormRef.value?.resetFields();
    propDialogVisible.value = false;
    propForm.id = '';
    propForm.name = '';
    propForm.description = '';
    propForm.image_model_state = false;
    propForm.image_model_id = '';
    propForm.three_view_model_state = false;
    propForm.three_view_model_id = '';
    propForm.status_enum = { value: 'initializing', label: '待初始化' };
    propForm.image = '';
    propForm.three_view_image = '';
    propForm.drama_id = '';
    propForm.episode_id = '';
}
const submitPropDialog = (callback?: () => void) => {
    $http.post('/app/shortplay/api/Prop/update', propForm).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            propForm.id = res.data.id;
            if (callback) {
                callback();
            } else {
                cancelPropDialog();
            }
            emit('success');
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('更新失败');
    })
}
const uploadImageRef = ref<any>(null);
const uploadReferenceImageRef = ref<any>(null);
const uploadHeadimgLoading = ref(false);
const uploadThreeViewLoading = ref(false);
const uploadLoading = ref(false);
const handleUploadSuccess = (response: any) => {
    if (response.code === ResponseCode.SUCCESS) {
        switch (response.data.dir_name) {
            case 'prop/image':
                uploadHeadimgLoading.value = false;
                propForm.image = response.data.url;
                uploadImageRef.value?.clearFiles();
                break;
            case 'prop/three_view':
                uploadThreeViewLoading.value = false;
                propForm.three_view_image = response.data.url;
                uploadImageRef.value?.clearFiles();
                break;
            case 'prop/reference':
                uploadLoading.value = false;
                propForm.image_reference_state = true;
                propForm.reference_image = response.data.url;
                uploadReferenceImageRef.value?.clearFiles();
                break;
        }
    } else {
        ElMessage.error(response.msg);
    }
}
const handleUploadError = () => {
    uploadImageRef.value?.clearFiles();
    uploadReferenceImageRef.value?.clearFiles();
}
const propHeadimgButtonRef = ref();
const propHeadimgPopoverRef = ref();
const propHeadimgModel = ref<any>({});
const handlePropHeadimgSelect = (item?: any) => {
    if (item) {
        propForm.image_model_id = item.id;
        propForm.image_state = true;
        propHeadimgModel.value = item;
    } else {
        propForm.image_model_id = '';
        propForm.image_state = false;
        propHeadimgModel.value = {};
    }
    propHeadimgPopoverRef.value?.hide();
}
const propThreeViewModelButtonRef = ref();
const propThreeViewModelPopoverRef = ref();
const propImageThreeViewModel = ref<any>({});
const handlePropThreeViewModelSelect = (item?: any) => {
    if (item) {
        propForm.three_view_model_id = item.id;
        propImageThreeViewModel.value = item;
        propForm.three_view_image_state = true;
    } else {
        propForm.three_view_model_id = '';
        propImageThreeViewModel.value = {};
        propForm.three_view_image_state = false;
    }
    propThreeViewModelPopoverRef.value?.hide();
}
const generateImageLoading = ref(false);
const handleGenerateImage = () => {
    if (generateImageLoading.value || propForm.status_enum.value === 'pending') return;
    if (!propForm.id) {
        return submitPropDialog(handleGenerateImage);
    }
    generateImageLoading.value = true;
    $http.post('/app/shortplay/api/Prop/initializing', propForm).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            propForm.status = res.data.status;
            propForm.status_enum = res.data.status_enum;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('生成图片失败');
    }).finally(() => {
        generateImageLoading.value = false;
    })
}
const subscribe = (channel: string, res: any) => {
    if (channel === 'generatepropimage') {
        if (res.id === propForm.id) {
            propForm.status_enum = res.status;
            if (res.image) {
                propForm.image = res.image;
            } else {
                generateImageLoading.value = false;
            }
        }
    } else if (channel === 'generatepropthreeviewimage') {
        if (res.id === propForm.id) {
            propForm.status_enum = res.status;
            if (res.image) {
                propForm.three_view_image = res.image;
            } else {
                generateImageLoading.value = false;
            }
        }
    }
}
const propImageModel = ref('description');
const uploadImageModel = ref('image');
defineExpose({
    open: openPropCreateDialog,
    upload: uploadProp,
    close: cancelPropDialog,
    subscribe: subscribe
})
</script>
<template>
    <div>
        <el-dialog v-model="propDialogVisible" class="generate-scene-dialog" draggable :width="showForm?'min(100%,840px)':'min(100%,426px)'"
            @close="cancelPropDialog">
            <template #header>
                <span class="font-weight-600" v-if="showForm">上传物品</span>
                <span class="font-weight-600" v-else-if="!propForm.id">创建物品</span>
                <span class="font-weight-600" v-else>编辑物品</span>
            </template>
            <el-form label-position="top" :model="propForm" :rules="propFormRules" ref="propFormRef" class="prop-form"
                :disabled="propForm.status_enum.value !== 'initializing'">
                <div class="flex grid-gap-4 flex-y-flex-start">
                    <div class="flex-1 grid-columns-6 grid-gap-4" v-if="showForm">
                        <el-form-item label="物品名称" prop="title" class="grid-column-6">
                            <el-input v-model="propForm.name" placeholder="请输入物品名称"
                                class="prop-form-input bg-overlay" />
                        </el-form-item>
                        <el-form-item label="物品图" class="grid-column-6">
                            <div class="flex flex-column grid-gap-4 w-100">
                                <el-segmented v-model="propImageModel" class="tabs-segmented"
                                    :options="[{ label: '文本生成', value: 'description' }, { label: '本地上传', value: 'upload' }]" />
                                <div class="bg-overlay rounded-4 p-4 w-100">
                                    <el-input v-model="propForm.description" placeholder="请输入物品描述" size="small"
                                        class="prop-form-textarea" type="textarea"
                                        :autosize="{ minRows: 6, maxRows: 20 }" />
                                    <div class="flex flex-y-center grid-gap-2 line-height-1 mt-4"
                                        v-if="propImageModel === 'description'">
                                        <div class="bg rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover"
                                            ref="propHeadimgButtonRef" title="选择使用AI生成图">
                                            <template v-if="propHeadimgModel.id">
                                                <el-avatar :src="propHeadimgModel.icon" :alt="propHeadimgModel.name"
                                                    shape="square" :size="16"></el-avatar>
                                                <span class="h10 text-ellipsis-1" style="max-width: 60px;">{{
                                                    propHeadimgModel.name
                                                    }}</span>
                                                <el-icon size="16" class="pointer"
                                                    @click.stop="handlePropHeadimgSelect()">
                                                    <Close />
                                                </el-icon>
                                            </template>
                                            <template v-else>
                                                <el-icon size="16">
                                                    <IconModelSvg />
                                                </el-icon>
                                                <span class="h10 overflow-hidden text-nowrap"
                                                    style="max-width: 60px;">物品图</span>
                                                <el-icon size="16">
                                                    <ArrowDown />
                                                </el-icon>
                                            </template>
                                        </div>
                                        <div class="bg rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover"
                                            ref="propThreeViewModelButtonRef" title="选择使用AI生成三视图">
                                            <template v-if="propImageThreeViewModel.id">
                                                <el-avatar :src="propImageThreeViewModel.icon"
                                                    :alt="propImageThreeViewModel.name" shape="square"
                                                    :size="16"></el-avatar>
                                                <span class="h10 text-ellipsis-1" style="max-width: 60px;">{{
                                                    propImageThreeViewModel.name }}</span>
                                                <el-icon size="16" class="pointer"
                                                    @click.stop="handlePropThreeViewModelSelect()">
                                                    <Close />
                                                </el-icon>
                                            </template>
                                            <template v-else>
                                                <el-icon size="16">
                                                    <IconModelSvg />
                                                </el-icon>
                                                <span class="h10 overflow-hidden text-nowrap"
                                                    style="max-width: 60px;">三视图</span>
                                                <el-icon size="16">
                                                    <ArrowDown />
                                                </el-icon>
                                            </template>
                                        </div>
                                        <el-upload ref="uploadReferenceImageRef" title="添加参考图"
                                            :data="{ dir_name: 'prop/reference', dir_title: '物品图参考照片' }"
                                            :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                                            :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1"
                                            type="cover" :disabled="uploadLoading"
                                            :before-upload="() => { uploadLoading = true; return true; }"
                                            :on-success="handleUploadSuccess" :show-file-list="false"
                                            :on-error="() => { uploadLoading = false; handleUploadError() }">
                                            <div
                                                class="bg rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover">
                                                <el-popover placement="top" :disabled="!propForm.reference_image"
                                                    width="fit-content">
                                                    <el-avatar :src="propForm.reference_image" fit="contain" :size="130"
                                                        shape="square"></el-avatar>
                                                    <template #reference>
                                                        <el-icon size="16"
                                                            v-if="!propForm.reference_image || uploadLoading">
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
                                            style="background-color: #FFFFFF;color:#141414;"
                                            @click="handleGenerateImage">
                                            <el-icon size="20">
                                                <Loading class="circular" v-if="generateImageLoading||propForm.status_enum.value === 'pending'" />
                                                <Top v-else />
                                            </el-icon>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </el-form-item>
                    </div>
                    <div class="flex flex-column grid-gap-4 p-4 bg-overlay rounded-4"
                        v-if="propImageModel === 'description'">
                        <el-avatar :src="propForm.image" shape="square" :size="360"
                            style="--el-avatar-bg-color:var(--el-bg-color-overlay)">
                            <div class="flex flex-column flex-center grid-gap-2"
                                v-if="propForm.status_enum.value === 'initializing'">
                                <el-icon size="64">
                                    <Loading class="circular" v-if="generateImageLoading" />
                                    <IconImageSvg v-else />
                                </el-icon>
                                <span class="h10">填写左侧表单，使用AI生成物品图</span>
                                <div class="flex flex-center grid-gap-2 h10">
                                    <span>点击“</span>
                                    <div class="rounded-round p-1 flex flex-center grid-gap-2"
                                        style="background-color: #FFFFFF;color:#141414;">
                                        <el-icon size="14">
                                            <Top />
                                        </el-icon>
                                    </div>
                                    <span>”按钮生成</span>
                                </div>
                            </div>
                            <div class="flex flex-column flex-center grid-gap-2"
                                v-else-if="propForm.status_enum.value === 'pending'">
                                <el-icon size="64">
                                    <Loading class="circular" />
                                </el-icon>
                                <span class="h10">生成中...</span>
                            </div>
                        </el-avatar>
                    </div>
                    <div class="flex flex-column grid-gap-4 bg-overlay rounded-4 p-4" v-else>
                        <div>
                            <el-upload v-if="uploadImageModel === 'image'" ref="uploadImageRef"
                                class="input-upload rounded-4" drag
                                :data="{ dir_name: 'prop/image', dir_title: '物品图照片' }"
                                :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                                :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1" type="cover"
                                :disabled="uploadHeadimgLoading"
                                :before-upload="() => { uploadHeadimgLoading = true; return true; }"
                                :on-success="handleUploadSuccess" :show-file-list="false"
                                :on-error="() => { uploadHeadimgLoading = false; handleUploadError() }">
                                <template v-if="!propForm.image">
                                    <el-icon class="el-icon--upload">
                                        <IconUploadImageSvg />
                                    </el-icon>
                                    <div class="el-upload__text">
                                        <span class="h10">拖拽物品图照片到此处或</span>
                                        <span class="h10">点击上传</span>
                                    </div>
                                    <div class="el-upload__text">
                                        <span class="h10">支持上传格式：</span>
                                        <span class="h10">PNG, JPG, JPEG</span>
                                    </div>
                                    <div class="el-upload__text">
                                        <span class="h10">图照片建议比例：</span>
                                        <span class="h10">1:1</span>
                                    </div>
                                </template>
                                <template v-else>
                                    <el-image :src="propForm.image" class="image-cover" fit="contain"></el-image>
                                </template>
                            </el-upload>
                            <el-upload v-else-if="uploadImageModel === 'three_view'" ref="uploadImageRef"
                                class="input-upload rounded-4" drag
                                :data="{ dir_name: 'prop/three_view', dir_title: '物品三视图' }"
                                :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                                :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1" type="cover"
                                :disabled="uploadThreeViewLoading"
                                :before-upload="() => { uploadThreeViewLoading = true; return true; }"
                                :on-success="handleUploadSuccess" :show-file-list="false"
                                :on-error="() => { uploadThreeViewLoading = false; handleUploadError() }">
                                <template v-if="!propForm.three_view_image">
                                    <el-icon class="el-icon--upload">
                                        <IconUploadImageSvg />
                                    </el-icon>
                                    <div class="el-upload__text">
                                        <span class="h10">拖拽物品三视图到此处或</span>
                                        <span class="h10">点击上传</span>
                                    </div>
                                    <div class="el-upload__text">
                                        <span class="h10">支持上传格式：</span>
                                        <span class="h10">PNG, JPG, JPEG</span>
                                    </div>
                                    <div class="el-upload__text">
                                        <span class="h10">图照片建议比例：</span>
                                        <span class="h10">1:1</span>
                                    </div>
                                </template>
                                <template v-else>
                                    <el-image :src="propForm.three_view_image" class="image-cover"
                                        fit="contain"></el-image>
                                </template>
                            </el-upload>
                        </div>
                        <div class="flex flex-center grid-gap-4">
                            <el-avatar :src="propForm.image" shape="square" :size="60" class="pointer"
                                @click="uploadImageModel = 'image'">
                                <div class="flex flex-column flex-center grid-gap-1"
                                    :class="{ 'text-secondary': uploadImageModel === 'three_view' }">
                                    <el-icon size="20">
                                        <Loading class="circular" v-if="uploadHeadimgLoading" />
                                        <IconPropSvg v-else />
                                    </el-icon>
                                    <span class="h10">物品图</span>
                                </div>
                            </el-avatar>
                            <el-avatar :src="propForm.three_view_image" shape="square" :size="60" class="pointer"
                                @click="uploadImageModel = 'three_view'">
                                <div class="flex flex-column flex-center grid-gap-1"
                                    :class="{ 'text-secondary': uploadImageModel === 'image' }">
                                    <el-icon size="20">
                                        <Loading class="circular" v-if="uploadThreeViewLoading" />
                                        <IconPropThreeViewSvg v-else />
                                    </el-icon>
                                    <span class="h10">三视图</span>
                                </div>
                            </el-avatar>
                        </div>
                    </div>
                </div>
            </el-form>
            <template #footer>
                <div class="flex flex-center grid-gap-2 w-100">
                    <el-button type="info" @click="cancelPropDialog" :disabled="propLoading">取消</el-button>
                    <div class="flex-1"></div>
                    <el-button type="success" @click="submitPropDialog()" :disabled="propLoading"
                        :loading="propLoading">提交</el-button>
                </div>
            </template>
        </el-dialog>
        <el-popover ref="propHeadimgPopoverRef" :virtual-ref="propHeadimgButtonRef" virtual-triggering
            :teleported="false" placement="bottom-start" width="min(100vw,380px)" trigger="click">
            <xl-models @select="handlePropHeadimgSelect" scene="prop_image" no-init />
        </el-popover>
        <el-popover ref="propThreeViewModelPopoverRef" :virtual-ref="propThreeViewModelButtonRef" virtual-triggering
            :teleported="false" placement="bottom-start" width="min(100vw,380px)" trigger="click">
            <xl-models @select="handlePropThreeViewModelSelect" scene="prop_three_view_image" no-init />
        </el-popover>
    </div>
</template>
<style lang="scss" scoped>
.input-upload {
    width: 360px;
    border: dashed 1px var(--el-border-color);

    :deep(.el-upload) {
        --el-fill-color-blank: var(--el-bg-color-overlay);
        --el-color-primary: var(--el-border-color-hover);
        --el-upload-dragger-padding-horizontal: 0;
        --el-upload-dragger-padding-vertical: 0;

        .el-upload-dragger {
            border: none;
            height: 360px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            gap: 6px;
        }
    }

    .image-cover {
        width: 360px;
        height: 360px;
    }
}


.icon-model {
    font-size: 20px;
    width: 22px;
    height: 22px;
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
</style>