<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { ElMessage } from 'element-plus';
import IconModelSvg from '@/svg/icon/icon-model.vue';
import { uniqid } from '@/common/functions';
const props = withDefaults(defineProps<{
    query?: any
    types?: any[]
}>(), {
    query: () => ({}),
    types: () => ([]),
});
const emit = defineEmits(['success']);
const CharacterLookSearch = reactive({
    type: 'all',
    description: '',
    ...props.query,
})
const characterLookList = ref<any[]>([]);
const characterLookDialogVisible = ref(false);
const loading = ref(false);
const getCharacterLookList = () => {
    loading.value = true;
    characterLookList.value = [];
    $http.get('/app/shortplay/api/CharacterLook/index', { params: CharacterLookSearch }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            characterLookList.value = res.data;
        }
    }).finally(() => {
        loading.value = false;
    })
}
const createForm = reactive({
    ...props.query,
    alias_id: uniqid(),
    title: '',
    overall_style: '',
    makeup: '',
    hair_style: '',
    costume: '',
    costume_url: '',
    status_note: '',
    costume_reference_state: false,
    model_id: ''
})
const characterLookFormRef = ref<any>();
const uploadImageRef = ref<any>(null);
const uploadLoading = ref(false);
const handleUploadSuccess = (response: any) => {
    uploadLoading.value = false;
    if (response.code === ResponseCode.SUCCESS) {
        switch (response.data.dir_name) {
            case 'actor/costume':
                createForm.costume_url = response.data.url;
                if (createForm.model_id) {
                    createForm.costume_reference_state = true;
                }
                uploadImageRef.value?.clearFiles();
                break;
        }
    } else {
        ElMessage.error(response.msg);
    }
}
const handleUploadError = () => {
    uploadLoading.value = false;
    uploadImageRef.value?.clearFiles();
}
const createLoading = ref(false);
const submit = () => {
    if (createLoading.value) return;
    createLoading.value = true;
    $http.post('/app/shortplay/api/CharacterLook/update', createForm).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            characterLookFormRef.value?.resetFields();
            emit('success');
            characterLookDialogVisible.value=false;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('创建失败');
    }).finally(() => {
        createLoading.value = false;
    })
}
const actorCostumeButtonRef = ref();
const actorCostumePopoverRef = ref();
const actorCostumeModel = ref<any>({});
const handleModelSelect = (item: any) => {
    actorCostumeModel.value = item;
    if (createForm.costume_url) {
        createForm.costume_reference_state = true;
    }
    actorCostumePopoverRef.value?.hide();
}
const openCharacterLookDialog = () => {
    getCharacterLookList();
    characterLookDialogVisible.value = true;
}
const handleBeforeClose = (done: any) => {
    if (createLoading.value) return;
    done();
}
defineExpose({
    open: openCharacterLookDialog,
})
</script>
<template>
    <div>
        <el-dialog v-model="characterLookDialogVisible" class="generate-scene-dialog" draggable width="min(100%,800px)"
            :close-on-press-escape="false" :close-on-click-modal="false" :before-close="handleBeforeClose">
            <template #header>
                <span class="font-weight-600">演员装扮</span>
            </template>
            <el-form label-position="right" label-width="80px" :model="createForm" size="large"
                ref="characterLookFormRef">
                <div class="grid-columns-2 grid-gap-x-10 grid-gap-y-4 character-look-form">
                    <el-form-item label="装扮名称" prop="title" class="grid-column-2">
                        <el-input v-model="createForm.title" placeholder="请输入装扮名称" class="form-input" />
                    </el-form-item>
                    <el-form-item label="整体" prop="overall_style" class="grid-column-1">
                        <el-input v-model="createForm.overall_style" placeholder="整体（如：日常、精致、狼狈、正式）"
                            class="form-input" />
                    </el-form-item>
                    <el-form-item label="状态" prop="status_note" class="grid-column-1">
                        <el-input v-model="createForm.status_note" placeholder="状态（凌乱、破损）" class="form-input" />
                    </el-form-item>
                    <el-form-item label="妆容" prop="makeup" class="grid-column-1">
                        <el-input v-model="createForm.makeup" placeholder="妆容（淡妆/浓妆/素颜感等）" class="form-input" />
                    </el-form-item>
                    <el-form-item label="发型" prop="hair_style" class="grid-column-1">
                        <el-input v-model="createForm.hair_style" placeholder="发型描述" class="form-input" />
                    </el-form-item>
                    <div class="grid-column-2 flex flex-column grid-gap-4">
                        <span>服饰描述</span>
                        <div class="flex flex-column bg-overlay rounded-4 p-4">
                            <el-input type="textarea" v-model="createForm.costume" placeholder="服饰描述（颜色+款式+搭配）"
                                class="form-textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
                            <el-upload ref="uploadImageRef" :data="{ dir_name: 'actor/costume', dir_title: '服饰图片' }"
                                :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                                :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1" type="cover"
                                :disabled="uploadLoading" :before-upload="() => { uploadLoading = true; return true; }"
                                :on-success="handleUploadSuccess" :show-file-list="false" :on-error="handleUploadError">
                                <div
                                    class="bg rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover">
                                    <el-popover placement="top" :disabled="!createForm.costume_url" width="fit-content">
                                        <el-avatar :src="createForm.costume_url" fit="contain" :size="130"
                                            shape="square"></el-avatar>
                                        <template #reference>
                                            <el-icon v-if="!createForm.costume_url || uploadLoading" color="#FFFFFF">
                                                <Loading class="circular" v-if="uploadLoading" />
                                                <Plus v-else />
                                            </el-icon>
                                            <el-icon v-else color="var(--el-color-success)">
                                                <PictureRounded />
                                            </el-icon>
                                        </template>
                                    </el-popover>
                                </div>
                            </el-upload>
                        </div>
                    </div>
                </div>
            </el-form>
            <template #footer>
                <el-button @click="characterLookDialogVisible = false;" bg text :disabled="createLoading">取消</el-button>
                <div class="flex-1"></div>
                <div class="flex flex-center grid-gap-2 input-button rounded-4 py-2 px-6" ref="actorCostumeButtonRef">
                    <template v-if="!actorCostumeModel.id">
                        <el-icon alt="角色装扮" class="icon-model" color="var(--el-color-success)">
                            <IconModelSvg />
                        </el-icon>
                        <span class="h10">选择装扮换装模型</span>
                    </template>
                    <template v-else>
                        <el-avatar :src="actorCostumeModel.icon" :alt="actorCostumeModel.name" shape="square"
                            class="icon-model"></el-avatar>
                        <span class="h10">{{ actorCostumeModel.name }}</span>
                        <el-icon
                            @click.stop="actorCostumeModel = {}; createForm.model_id = ''; createForm.costume_reference_state = false;">
                            <Close />
                        </el-icon>
                    </template>
                </div>
                <el-button type="success" @click="submit()" :loading="createLoading">创建</el-button>
            </template>
        </el-dialog>
        <el-popover ref="actorCostumePopoverRef" :virtual-ref="actorCostumeButtonRef" virtual-triggering
            placement="bottom-start" width="min(100vw,380px)" trigger="click">
            <xl-models v-model="createForm.model_id" @select="handleModelSelect" scene="character_look_costume"
                no-init />
        </el-popover>
    </div>
</template>
<style lang="scss" scoped>
.character-look-form {
    .form-input {
        --el-input-bg-color: var(--el-bg-color-overlay);

        :deep(.el-input__wrapper) {
            box-shadow: none;
        }

    }

    .form-textarea {
        :deep(.el-textarea__inner) {
            box-shadow: none;
            padding: 0;
            resize: none;
        }
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
</style>