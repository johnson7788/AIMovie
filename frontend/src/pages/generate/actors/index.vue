<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import IconPrevStepSvg from '@/svg/icon/icon-prev-step.vue';
import IconNextStepSvg from '@/svg/icon/icon-next-step.vue';
import IconBatchSvg from '@/svg/icon/icon-batch.vue';
import IconModelSvg from '@/svg/icon/icon-model.vue';
import IconReplaceSvg from '@/svg/icon/icon-replace.vue';
import { useWebConfigStore, useUserStore, useRefs } from '@/stores';
import { useRoute } from 'vue-router';
import router from '@/routers';
import { Loading, UploadFilled } from '@element-plus/icons-vue';
import { usePush } from '@/composables/usePush';
const route = useRoute();
const userStore = useUserStore();
const { USERINFO } = useRefs(userStore);
const webConfigStore = useWebConfigStore();
const { WEBCONFIG } = useRefs(webConfigStore);
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
const ActorSearch = reactive({
    type: 'episode',
    name: '',
    actor_id: '',
    species_type: null,
    gender: null,
    age: null,
    drama_id: drama_id.value,
    episode_id: episode_id.value
})
const actorList = ref<any[]>([]);
const loading = ref(false);
const actorCreateRef = ref<any>(null);
const currentActor = ref<any>();
const currentActorForm = ref<any>({
    actor_id: '',
    drama_id: drama_id.value,
    episode_id: episode_id.value,
    name: '',
    species_type: null,
    gender: null,
    age: null,
    remarks: '',
    image_model_id: null,
    three_view_model_id: null,
    image_state: false,
    three_view_image_state: false,
    image_reference_state: false,
    reference_headimg: '',
    image: '',
    three_view_image: '',
});
watch(actorList, () => {
    try {
        const find = actorList.value.find((item: any) => item.id === currentActor.value?.id);
        if (find) {
            handleCurrentActor(find)
        } else {
            const defaultActor = actorList.value.find((item: any) => item.is_edit);
            if (defaultActor) {
                handleCurrentActor(defaultActor);
            } else {
                currentActor.value = undefined;
                currentActorForm.value = {
                    id: '',
                    drama_id: drama_id.value,
                    episode_id: episode_id.value,
                    name: '',
                    species_type: null,
                    gender: null,
                    age: null,
                    remarks: '',
                    image_model_id: null,
                    three_view_model_id: null,
                    image_state: false,
                    three_view_image_state: false,
                    image_reference_state: false,
                    reference_headimg: '',
                    image: '',
                    three_view_image: '',
                };
            }
        }
    } catch (error) {
        console.error('watch actorList error', error);
    }
})
const getActorList = () => {
    loading.value = true;
    $http.get('/app/shortplay/api/Actor/index', { params: ActorSearch }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            actorList.value = res.data;
        }
    }).catch((error) => {
        console.error('getActorList error', error);
    }).finally(() => {
        loading.value = false;
    })
}
const previewImageVisible = ref(false);
const imageList = ref<any[]>([]);
/* const handlePreviewImage = (currentItem: any) => {
    if (!currentItem.headimg && !currentItem.three_view_image) return;
    imageList.value = [currentItem.headimg, currentItem.three_view_image];
    if (currentItem.character_look_id) {
        imageList.value = [currentItem.headimg, currentItem.three_view_image, currentItem.origin_headimg, currentItem.origin_three_view_image];
    }
    nextTick(() => {
        previewImageVisible.value = true;
    })
} */
const taskList = ref<any[]>([]);
const taskLoading = ref(false);
const taskSearch = reactive({
    alias_id: '',
    scene: 'actor_image',
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
const handleCurrentActor = (item: any) => {
    if (!item.is_edit) {
        return;
    }
    currentActor.value = item;
    currentActorForm.value.id = item.id;
    currentActorForm.value.name = item.name;
    currentActorForm.value.species_type = item.species_type;
    currentActorForm.value.gender = item.gender;
    currentActorForm.value.age = item.age;
    currentActorForm.value.remarks = item.remarks;
    currentActorForm.value.image = item.headimg;
    currentActorForm.value.three_view_image = item.three_view_image;
    currentActorForm.value.image_reference_state = false;
    currentActorForm.value.reference_headimg = '';
    taskSearch.alias_id = item.id;
    getTaskList();
}
const modelPopoverRef = ref<any>(null);
const modelButtonRef = ref<any>(null);
const model = ref<any>({});
const handleModelSelect = (item?: any) => {
    if (item) {
        model.value = item;
        currentActorForm.value.image_state = true;
    } else {
        model.value = {};
        currentActorForm.value.image_model_id = null;
        currentActorForm.value.image_state = false;
    }
    modelPopoverRef.value?.hide();
}
const threeViewModelPopoverRef = ref<any>(null);
const threeViewModelButtonRef = ref<any>(null);
const threeViewModel = ref<any>({});
const handleThreeViewModelSelect = (item?: any) => {
    if (item) {
        threeViewModel.value = item;
        currentActorForm.value.three_view_image_state = true;
    } else {
        threeViewModel.value = {};
        currentActorForm.value.three_view_model_id = null;
        currentActorForm.value.three_view_image_state = false;
    }
    threeViewModelPopoverRef.value?.hide();
}
const generateImageLoading = ref(false);
const handleGenerateImage = () => {
    if (generateImageLoading.value || currentActor.value.status_enum.value === 'pending') return;
    if(!currentActorForm.value.image_model_id&&!currentActorForm.value.three_view_model_id) {
        ElMessage.error('请先选择形象图模型或三视图模型');
        return;
    }
    generateImageLoading.value = true;
    $http.post('/app/shortplay/api/Actor/initializing', {
        ...currentActorForm.value,
        image: '',
        three_view_image: ''
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            currentActor.value.status = res.data.status;
            currentActor.value.status_enum = res.data.status_enum;
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
        currentActorForm.value.image_reference_state = true;
        currentActorForm.value.reference_headimg = response.data.url;
    } else {
        ElMessage.error(response.msg);
    }
    uploadImageRef.value?.clearFiles();
}
const handleUploadReferenceImageError = () => {
    uploadLoading.value = false;
    uploadImageRef.value?.clearFiles();
}
const replaceActorLoading = ref(false);
const handleReplaceActor = (item: any) => {
    if (replaceActorLoading.value) return;
    replaceActorLoading.value = true;
    $http.post('/app/shortplay/api/Actor/ReplaceActor', {
        id: currentActor.value.id,
        task_id: item.id
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            currentActor.value.headimg = item.result.image_path;
            if (!currentActor.value.character_look_id) {
                currentActor.value.origin_headimg = item.result.image_path;
            }
            currentActor.value.status = res.data.status;
            currentActor.value.status_enum = res.data.status_enum;
            currentActorForm.value.image = item.result.image_path;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('替换演员失败');
    }).finally(() => {
        replaceActorLoading.value = false;
    })
}
const batchGenerateDialogVisible = ref(false);
const batchGenerateLoading = ref(false);
const batchGenerateLength = ref(0);
const batchGenerateList = ref<any[]>([]);
const handleBatchGenerate = () => {
    batchGenerateDialogVisible.value = true;
    batchGenerateList.value = actorList.value.filter((item: any) => item.status === 'initializing')
    batchGenerateLength.value = batchGenerateList.value.length
}
const submitBatchGenerate = () => {
    batchGenerateLoading.value = true;
    Promise.all(batchGenerateList.value.map((item: any) => {
        return $http.post('/app/shortplay/api/Actor/initializing', {
            id: item.id,
            image_reference_state: item.headimg ? true : false,
            reference_headimg: item.headimg ? item.headimg : '',
            image_state: true,
            three_view_image_state: true,
            image_model_id: model.value.id,
            three_view_model_id: threeViewModel.value.id,
        })
    })).then(() => {
        getActorList();
    }).catch((error) => {
        console.error('submitBatchGenerate error', error);
    }).finally(() => {
        batchGenerateLoading.value = false;
        batchGenerateDialogVisible.value = false;
    })
}
const handleDeleteActor = (item: any) => {
    $http.post('/app/shortplay/api/DramaEpisode/deleteActor', {
        id: item.id,
        drama_id: drama_id.value,
        episode_id: episode_id.value,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            getActorList();
        } else {
            ElMessage.error(res.msg);
        }
    })
}
const voiceDialogRef = ref<any>();
const handleVoiceActor = (item: any) => {
    currentActor.value = item;
    voiceDialogRef.value?.open({
        modelScene: 'dialogue_voice',
        voice: item.voice
    });
}
const handleVoiceSuccess = (data: any) => {
    $http.post('/app/shortplay/api/Actor/voice', {
        id: currentActor.value.id,
        drama_id: drama_id.value,
        episode_id: episode_id.value,
        apply_scope: 'episode',
        voice: data
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            getActorList();
        } else {
            ElMessage.error(res.msg);
        }
    }).catch((error) => {
        console.error('handleVoiceSuccess error', error);
        ElMessage.error('设置演员音色失败');
    })
}
const characterLookRef = ref();
const handleCharacterLookActor = (item: any) => {
    currentActor.value = item;
    characterLookRef.value?.open?.({ actor: item });
}
const handleCharacterLookSelect = (item: any) => {
    let url = '/app/shortplay/api/Generate/characterLook';
    if (item.type === 'actor') {
        url = '/app/shortplay/api/DramaEpisode/CharacterLook';
    }
    $http.post(url, {
        drama_id: drama_id.value,
        episode_id: episode_id.value,
        actor_id: currentActor.value.id,
        character_look_id: item.id,
        actor_costume_model_id: item.actor_costume_model_id,
        actor_costume_three_view_model_id: item.actor_costume_three_view_model_id,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            const find = actorList.value.find((n: any) => n.id === res.data.id);
            if (item.type != 'actor' && find) {
                find.character_look_state = 1;
            } else {
                getActorList();
            }
        } else {
            ElMessage.error(res.msg);
        }
    })
}

