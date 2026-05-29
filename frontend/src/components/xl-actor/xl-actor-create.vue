<script setup lang="ts">
import { $http } from '@/common/http';
import { ResponseCode } from '@/common/const';
import { ElMessage } from 'element-plus';
import { useRefs, useWebConfigStore } from '@/stores';
import IconModelSvg from '@/svg/icon/icon-model.vue';
import IconActorSvg from '@/svg/icon/icon-actor.vue';
import IconActorThreeViewSvg from '@/svg/icon/icon-actor-three-view.vue';
import IconImageSvg from '@/svg/icon/icon-image.vue';
import IconUploadImageSvg from '@/svg/icon/icon-upload-image.vue';
const webConfigStore = useWebConfigStore();
const { WEBCONFIG } = useRefs(webConfigStore);
const emit = defineEmits(['success']);
const actorDialogVisible = ref(false);
const actorForm = reactive<any>({
    id: '',
    drama_id: '',
    episode_id: '',
    image_state: false,
    image_model_id: '',
    three_view_image_state: false,
    three_view_model_id: '',
    status_enum: { value: 'initializing', label: '待初始化' },
    name: '',
    headimg: '',
    three_view_image: '',
    species_type: '',
    gender: '',
    age: '',
    remarks: '',
    image_reference_state: false,
    reference_headimg: '',
    voice_channel: null,
    voice_id: null,
    voice_name: null,
    voice_model_id: null,
})
const actorFormRef = ref<any>(null);
const actorLoading = ref(false);
const actorFormRules = reactive({
    image_model_id: [{ required: true, message: '请选择图片模型', trigger: 'change' }],
    three_view_model_id: [{ required: true, message: '请选择三维模型', trigger: 'change' }],
    species_type: [{ required: true, message: '请选择物种', trigger: 'change' }],
    gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
    age: [{ required: true, message: '请选择年龄', trigger: 'change' }],
    remarks: [{ required: true, message: '请输入备注', trigger: 'change' }],
})
const showForm=ref(false);
const openActorCreateDialog = (actor?: any, drama_id?: string | number, episode_id?: string | number) => {
    showForm.value = true;
    actorImageModel.value = 'remarks';
    actorDialogVisible.value = true;
    nextTick(() => {
        if (actor) {
            actorForm.id = actor.id;
            actorForm.headimg = actor.headimg;
            actorForm.three_view_image = actor.three_view_image;
            actorForm.name = actor.name;
            actorForm.species_type = actor.species_type;
            actorForm.gender = actor.gender;
            actorForm.age = actor.age;
            actorForm.remarks = actor.remarks;
            actorForm.voice_channel = actor.voice_channel;
            actorForm.voice_id = actor.voice_id;
            actorForm.voice_name = actor.voice_name;
            actorForm.voice_model_id = actor.voice_model_id;
            actorForm.drama_id = drama_id;
            actorForm.episode_id = episode_id;
        } else {
            actorForm.drama_id = drama_id;
            actorForm.episode_id = episode_id;
        }
    })
}
const uploadActor = (actor?: any, drama_id?: string | number, episode_id?: string | number) => {
    showForm.value = false;
    actorImageModel.value = 'upload';
    actorDialogVisible.value = true;
    nextTick(() => {
        if (actor) {
            actorForm.id = actor.id;
            actorForm.headimg = actor.headimg;
            actorForm.three_view_image = actor.three_view_image;
            actorForm.name = actor.name;
            actorForm.species_type = actor.species_type;
            actorForm.gender = actor.gender;
            actorForm.age = actor.age;
            actorForm.remarks = actor.remarks;
            actorForm.voice_channel = actor.voice_channel;
            actorForm.voice_id = actor.voice_id;
            actorForm.voice_name = actor.voice_name;
            actorForm.voice_model_id = actor.voice_model_id;
            actorForm.drama_id = drama_id;
            actorForm.episode_id = episode_id;
        } else {
            actorForm.drama_id = drama_id;
            actorForm.episode_id = episode_id;
        }
    })
}
const cancelActorDialog = () => {
    actorFormRef.value?.resetFields();
    actorDialogVisible.value = false;
    actorForm.id = '';
    actorForm.name = '';
    actorForm.species_type = '';
    actorForm.gender = '';
    actorForm.age = '';
    actorForm.remarks = '';
    actorForm.image_model_state = false;
    actorForm.image_model_id = '';
    actorForm.three_view_model_state = false;
    actorForm.three_view_model_id = '';
    actorForm.status_enum = { value: 'initializing', label: '待初始化' };
    actorForm.headimg = '';
    actorForm.three_view_image = '';
    actorForm.drama_id = '';
    actorForm.episode_id = '';
    actorForm.voice_channel = null;
    actorForm.voice_id = null;
    actorForm.voice_name = null;
    actorForm.voice_model_id = null;
}
const submitActorDialog = (callback?: () => void) => {
    $http.post('/app/shortplay/api/Actor/update', actorForm).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            actorForm.id = res.data.id;
            emit('success');
            if (callback) {
                callback();
            } else {
                cancelActorDialog();
            }
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
            case 'actor/image':
                uploadHeadimgLoading.value = false;
                actorForm.headimg = response.data.url;
                uploadImageRef.value?.clearFiles();
                break;
            case 'actor/three_view':
                uploadThreeViewLoading.value = false;
                actorForm.three_view_image = response.data.url;
                uploadImageRef.value?.clearFiles();
                break;
            case 'actor/reference':
                uploadLoading.value = false;
                actorForm.image_reference_state = true;
                actorForm.reference_headimg = response.data.url;
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
const actorHeadimgButtonRef = ref();
const actorHeadimgPopoverRef = ref();
const actorHeadimgModel = ref<any>({});
const handleActorHeadimgSelect = (item?: any) => {
    if (item) {
        actorForm.image_model_id = item.id;
        actorForm.image_state = true;
        actorHeadimgModel.value = item;
    } else {
        actorForm.image_model_id = '';
        actorForm.image_state = false;
        actorHeadimgModel.value = {};
    }
    actorHeadimgPopoverRef.value?.hide();
}
const actorThreeViewModelButtonRef = ref();
const actorThreeViewModelPopoverRef = ref();
const actorImageThreeViewModel = ref<any>({});
const handleActorThreeViewModelSelect = (item?: any) => {
    if (item) {
        actorForm.three_view_model_id = item.id;
        actorImageThreeViewModel.value = item;
        actorForm.three_view_image_state = true;
    } else {
        actorForm.three_view_model_id = '';
        actorImageThreeViewModel.value = {};
        actorForm.three_view_image_state = false;
    }
    actorThreeViewModelPopoverRef.value?.hide();
}
const generateImageLoading = ref(false);
const handleGenerateImage = () => {
    if (generateImageLoading.value || actorForm.status_enum.value === 'pending') return;
    if (!actorForm.id) {
        return submitActorDialog(handleGenerateImage);
    }
    generateImageLoading.value = true;
    $http.post('/app/shortplay/api/Actor/initializing', actorForm).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            actorForm.status = res.data.status;
            actorForm.status_enum = res.data.status_enum;
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
    if (channel === 'generateactorimage') {
        if (res.id === actorForm.id) {
            actorForm.status_enum = res.status;
            if (res.image) {
                actorForm.headimg = res.image;
            } else {
                generateImageLoading.value = false;
            }
        }
    } else if (channel === 'generateactorthreeviewimage') {
        if (res.id === actorForm.id) {
            actorForm.status_enum = res.status;
            if (res.image) {
                actorForm.three_view_image = res.image;
            } else {
                generateImageLoading.value = false;
            }
        }
    }
}
const actorImageModel = ref('remarks');
const uploadImageModel = ref('headimg');
const voiceDialogRef = ref<any>();
const handleVoiceSuccess = (data: any) => {
    actorForm.voice_channel = data.voice_channel;
    actorForm.voice_id = data.voice_id;
    actorForm.voice_name = data.name;
    actorForm.voice_model_id = data.model_id;
}
defineExpose({
    open: openActorCreateDialog,
    upload: uploadActor,
    close: cancelActorDialog,
    subscribe: subscribe
})
</script>
<template>
    <div>
        <el-dialog v-model="actorDialogVisible" class="generate-scene-dialog" draggable :width="showForm ? 'min(100%,840px)' : 'min(100%,420px)'" append-to-body
            @close="cancelActorDialog">
            <template #header>
                <span class="font-weight-600" v-if="!showForm">上传演员</span>
                <span class="font-weight-600" v-else-if="!actorForm.id">创建演员</span>
                <span class="font-weight-600" v-else>编辑演员</span>
            </template>
            <el-form label-position="top" :model="actorForm" :rules="actorFormRules" ref="actorFormRef"
                class="actor-form" :disabled="actorForm.status_enum.value !== 'initializing'">
                <div class="flex grid-gap-4 flex-y-flex-start">
                    <div class="flex-1 grid-columns-6 grid-gap-4" v-if="showForm">
                        <el-form-item label="演员名称" prop="title" class="grid-column-3">
                            <el-input v-model="actorForm.name" placeholder="请输入演员名称"
                                class="actor-form-input bg-overlay" />
                        </el-form-item>
                        <el-form-item label="演员音色" prop="title" class="grid-column-3">
                            <el-button text bg @click="voiceDialogRef?.open?.({ modelScene:'dialogue_voice',actor: actorForm })">
                                <span v-if="actorForm.voice_name">音色:{{ actorForm.voice_name }}</span>
                                <span v-else>点击选择音色</span>
                            </el-button>
                        </el-form-item>
                        <el-form-item label="物种" prop="title" class="grid-column-2">
                            <el-select v-model="actorForm.species_type" placeholder="请选择物种" :teleported="false"
                                class="actor-form-select">
                                <el-option v-for="item in WEBCONFIG?.enum?.actor_species_type" :key="item.value"
                                    :label="item.label" :value="item.value" />
                            </el-select>
                        </el-form-item>
                        <el-form-item label="性别" prop="title" class="grid-column-2">
                            <el-select v-model="actorForm.gender" placeholder="请选择性别" :teleported="false"
                                class="actor-form-select">
                                <el-option v-for="item in WEBCONFIG?.enum?.actor_gender" :key="item.value"
                                    :label="item.label" :value="item.value" />
                            </el-select>
                        </el-form-item>
                        <el-form-item label="年龄" prop="title" class="grid-column-2">
                            <el-select v-model="actorForm.age" placeholder="请选择年龄" :teleported="false"
                                class="actor-form-select">
                                <el-option v-for="item in WEBCONFIG?.enum?.actor_age" :key="item.value"
                                    :label="item.label" :value="item.value" />
                            </el-select>
                        </el-form-item>
                        <el-form-item label="演员形象" class="grid-column-6">
                            <div class="flex flex-column grid-gap-4 w-100">
                                <el-segmented v-model="actorImageModel" class="tabs-segmented"
                                    :options="[{ label: '文本生成', value: 'remarks' }, { label: '本地上传', value: 'upload' }]" />
                                <div class="bg-overlay rounded-4 p-4 w-100">
                                    <el-input v-model="actorForm.remarks" placeholder="请输入角色描述" size="small"
                                        class="actor-form-textarea" type="textarea"
                                        :autosize="{ minRows: 6, maxRows: 20 }" />
                                    <div class="flex flex-y-center grid-gap-2 line-height-1 mt-4"
                                        v-if="actorImageModel === 'remarks'">
                                        <div class="bg rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover"
                                            ref="actorHeadimgButtonRef" title="选择使用AI生成形象图">
                                            <template v-if="actorHeadimgModel.id">
                                                <el-avatar :src="actorHeadimgModel.icon" :alt="actorHeadimgModel.name"
                                                    shape="square" :size="16"></el-avatar>
                                                <span class="h10 text-ellipsis-1" style="max-width: 60px;">{{
                                                    actorHeadimgModel.name
                                                }}</span>
                                                <el-icon size="16" class="pointer"
                                                    @click.stop="handleActorHeadimgSelect()">
                                                    <Close />
                                                </el-icon>
                                            </template>
                                            <template v-else>
                                                <el-icon size="16">
                                                    <IconModelSvg />
                                                </el-icon>
                                                <span class="h10 overflow-hidden text-nowrap"
                                                    style="max-width: 60px;">形象图</span>
                                                <el-icon size="16">
                                                    <ArrowDown />
                                                </el-icon>
                                            </template>
                                        </div>
                                        <div class="bg rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover"
                                            ref="actorThreeViewModelButtonRef" title="选择使用AI生成三视图">
                                            <template v-if="actorImageThreeViewModel.id">
                                                <el-avatar :src="actorImageThreeViewModel.icon"
                                                    :alt="actorImageThreeViewModel.name" shape="square"
                                                    :size="16"></el-avatar>
                                                <span class="h10 text-ellipsis-1" style="max-width: 60px;">{{
                                                    actorImageThreeViewModel.name }}</span>
                                                <el-icon size="16" class="pointer"
                                                    @click.stop="handleActorThreeViewModelSelect()">
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
                                            :data="{ dir_name: 'actor/reference', dir_title: '演员形象参考照片' }"
                                            :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                                            :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1"
                                            type="cover" :disabled="uploadLoading"
                                            :before-upload="() => { uploadLoading = true; return true; }"
                                            :on-success="handleUploadSuccess" :show-file-list="false"
                                            :on-error="() => { uploadLoading = false; handleUploadError() }">
                                            <div
                                                class="bg rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover">
                                                <el-popover placement="top" :disabled="!actorForm.reference_headimg"
                                                    width="fit-content">
                                                    <el-avatar :src="actorForm.reference_headimg" fit="contain"
                                                        :size="130" shape="square"></el-avatar>
                                                    <template #reference>
                                                        <el-icon size="16"
                                                            v-if="!actorForm.reference_headimg || uploadLoading">
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
                                                <Loading class="circular" v-if="generateImageLoading||actorForm.status_enum.value === 'pending'" />
                                                <Top v-else />
                                            </el-icon>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </el-form-item>
                    </div>
                    <div class="flex flex-column grid-gap-4 p-4 bg-overlay rounded-4"
                        v-if="actorImageModel === 'remarks'">
                        <el-avatar :src="actorForm.headimg" shape="square" :size="360"
                            style="--el-avatar-bg-color:var(--el-bg-color-overlay)">
                            <div class="flex flex-column flex-center grid-gap-2"
                                v-if="actorForm.status_enum.value === 'initializing'">
                                <el-icon size="64">
                                    <Loading class="circular" v-if="generateImageLoading" />
                                    <IconImageSvg v-else />
                                </el-icon>
                                <span class="h10">填写左侧表单，使用AI生成演员形象图</span>
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
                                v-else-if="actorForm.status_enum.value === 'pending'">
                                <el-icon size="64">
                                    <Loading class="circular" />
                                </el-icon>
                                <span class="h10">生成中...</span>
                            </div>
                        </el-avatar>
                    </div>
                    <div class="flex flex-column grid-gap-4 bg-overlay rounded-4 p-4" v-else>
                        <div>
                            <el-upload v-if="uploadImageModel === 'headimg'" ref="uploadImageRef"
                                class="input-upload rounded-4" drag
                                :data="{ dir_name: 'actor/image', dir_title: '演员形象照片' }"
                                :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                                :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1" type="cover"
                                :disabled="uploadHeadimgLoading"
                                :before-upload="() => { uploadHeadimgLoading = true; return true; }"
                                :on-success="handleUploadSuccess" :show-file-list="false"
                                :on-error="() => { uploadHeadimgLoading = false; handleUploadError() }">
                                <template v-if="!actorForm.headimg">
                                    <el-icon class="el-icon--upload">
                                        <IconUploadImageSvg />
                                    </el-icon>
                                    <div class="el-upload__text">
                                        <span class="h10">拖拽演员形象照片到此处或</span>
                                        <span class="h10">点击上传</span>
                                    </div>
                                    <div class="el-upload__text">
                                        <span class="h10">支持上传格式：</span>
                                        <span class="h10">PNG, JPG, JPEG</span>
                                    </div>
                                    <div class="el-upload__text">
                                        <span class="h10">形象照片建议比例：</span>
                                        <span class="h10">1:1</span>
                                    </div>
                                </template>
                                <template v-else>
                                    <el-image :src="actorForm.headimg" class="image-cover" fit="contain"></el-image>
                                </template>
                            </el-upload>
                            <el-upload v-else-if="uploadImageModel === 'three_view'" ref="uploadImageRef"
                                class="input-upload rounded-4" drag
                                :data="{ dir_name: 'actor/three_view', dir_title: '演员三视图' }"
                                :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                                :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1" type="cover"
                                :disabled="uploadThreeViewLoading"
                                :before-upload="() => { uploadThreeViewLoading = true; return true; }"
                                :on-success="handleUploadSuccess" :show-file-list="false"
                                :on-error="() => { uploadThreeViewLoading = false; handleUploadError() }">
                                <template v-if="!actorForm.three_view_image">
                                    <el-icon class="el-icon--upload">
                                        <IconUploadImageSvg />
                                    </el-icon>
                                    <div class="el-upload__text">
                                        <span class="h10">拖拽演员三视图到此处或</span>
                                        <span class="h10">点击上传</span>
                                    </div>
                                    <div class="el-upload__text">
                                        <span class="h10">支持上传格式：</span>
                                        <span class="h10">PNG, JPG, JPEG</span>
                                    </div>
                                    <div class="el-upload__text">
                                        <span class="h10">形象照片建议比例：</span>
                                        <span class="h10">1:1</span>
                                    </div>
                                </template>
                                <template v-else>
                                    <el-image :src="actorForm.three_view_image" class="image-cover"
                                        fit="contain"></el-image>
                                </template>
                            </el-upload>
                        </div>
                        <div class="flex flex-center grid-gap-4">
                            <el-avatar :src="actorForm.headimg" shape="square" :size="60" class="pointer"
                                @click="uploadImageModel = 'headimg'">
                                <div class="flex flex-column flex-center grid-gap-1"
                                    :class="{ 'text-secondary': uploadImageModel === 'three_view' }">
                                    <el-icon size="20">
                                        <Loading class="circular" v-if="uploadHeadimgLoading" />
                                        <IconActorSvg v-else />
                                    </el-icon>
                                    <span class="h10">形象图</span>
                                </div>
                            </el-avatar>
                            <el-avatar :src="actorForm.three_view_image" shape="square" :size="60" class="pointer"
                                @click="uploadImageModel = 'three_view'">
                                <div class="flex flex-column flex-center grid-gap-1"
                                    :class="{ 'text-secondary': uploadImageModel === 'headimg' }">
                                    <el-icon size="20">
                                        <Loading class="circular" v-if="uploadThreeViewLoading" />
                                        <IconActorThreeViewSvg v-else />
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
                    <el-button type="info" @click="cancelActorDialog" :disabled="actorLoading">取消</el-button>
                    <div class="flex-1"></div>
                    <el-button type="success" @click="submitActorDialog()" :disabled="actorLoading"
                        :loading="actorLoading">提交</el-button>
                </div>
            </template>
        </el-dialog>
        <el-popover ref="actorHeadimgPopoverRef" :virtual-ref="actorHeadimgButtonRef" virtual-triggering
            :teleported="false" placement="bottom-start" width="min(100vw,380px)" trigger="click">
            <xl-models @select="handleActorHeadimgSelect" scene="actor_image" no-init />
        </el-popover>
        <el-popover ref="actorThreeViewModelPopoverRef" :virtual-ref="actorThreeViewModelButtonRef" virtual-triggering
            :teleported="false" placement="bottom-start" width="min(100vw,380px)" trigger="click">
            <xl-models @select="handleActorThreeViewModelSelect" scene="actor_three_view_image" no-init />
        </el-popover>
        <xl-voice ref="voiceDialogRef" @success="handleVoiceSuccess" />
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

.input-button {
    background-color: var(--el-fill-color-darker);
    cursor: pointer;

    &:hover {
        background-color: var(--el-fill-color-dark);
    }
}

.icon-model {
    font-size: 20px;
    width: 22px;
    height: 22px;
}

.actor-form {
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
            border-radius:0;
        }
    }
}
</style>