const { subscribe, unsubscribeAll } = usePush();
const addListener = () => {
    subscribe('private-generateactorimage-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const findItem = actorList.value.find((item: any) => item.id === res.id);
        if (findItem) {
            findItem.status_enum = res.status;
            if (res.image) {
                findItem.headimg = res.image;
            }
        }
        actorCreateRef.value?.subscribe?.('generateactorimage', res);
    });
    subscribe('private-generateactorthreeviewimage-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const findItem = actorList.value.find((item: any) => item.id === res.id);
        if (findItem) {
            findItem.status_enum = res.status;
            if (res.image) {
                findItem.three_view_image = res.image;
            }
        }
        actorCreateRef.value?.subscribe?.('generateactorthreeviewimage', res);
    });
}
const prevStep = () => {
    router.push(`/generate/drama/${route.params.drama_id}/${route.params.episode_id}`);
}
const nextStep = () => {
    router.push(`/generate/props/${route.params.drama_id}/${route.params.episode_id}`);
}
onMounted(() => {
    getActorList();
    getDramaInfo();
    addListener();
})
onUnmounted(() => {
    console.log('actors unmounted');
    unsubscribeAll();
})
</script>
<template>
    <div class="flex flex-column draw-module">
        <div class="flex-1 flex grid-gap-10 overflow-hidden">
            <div class="flex-1 flex flex-column grid-gap-4 overflow-hidden">
                <el-form class="flex flex-center grid-gap-4" @submit.prevent="getActorList">
                    <el-form-item class="mb-0">
                        <el-input v-model="ActorSearch.name" placeholder="搜索演员" clearable @change="getActorList">
                            <template #suffix>
                                <el-icon>
                                    <Search />
                                </el-icon>
                            </template>
                        </el-input>
                    </el-form-item>
                    <div class="flex-1"></div>
                    <el-form-item class="mb-0" style="width: 80px;">
                        <el-select v-model="ActorSearch.species_type" placeholder="物种" clearable :teleported="false"
                            @change="getActorList">
                            <el-option v-for="item in WEBCONFIG?.enum?.actor_species_type" :key="item.value"
                                :label="item.label" :value="item.value" />
                        </el-select>
                    </el-form-item>
                    <el-form-item class="mb-0" style="width: 80px;">
                        <el-select v-model="ActorSearch.gender" placeholder="性别" clearable :teleported="false"
                            @change="getActorList">
                            <el-option v-for="item in WEBCONFIG?.enum?.actor_gender" :key="item.value"
                                :label="item.label" :value="item.value" />
                        </el-select>
                    </el-form-item>
                    <el-form-item class="mb-0" style="width: 80px;">
                        <el-select v-model="ActorSearch.age" placeholder="年龄" clearable :teleported="false"
                            @change="getActorList">
                            <el-option v-for="item in WEBCONFIG?.enum?.actor_age" :key="item.value" :label="item.label"
                                :value="item.value" />
                        </el-select>
                    </el-form-item>
                </el-form>
                <el-scrollbar class="flex-1">
                    <div
                        class="grid-columns-xxl-7 grid-columns-xl-6 grid-columns-lg-5 grid-columns-md-4 grid-columns-sm-3 grid-columns-xs-2 grid-columns-p-1 grid-gap-4">
                        <div class="grid-column-1 rounded-4 p-4 actor-item flex flex-column flex-center grid-gap-4 pointer bg-overlay"
                            @click="actorCreateRef?.open?.(null, ActorSearch.drama_id, ActorSearch.episode_id)">
                            <el-icon class="rounded-4" size="20"
                                style="height: 40px; width: 40px;background-color: var(--el-fill-color-dark);">
                                <Plus />
                            </el-icon>
                            <span>添加演员</span>
                        </div>
                        <div class="grid-column-1 rounded-4 flex flex-column flex-center grid-gap-2 actor-item bg-overlay border"
                            :class="{ 'border-success': item.id === currentActorForm.id }" v-for="item in actorList"
                            :key="item.id">
                            <el-avatar :src="item.headimg" class="actor-avatar bg-mosaic" fit="cover" :title="item.is_edit?item.name:'公共角色不可编辑'">
                                {{ item.name }}
                            </el-avatar>
                            <div class="actor-edit-mask flex flex-column grid-gap-4 flex-center pointer"
                                v-if="item.is_edit" @click="handleCurrentActor(item)">
                                <div class="flex flex-center bg-overlay rounded-round p-2 pointer grid-gap-2"
                                    @click.stop="actorCreateRef?.upload?.(item, ActorSearch.drama_id, ActorSearch.episode_id)">
                                    <el-icon size="16">
                                        <UploadFilled />
                                    </el-icon>
                                    <span class="h10">手动上传</span>
                                </div>
                                <el-popconfirm title="确定删除该演员吗？" width="fit-content" @confirm="handleDeleteActor(item)"
                                    placement="bottom-end">
                                    <template #reference>
                                        <div class="flex flex-center bg-overlay rounded-round p-2 pointer grid-gap-2"
                                            @click.stop>
                                            <el-icon size="16">
                                                <Delete />
                                            </el-icon>
                                            <span class="h10">删除演员</span>
                                        </div>
                                    </template>
                                </el-popconfirm>
                            </div>
                            <div class="flex grid-gap-2 actor-status">
                                <!-- <span class="actor-tag pointer" title="复制演员"
                                    @click.stop="setClipboard(`@${item.name}(${item.actor_id}) `)">{{
                                        item.actor_id
                                    }}</span> -->
                                <div class="flex-1"></div>
                                <div class="flex flex-column flex-y-flex-end grid-gap-2">
                                    <span class="actor-tag" :class="[`actor-tag--` + item.status_enum.props.type]">
                                        {{ item.status_enum.label }}
                                    </span>
                                </div>
                            </div>
                            <div class="flex flex-column grid-gap-2 actor-info">
                                <div class="actor-name flex flex-center grid-gap-1"
                                    :class="{ 'pointer': item.is_edit, 'actor-name--success': item.id === currentActorForm.id }"
                                    @click.stop="actorCreateRef?.open?.(item, ActorSearch.drama_id, ActorSearch.episode_id)">
                                    <el-icon size="16">
                                        <UserFilled />
                                    </el-icon>
                                    <span>{{ item.name }}</span>
                                </div>
                                <!-- <div class="flex grid-gap-2">
                                    <span class="actor-tag">{{ item.species_type_enum?.label
                                        }}</span>
                                    <span class="actor-tag">{{ item.gender_enum?.label }}</span>
                                    <span class="actor-tag">{{ item.age_enum?.label }}</span>
                                </div> -->
                            </div>
                            <div class="actor-action flex flex-center px-4">
                                <el-button text bg @click="handleVoiceActor(item)" class="flex-1 text-ellipsis-1">
                                    <span v-if="item.voice">音色:{{ item.voice.name }}</span>
                                    <span v-else>演员音色</span>
                                </el-button>
                                <el-button text bg @click="handleCharacterLookActor(item)"
                                    class="flex-1 text-ellipsis-1" :disabled="!!item.character_look_state">
                                    <span v-if="item.character_look_state">换装中</span>
                                    <span v-else-if="item.characterLook">{{ item.characterLook.title }}</span>
                                    <span v-else>演员装扮</span>
                                </el-button>
                            </div>
                        </div>
                    </div>
                </el-scrollbar>
            </div>
            <div class="actor-form-wrapper bg-overlay border rounded-4 actor-form flex flex-column grid-gap-4">
                <template v-if="currentActorForm.id">
                    <div class="border-bottom flex flex-center">
                        <el-input v-model="currentActorForm.name" placeholder="角色演员" size="large"
                            class="actor-form-input flex-1">
                        </el-input>
                    </div>
                    <div class="flex flex-column grid-gap-2 px-4">
                        <span>基础信息</span>
                        <div class="flex grid-gap-2">
                            <el-select v-model="currentActorForm.species_type" placeholder="请选择物种" size="small"
                                class="flex-1 actor-form-select">
                                <el-option v-for="item in WEBCONFIG?.enum?.actor_species_type" :key="item.value"
                                    :label="item.label" :value="item.value" />
                            </el-select>
                            <el-select v-model="currentActorForm.gender" placeholder="请选择性别" size="small"
                                class="flex-1 actor-form-select">
                                <el-option v-for="item in WEBCONFIG?.enum?.actor_gender" :key="item.value"
                                    :label="item.label" :value="item.value" />
                            </el-select>
                            <el-select v-model="currentActorForm.age" placeholder="请选择年龄" size="small"
                                class="flex-1 actor-form-select">
                                <el-option v-for="item in WEBCONFIG?.enum?.actor_age" :key="item.value"
                                    :label="item.label" :value="item.value" />
                            </el-select>
                        </div>
                    </div>
                    <div class="flex flex-column grid-gap-2 px-4">
                        <span>角色描述</span>
                        <div class="bg rounded-4 p-4 border">
                            <el-input v-model="currentActorForm.remarks" placeholder="请输入角色描述" size="small"
                                class="actor-form-textarea" type="textarea" :autosize="{ minRows: 6, maxRows: 20 }" />
                            <div class="flex flex-y-center grid-gap-2">
                                <div class="bg-overlay rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover"
                                    ref="modelButtonRef" title="选择使用AI生成形象图">
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
                                        <span class="h10">形象图</span>
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
                                    :data="{ dir_name: 'actor/reference', dir_title: '演员形象参考照片' }"
                                    :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                                    :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1" type="cover"
                                    :disabled="uploadLoading"
                                    :before-upload="() => { uploadLoading = true; return true; }"
                                    :on-success="handleUploadReferenceImageSuccess" :show-file-list="false"
                                    :on-error="handleUploadReferenceImageError">
                                    <div
                                        class="bg-overlay rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover">
                                        <el-popover placement="top" :disabled="!currentActorForm.reference_headimg"
                                            width="fit-content">
                                            <el-avatar :src="currentActorForm.reference_headimg" fit="contain"
                                                :size="130" shape="square"></el-avatar>
                                            <template #reference>
                                                <el-icon size="16"
                                                    v-if="!currentActorForm.reference_headimg || uploadLoading">
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
                                            v-if="generateImageLoading || currentActor.status_enum.value === 'pending'" />
                                        <Top v-else />
                                    </el-icon>
                                </div>
                            </div>
                        </div>
                    </div>
                    <el-popover ref="modelPopoverRef" popper-class="model-popover" :virtual-ref="modelButtonRef"
                        virtual-triggering placement="bottom" width="min(100vw,380px)" trigger="click">
                        <xl-models v-model="currentActorForm.image_model_id" @select="handleModelSelect" no-init
                            scene="actor_image" />
                    </el-popover>
                    <el-popover ref="threeViewModelPopoverRef" popper-class="model-popover"
                        :virtual-ref="threeViewModelButtonRef" virtual-triggering placement="bottom"
                        width="min(100vw,380px)" trigger="click">
                        <xl-models v-model="currentActorForm.three_view_model_id" @select="handleThreeViewModelSelect"
                            no-init scene="actor_three_view_image" />
                    </el-popover>
                    <div class="flex flex-column grid-gap-2 px-4 pt-4">
                        <span>角色原始形象记录</span>
                    </div>
                    <el-scrollbar class="flex-1">
                        <div class="grid-columns-2 grid-gap-4 p-4" v-if="taskList.length > 0">
                            <div class="grid-column-1 task-item" v-for="item in taskList" :key="item.id">
                                <el-avatar :src="item.result.image_path" fit="contain" shape="square" :size="206">
                                </el-avatar>
                                <div class="flex flex-center grid-gap-2 task-item-replace pointer"
                                    v-if="item.status==='success'&&item.result.image_path !== currentActor.headimg && item.result.image_path !== currentActor.origin_headimg"
                                    @click="handleReplaceActor(item)">
                                    <el-icon>
                                        <Loading class="circular" v-if="replaceActorLoading" />
                                        <IconReplaceSvg v-else />
                                    </el-icon>
                                    <span class="h10 text-nowrap">替换原始形象</span>
                                </div>
                            </div>
                        </div>
                        <el-empty v-else description="暂无原始形象记录" />
                    </el-scrollbar>
                </template>
                <el-empty v-else description="点击角色名称选择角色" />
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
                :disabled="actorList.filter((item: any) => item.status === 'initializing').length <= 0"
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
        <el-image-viewer :url-list="imageList" v-if="previewImageVisible" @close="previewImageVisible = false" />
        <xl-actor-create ref="actorCreateRef" @success="getActorList" />
        <el-dialog v-model="batchGenerateDialogVisible" class="generate-storyboard-dialog" draggable width="800px">
            <template #header>
                <span class="font-weight-600">批量生成演员</span>
            </template>
            <div class="flex grid-gap-10">
                <xl-models title="形象模型" v-model="currentActorForm.image_model_id" @select="handleModelSelect" no-init
                    class="flex-1 bg-overlay rounded-4 p-4" scene="actor_image" />
                <xl-models title="三视图模型" v-model="currentActorForm.three_view_model_id"
                    @select="handleThreeViewModelSelect" class="flex-1 bg-overlay rounded-4 p-4" no-init
                    scene="actor_three_view_image" />
            </div>
            <template #footer>
                <el-button type="info" @click="batchGenerateDialogVisible = false"
                    :disabled="batchGenerateLoading">取消</el-button>
                <div class="flex-1"></div>
                <el-button type="success" icon="Check" @click="submitBatchGenerate"
                    :disabled="!currentActorForm.image_model_id || !currentActorForm.three_view_model_id"
                    :loading="batchGenerateLoading">生成</el-button>
            </template>
        </el-dialog>
        <xl-voice ref="voiceDialogRef" @success="handleVoiceSuccess" />
        <xl-character-look ref="characterLookRef" @select="handleCharacterLookSelect"
            :query="{ drama_id: drama_id, episode_id: episode_id }" />
    </div>
</template>
<style lang="scss" scoped>
.draw-module {
    height: calc(100vh - var(--xl-header-height));
    margin: 0 auto;
    padding: 20px;
    overflow: hidden;

    .actor-form-wrapper {
        width: 450px;
        height: 100%;
        overflow: hidden;
    }

    .actor-item {
        height: 310px;
        position: relative;
        overflow: hidden;
        box-shadow: inset 0 0 0px 2px transparent;

        &:hover {
            background-color: var(--el-fill-color-dark);

            .actor-delete {
                opacity: 1;
            }
        }

        &.active {
            box-shadow: inset 0 0 0px 2px var(--el-color-success);
        }

        .actor-avatar {
            height: 260px;
            width: 100%;
            border-radius: 0px;
        }

        .bg-overlay {
            background-color: rgba(0, 0, 0, 0.5);
        }

        .actor-edit-mask {
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

        .actor-status {
            position: absolute;
            top: 0;
            right: 0;
            width: 100%;
            padding: 10px;
            justify-content: flex-start;
            align-items: flex-start;
            z-index: 1;
        }

        .actor-info {
            position: absolute;
            bottom: 50px;
            left: 0;
            width: 100%;
            padding: 10px;
            justify-content: flex-start;
            align-items: flex-start;
            z-index: 1;
        }


        .actor-tag,
        .actor-name {
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

        .actor-delete {
            width: 28px;
            height: 28px;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }


        .actor-name {
            padding: 4px 8px;
            border-radius: 20px;
        }

        .actor-action {
            height: 50px;
            width: 100%;
        }
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