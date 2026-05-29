<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import IconModelSvg from '@/svg/icon/icon-model.vue';
import IconReplaceSvg from '@/svg/icon/icon-replace.vue';
import IconTransitionSvg from '@/svg/icon/icon-transition.vue';
import IconStoryboardSvg from '@/svg/icon/icon-storyboard.vue';
import IconDubbingSvg from '@/svg/icon/icon-dubbing.vue';
import IconVideoSvg from '@/svg/icon/icon-video.vue';
import IconImageSvg from '@/svg/icon/icon-image.vue';
import IconClothesSvg from '@/svg/icon/icon-clothes.vue';
import IconSelectSvg from '@/svg/icon/icon-select.vue';
import { useUserStore, useRefs, useModelStore } from '@/stores';
import { useRoute } from 'vue-router';
import { Loading } from '@element-plus/icons-vue';
import { formatDuration, truncate } from '@/common/functions';
import { useAVCanvas } from '@/composables/useAVCanvas';
import { usePush } from '@/composables/usePush';
import { ElLoadingService, ElMessageBox, ElMessageBoxOptions, TabPaneName } from 'element-plus';
import { COMPSITE_EVENTS, useCompsite } from '@/composables/useCompsite';
import { useLoading } from '@/composables/useLoading';
const route = useRoute();
const userStore = useUserStore();
const { USERINFO } = useRefs(userStore);
const modelStore = useModelStore();
const drama_id = ref<string | number>(route.params.drama_id as string | number)
const episode_id = ref<string | number>(route.params.episode_id as string | number)
const emit = defineEmits(['update:drama']);
const dramaInfo = ref<any>({});
const getDramaInfo = () => {
    if (!drama_id.value) return;
    $http.get('/app/shortplay/api/Works/details', { params: { id: drama_id.value } }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            dramaInfo.value = res.data;
            narrationModel.value = modelStore.get('storyboard_narration_voice', dramaInfo.value.voice?.model_id);
            emit('update:drama', dramaInfo.value);
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('获取短剧详情失败');
    })
}
const StoryboardSearch = reactive({
    type: 'episode',
    name: '',
    drama_id: drama_id.value,
    episode_id: episode_id.value
})
const sceneList = ref<any[]>([]);
const getSceneList = () => {
    $http.get('/app/shortplay/api/Scene/index', { params: { drama_id: drama_id.value, episode_id: episode_id.value } }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            sceneList.value = res.data;
        }
    })
}
const actorsList = ref<any[]>([]);
const getActorsList = () => {
    if (!currentStoryboard.value?.id) return;
    $http.get('/app/shortplay/api/Actor/index', { params: { type: 'storyboard', drama_id: drama_id.value, episode_id: episode_id.value, storyboard_id: currentStoryboard.value?.id } }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            actorsList.value = res.data;
        }
    })
}
const storyboardList = ref<any[]>([]);
const loading = ref(false);
const currentStoryboard = ref<any>();
watch(currentStoryboard, (newVal) => {
    currentTask.value = undefined;
    if (newVal) {
        getActorsList();
    }
})
const currentStoryboardForm = ref<any>({
    drama_id: drama_id.value,
    episode_id: episode_id.value,
    storyboard_id: '',
    title: '',
    description: '',
    image_prompt: '',
    video_prompt: '',
    video_negative_prompt: '',
    duration: 5000,
    first_image: '',
    last_image: '',
    storyboard_location: '',
    storyboard_space: '',
    storyboard_time: '',
    storyboard_weather: '',
    model_id: null,
    video_model_id: null,
    storyboards: []
});

const storyboardButtonRef = ref();
const storyboardPopoverRef = ref();
const storyboardRef = ref<any>();
const quoteStoryboards = ref<any[]>([]);
const handleQuoteStoryboardSelect = (item: any) => {
    storyboardPopoverRef.value?.hide();
    quoteStoryboards.value.push({
        id: item.id,
        image: item.image,
    });
    currentStoryboardForm.value.storyboards.push(item.id);
}
const handleDeleteQuoteStoryboard = (index: number) => {
    quoteStoryboards.value.splice(index, 1);
    currentStoryboardForm.value.storyboards.splice(index, 1);
}
watch(storyboardList, () => {
    try {
        const find = storyboardList.value.find((item: any) => item.id === currentStoryboard.value?.id);
        if (find) {
            handleCurrentStoryboard(find)
        } else {
            currentStoryboard.value = undefined;
            currentStoryboardForm.value = {
                drama_id: drama_id.value,
                episode_id: episode_id.value,
                storyboard_id: '',
                title: '',
                description: '',
                image_prompt: '',
                video_prompt: '',
                video_negative_prompt: '',
                duration: 5000,
                first_image: '',
                last_image: '',
                storyboard_location: '',
                storyboard_space: '',
                storyboard_time: '',
                storyboard_weather: '',
                model_id: null,
            };
        }
        AVCanvas.parseTrackResource(storyboardList.value, currentStoryboard.value);
    } catch (error) {
        console.error('watch storyboardList error', error);
    }
})
const getStoryboardList = () => {
    loading.value = true;
    $http.get('/app/shortplay/api/Storyboard/index', { params: StoryboardSearch }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            storyboardList.value = res.data;
            const find = storyboardList.value.find((item: any) => item.id === currentStoryboard.value?.id);
            if (!find && storyboardList.value.length > 0) {
                handleCurrentStoryboard(storyboardList.value[0]);
            }
            getSceneList();
        }
    }).catch((error) => {
        console.error('getStoryboardList error', error);
    }).finally(() => {
        loading.value = false;
    })
}
const taskList = ref<any[]>([]);
const taskLoading = ref(false);
const taskSearch = reactive({
    alias_id: '',
    scenes: ['storyboard_image', 'storyboard_video'],
    page: 1,
    page_size: 100,
});
const currentTask = ref<any>();
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
const handleCurrentStoryboard = (item: any) => {
    currentStoryboard.value = item;
    currentStoryboardForm.value.storyboard_id = item.id;
    currentStoryboardForm.value.title = item.title;
    currentStoryboardForm.value.description = item.description;
    currentStoryboardForm.value.image_prompt = item.image_prompt;
    currentStoryboardForm.value.video_prompt = item.video_prompt;
    currentStoryboardForm.value.first_image = item.image;
    currentStoryboardForm.value.storyboard_location = item.storyboard_location;
    currentStoryboardForm.value.storyboard_space = item.storyboard_space;
    currentStoryboardForm.value.storyboard_time = item.storyboard_time;
    currentStoryboardForm.value.storyboard_weather = item.storyboard_weather;
    currentStoryboardForm.value.model_id = item.model_id;
    currentStoryboardForm.value.duration = item.duration;
    currentStoryboardForm.value.narration = item.narration;
    taskSearch.alias_id = item.id;
    getTaskList();
    dialogues.value = [];
    if (activeName.value === 'dialogue') {
        getDialogues();
    }
    AVCanvas.stop();
    AVCanvas.switchClip(item);
}
const modelPopoverRef = ref<any>(null);
const modelButtonRef = ref<any>(null);
const model = ref<any>({});
const handleModelSelect = (item?: any) => {
    if (item) {
        model.value = item;
    } else {
        model.value = {};
        currentStoryboardForm.value.model_id = null;
    }
    modelPopoverRef.value?.hide();
}
const videoModelPopoverRef = ref<any>(null);
const videoModelButtonRef = ref<any>(null);
const videoModel = ref<any>({});
const handleVideoModelSelect = (item?: any) => {
    if (item) {
        videoModel.value = item;
    } else {
        videoModel.value = {};
        currentStoryboardForm.value.video_model_id = null;
    }
    videoModelPopoverRef.value?.hide();
}
const generateImageLoading = ref(false);
const handleGenerateImage = () => {
    if (generateImageLoading.value || currentStoryboard.value.image_state) return;
    generateImageLoading.value = true;
    $http.post('/app/shortplay/api/Generate/storyboardImage', { ...currentStoryboardForm.value, prompt: currentStoryboardForm.value.image_prompt, model_id: model.value.id }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            currentStoryboard.value.image_state = 1;
            getTaskList();
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('生成图片失败');
    }).finally(() => {
        generateImageLoading.value = false;
    })
}

const generateVideoLoading = ref(false);
const handleGenerateVideo = () => {
    if (generateVideoLoading.value || currentStoryboard.value.video_state) return;
    generateVideoLoading.value = true;
    $http.post('/app/shortplay/api/Generate/storyboardVideo', {
        ...currentStoryboardForm.value,
        prompt: currentStoryboardForm.value.video_prompt,
        negative_prompt: currentStoryboardForm.value.video_negative_prompt,
        first_image: currentStoryboardForm.value.first_image,
        last_image: currentStoryboardForm.value.last_image,
        duration: currentStoryboardForm.value.duration,
        model_id: videoModel.value.id,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            currentStoryboard.value.video_state = 1;
            getTaskList();
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('生成视频失败');
    }).finally(() => {
        generateVideoLoading.value = false;
    });
}
const replaceStoryboardLoading = ref(false);
const handleReplaceStoryboard = (item: any) => {
    if (replaceStoryboardLoading.value) return;
    replaceStoryboardLoading.value = true;
    $http.post('/app/shortplay/api/Storyboard/ReplaceStoryboard', {
        id: currentStoryboard.value.id,
        drama_id: StoryboardSearch.drama_id,
        episode_id: StoryboardSearch.episode_id,
        task_id: item.id
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            getStoryboardList();
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('替换分镜失败');
    }).finally(() => {
        replaceStoryboardLoading.value = false;
    })
}
const batchGenerateDialogVisible = ref(false);
const batchGenerateLoading = ref(false);
const batchGenerateLength = ref(0);
const batchGenerateList = ref<any[]>([]);
const BatchGenerateImage = () => {
    batchGenerateDialogVisible.value = true;
    batchGenerateList.value = storyboardList.value.filter((item: any) => !item.image)
    batchGenerateLength.value = batchGenerateList.value.length
}
const submitBatchGenerateImage = () => {
    batchGenerateLoading.value = true;
    Promise.all(batchGenerateList.value.map((item: any) => {
        return $http.post('/app/shortplay/api/Generate/storyboardImage', {
            storyboard_id: item.id,
            drama_id: drama_id.value,
            model_id: model.value.id,
            prompt: item.image_prompt,
        })
    })).then(() => {
        getStoryboardList();
    }).catch((error) => {
        console.error('submitBatchGenerateImage error', error);
    }).finally(() => {
        batchGenerateLoading.value = false;
        batchGenerateDialogVisible.value = false;
    })
}
const batchGenerateVideoDialogVisible = ref(false);
const batchGenerateVideoLoading = ref(false);
const batchGenerateVideoLength = ref(0);
const batchGenerateVideoList = ref<any[]>([]);
const BatchGenerateVideo = () => {
    batchGenerateVideoDialogVisible.value = true;
    batchGenerateVideoList.value = storyboardList.value.filter((item: any) => !item.video)
    batchGenerateVideoLength.value = batchGenerateVideoList.value.length
}
const submitBatchGenerateVideo = () => {
    batchGenerateVideoLoading.value = true;
    Promise.all(batchGenerateList.value.map((item: any) => {
        return $http.post('/app/shortplay/api/Generate/storyboardVideo', {
            storyboard_id: item.id,
            drama_id: drama_id.value,
            model_id: videoModel.value.id,
            prompt: item.video_prompt,
            first_image: item.image
        })
    })).then(() => {
        getStoryboardList();
    }).catch((error) => {
        console.error('submitBatchGenerateVideo error', error);
    }).finally(() => {
        batchGenerateVideoLoading.value = false;
        batchGenerateVideoDialogVisible.value = false;
    })
}
const { subscribe, unsubscribeAll } = usePush();
const addListener = () => {
    subscribe('private-generatestoryboardimage-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const findItem = storyboardList.value.find((item: any) => item.id === res.id);
        if (findItem) {
            findItem.image_state = 0;
            if (res.image) {
                findItem.image = res.image;
                findItem.use_material_type = 'image';
            }else{
                ElMessage.error('生成图片失败');
            }
            if (findItem.id === currentStoryboard.value.id) {
                handleCurrentStoryboard(findItem);
            }
        }
    })
    subscribe('private-generatestoryboard-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const find = storyboardList.value.find((item: any) => item.id === res.id);
        switch (res.event) {
            case 'storyboard_image':
                if (find) {
                    find.image_state = 0;
                    if (res.image) {
                        find.image = res.image;
                        find.use_material_type = 'image';
                    }else{
                        ElMessage.error('生成图片失败');
                    }
                    if (find.id === currentStoryboard.value.id) {
                        handleCurrentStoryboard(find);
                    }
                }
                break;
            case 'storyboard_video':
                if (find) {
                    find.video_state = 0;
                    if (res.video) {
                        find.video = res.video;
                        find.use_material_type = 'video';
                    }else{
                        ElMessage.error('生成视频失败');
                    }
                    if (find.id === currentStoryboard.value.id) {
                        handleCurrentStoryboard(find);
                    }
                }
                break;
            case 'storyboard_narration_voice':
                if (find) {
                    find.narration_state = 0;
                    if (res.audio) {
                        find.narration_audio = res.audio;
                    }else{
                        ElMessage.error('生成旁白音频失败');
                    }
                }
                break;
            case 'actor_costume':
                if (find) {
                    const actor = actorsList.value.find((item: any) => item.id === res.actor_id);
                    if (actor) {
                        if (res.image) {
                            actor.headimg = res.image;
                        } else {
                            actor.character_look_id = null;
                            actor.character_look_state = 0;
                            ElMessage.error('生成演员形象失败');
                        }
                    }
                }
                break;
            case 'actor_costume_three_view':
                if (find) {
                    const actor = actorsList.value.find((item: any) => item.id === res.actor_id);
                    if (actor) {
                        if (res.image) {
                            actor.three_view_image = res.image;
                        } else {
                            actor.character_look_id = null;
                            ElMessage.error('生成演员形象失败');
                        }
                        actor.character_look_state = 0;
                    }
                }
                break;
            case 'dialogue_voice':
                if (find) {
                    const dialogue = dialogues.value.find((item: any) => item.id === res.dialogue_id);
                    if (dialogue) {
                        if (res.audio) {
                            dialogue.audio = res.audio;
                        }else{
                            ElMessage.error('生成对话音频失败');
                        }
                        dialogue.voice_state = 0;
                    }
                }
                break;
        }
    });
    subscribe('private-generateactorimage-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const findItem = actorsList.value.find((item: any) => item.id === res.id);
        if (findItem) {
            findItem.actor.status_enum = res.status;
            if (res.image) {
                findItem.headimg = res.image;
            }else{
                ElMessage.error('生成演员形象失败');
            }
        }
    })
    subscribe('private-generateactorthreeviewimage-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const findItem = actorsList.value.find((item: any) => item.id === res.id);
        if (findItem) {
            findItem.status_enum = res.status;
            if (res.image) {
                findItem.three_view_image = res.image;
            }else{
                ElMessage.error('生成演员形象失败');
            }
        }
    })
    subscribe('private-generatepropimage-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const findItem = currentStoryboard.value.props.find((item: any) => item.prop_id === res.id);
        if (findItem) {
            findItem.prop.status_enum = res.status;
            if (res.image) {
                findItem.prop.image = res.image;
            }else{
                ElMessage.error('生成物品失败');
            }
        }
    })
    subscribe('private-generatepropthreeviewimage-' + USERINFO.value?.user, (res: any) => {
        console.log('channels complete info message', res);
        const findItem = currentStoryboard.value.props.find((item: any) => item.prop_id === res.id);
        if (findItem) {
            findItem.prop.status_enum = res.status;
            if (res.image) {
                findItem.prop.three_view_image = res.image;
            }else{
                ElMessage.error('生成物品失败');
            }
        }
    })
}

const handleInsertEmptyStoryboard = (item?: any) => {
    $http.post('/app/shortplay/api/Storyboard/insertAfter', {
        drama_id: item.drama_id,
        episode_id: item.episode_id,
        after_id: item?.id
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            if (item) {
                // 插入本地
                const index = storyboardList.value.findIndex(item => item.id === item.id)
                storyboardList.value.splice(index + 1, 0, res.data)
            } else {
                storyboardList.value.push(res.data)
            }
            storyboardList.value.sort((a, b) => a.sort - b.sort).forEach((item) => {
                if (item.sort >= res.data.sort && item.id !== res.data.id) {
                    item.sort++;
                }
            })
            handleCurrentStoryboard(res.data);
        } else {
            ElMessage.error(res.msg)
        }
    }).catch(() => {
        ElMessage.error('插入失败')
    })
}
const handleDeleteStoryboard = (item: any) => {
    // 🔥 3. 调用服务端删除接口
    $http.post('/app/shortplay/api/Storyboard/deleteStoryboard', {
        id: item.id,
        drama_id: item.drama_id,
        episode_id: item.episode_id,
    })
        .then((res: any) => {
            if (res.code === ResponseCode.SUCCESS) {
                ElMessage.success('删除成功');
                getStoryboardList();
            } else {
                ElMessage.error(res.msg);
            }
        })
        .catch(() => {
            ElMessage.error('删除失败');
        })
};
const handleChangeStoryboard = (row: any, newSort?: number) => {
    if (newSort === undefined || newSort < 1 || newSort > storyboardList.value.length) return;
    // 拿到全部数据
    const list = storyboardList.value;
    const originalList = JSON.parse(JSON.stringify(storyboardList.value));

    // 只拿当前分镜的
    const currentStoryboardList = list
        .sort((a, b) => a.sort - b.sort);

    // 找到当前操作的 item 在 currentStoryboardList 里的 index
    const oldIndex = currentStoryboardList.findIndex(i => i.id === row.id);
    if (oldIndex === -1) return;

    // 目标 index
    const newIndex = currentStoryboardList.findIndex(i => i.sort === newSort);
    if (newIndex === -1) return;

    // 移动元素
    const current = currentStoryboardList.splice(oldIndex, 1)[0];
    currentStoryboardList.splice(newIndex, 0, current);

    // 重新编号 sort（只改当前分镜的 sort）
    currentStoryboardList.forEach((item, index) => {
        item.sort = index + 1;
    });
    // 替换回 storyboardList
    storyboardList.value = list.map(item => {
        const found = currentStoryboardList.find(i => i.id === item.id);
        return found ?? item; // 当前分镜更新，其他分镜保持不动
    });
    $http.post('/app/shortplay/api/Storyboard/updateSort', {
        drama_id: row.drama_id,
        episode_id: row.episode_id,
        storyboards: currentStoryboardList.map((item: any) => {
            return {
                id: item.id,
                sort: item.sort,
            }
        }),
    })
        .then((res: any) => {
            if (res.code !== ResponseCode.SUCCESS) {
                ElMessage.error(res.msg);
                storyboardList.value = originalList;
            }
        }).catch(() => {
            ElMessage.error('更新分镜失败');
            storyboardList.value = originalList;
        });
};
const handleCopyStoryboard = (row: any) => {
    // 请求服务端：新增分镜
    $http.post('/app/shortplay/api/Storyboard/copyStoryboard', {
        drama_id: row.drama_id,
        episode_id: row.episode_id,
        copy_id: row.id,
        new_sort: row.sort + 1
    })
        .then((res: any) => {
            if (res.code === ResponseCode.SUCCESS) {
                // 服务端会返回新生成的 id
                getStoryboardList();
                ElMessage.success('复制成功');
            } else {
                ElMessage.error(res.msg);
            }
        })
        .catch(() => {
            ElMessage.error('复制失败');
        })
};
const currentStoryboardUploadImageRef = ref<any>(null);
const currentStoryboardUploadLoading = ref(false);
const handleUploadSuccess = (response: any) => {
    currentStoryboardUploadLoading.value = false;
    if (response.code === ResponseCode.SUCCESS) {
        switch (response.data.dir_name) {
            case 'storyboard/image':
                currentStoryboard.value.image = response.data.url;
                $http.post('/app/shortplay/api/Storyboard/update', {
                    id: currentStoryboard.value.id,
                    drama_id: StoryboardSearch.drama_id,
                    episode_id: StoryboardSearch.episode_id,
                    image: response.data.url,
                }).then((res: any) => {
                    if (res.code === ResponseCode.SUCCESS) {
                        getStoryboardList();
                        ElMessage.success('保存成功');
                    } else {
                        ElMessage.error(res.msg);
                    }
                })
                break;
            case 'storyboard/video':
                currentStoryboard.value.video = response.data.url;
                $http.post('/app/shortplay/api/Storyboard/update', {
                    id: currentStoryboard.value.id,
                    drama_id: StoryboardSearch.drama_id,
                    episode_id: StoryboardSearch.episode_id,
                    video: response.data.url,
                }).then((res: any) => {
                    if (res.code === ResponseCode.SUCCESS) {
                        getStoryboardList();
                        ElMessage.success('保存成功');
                    } else {
                        ElMessage.error(res.msg);
                    }
                })
                break;
        }
    } else {
        ElMessage.error(response.msg);
    }
    currentStoryboardUploadImageRef.value?.clearFiles();
}
const handleUploadError = () => {
    currentStoryboardUploadLoading.value = false;
    currentStoryboardUploadImageRef.value?.clearFiles();
}
const activeName = ref('image');
const actorButtonRef = ref();
const actorPopoverRef = ref();
const handleActorSelect = (item: any) => {
    actorPopoverRef.value?.hide();
    $http.post('/app/shortplay/api/Storyboard/joinActor', {
        drama_id: drama_id.value,
        storyboard_id: currentStoryboard.value.id,
        actor_id: item.id,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            getActorsList();
        } else {
            ElMessage.error(res.msg);
        }
    });
}
const previewImageVisible = ref(false);
const imageList = ref<any[]>([]);
const initialIndex = ref(0);
const handlePreviewImage = (list: any[], activeImage?: string) => {
    if (!activeImage) return;
    imageList.value = list;
    initialIndex.value = imageList.value.findIndex((image: any) => image === activeImage);
    nextTick(() => {
        previewImageVisible.value = true;
    })
}

const handleDeleteProp = (prop: any) => {
    $http.post('/app/shortplay/api/Storyboard/deleteProp', {
        drama_id: drama_id.value,
        storyboard_id: currentStoryboard.value.id,
        id: prop.id,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            currentStoryboard.value = res.data;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('删除物品失败');
    })
}
const propButtonRef = ref();
const propPopoverRef = ref();
const handlePropSelect = (item: any) => {
    propPopoverRef.value?.hide();
    $http.post('/app/shortplay/api/Storyboard/joinProp', {
        drama_id: drama_id.value,
        storyboard_id: currentStoryboard.value.id,
        prop_id: item.id,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            currentStoryboard.value = res.data;
        } else {
            ElMessage.error(res.msg);
        }
    });
}
const characterLookRef = ref();
const currentActor = ref<any>({});
const handleCharacterLook = (actor: any) => {
    if (actor.character_look_state) return;
    currentActor.value = actor;
    characterLookRef.value?.open?.({ actor: actor });
}
const handleCharacterLookSelect = (item: any) => {
    currentActor.value.character_look_state = 1;
    let url = '/app/shortplay/api/Generate/characterLook';
    if (item.type === 'actor') {
        url = '/app/shortplay/api/Storyboard/CharacterLook';
    }
    $http.post(url, {
        drama_id: drama_id.value,
        episode_id: episode_id.value,
        storyboard_id: currentStoryboard.value.id,
        actor_id: currentActor.value.id,
        character_look_id: item.id,
        actor_costume_model_id: item.actor_costume_model_id,
        actor_costume_three_view_model_id: item.actor_costume_three_view_model_id,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            if (item.type === 'actor') {
                getActorsList();
            }
        } else {
            ElMessage.error(res.msg);
            currentActor.value.character_look_state = 0;
        }
    }).catch(() => {
        ElMessage.error('应用形象失败');
        currentActor.value.character_look_state = 0;
    })
}
const handleDeleteActor = (actor: any) => {
    $http.post('/app/shortplay/api/Storyboard/deleteActor', {
        drama_id: drama_id.value,
        storyboard_id: currentStoryboard.value.id,
        id: actor.storyboard_actor_id,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            getActorsList();
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('删除演员失败');
    })
}
const handleSceneSelect = (scene: any) => {
    $http.post('/app/shortplay/api/Storyboard/update', {
        drama_id: drama_id.value,
        episode_id: episode_id.value,
        id: currentStoryboard.value.id,
        scene_id: scene.id,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            currentStoryboard.value = res.data;
        }
    }).catch(() => {
        ElMessage.error('更新分镜失败');
    })
}
const firstImageButtonRef = ref();
const firstImagePopoverRef = ref();
const lastImageButtonRef = ref();
const lastImagePopoverRef = ref();
const firstImageStoryboardRef = ref<any>();
const lastImageStoryboardRef = ref<any>();

const handleFirstImageSelect = (item: any) => {
    currentStoryboardForm.value.first_image = item.image;
    firstImagePopoverRef.value?.hide();
}
const handleLastImageSelect = (item: any) => {
    currentStoryboardForm.value.last_image = item.image;
    lastImagePopoverRef.value?.hide();
}

const dialogueCreateRef = ref<any>();
const dialogues = ref<any[]>([]);
const dialoguesLoading = ref(false);
const getDialogues = () => {
    if (dialoguesLoading.value) return;
    dialoguesLoading.value = true;
    $http.get('/app/shortplay/api/StoryboardDialogue/index', {
        params: {
            drama_id: drama_id.value,
            storyboard_id: currentStoryboard.value.id,
        }
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            dialogues.value = res.data;
            handleCurrentDialogue(dialogues.value[0]);
        }
    }).catch(() => {
        ElMessage.error('获取对话失败');
    }).finally(() => {
        dialoguesLoading.value = false;
    })
}
const currentDialogue = ref<any>();
const dialogueModel = ref<any>({});
const handleCurrentDialogue = (dialogue?: any) => {
    if (dialogue?.voice) {
        dialogue.voice.selected_emotion = dialogue.voice.emotions_enum?.find((item: any) => item.value === dialogue.emotion);
        dialogueModel.value = modelStore.get('dialogue_voice', dialogue.voice.model_id);
    }
    currentDialogue.value = dialogue;
}
const handleAddDialogue = () => {
    dialogueCreateRef.value?.open(currentStoryboard.value);
}
const handleEditDialogue = () => {
    dialogueCreateRef.value?.open(currentStoryboard.value, currentDialogue.value);
}
const handleDialogueCreateSuccess = (dialogue: any) => {
    const find = currentStoryboard.value.dialogues.find((d: any) => d.id === dialogue.id)
    if (find) {
        Object.assign(find, dialogue);
    } else {
        currentStoryboard.value.dialogues.push(dialogue);
    }
}
const dialogueVoiceDialogRef = ref<any>();
const handleDialogueVoiceSuccess = (data: any, options?: any) => {
    currentDialogue.value.voice = data;
    $http.post('/app/shortplay/api/Actor/voice', {
        id: currentDialogue.value.actor.id,
        dialogue_id: currentDialogue.value.id,
        drama_id: drama_id.value,
        episode_id: episode_id.value,
        storyboard_id: currentStoryboard.value.id,
        scene_id: currentStoryboard.value.scene_id,
        apply_scope: 'dialogue',
        voice: data,
        ...options
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('设置对话音色失败');
    })
}
const handleDeleteDialogue = () => {
    ElMessageBox.confirm('确定删除该对话吗？', '提示', {
        title: '提示',
        message: '确定删除该对话吗？',
        beforeClose: (action: any, instance: any, done: () => void) => {
            if (action === 'confirm') {
                instance.confirmButtonLoading = true;
                instance.cancelButtonLoading = true;
                $http.post('/app/shortplay/api/StoryboardDialogue/delete', {
                    drama_id: drama_id.value,
                    storyboard_id: currentStoryboard.value.id,
                    dialogue_id: currentDialogue.value.id,
                }).then((res: any) => {
                    if (res.code === ResponseCode.SUCCESS) {
                        ElMessage.success('删除成功');
                        getDialogues();
                        done();
                    } else {
                        ElMessage.error(res.msg);
                    }
                }).catch(() => {
                    ElMessage.error('删除失败');
                }).finally(() => {
                    instance.confirmButtonLoading = false;
                    instance.cancelButtonLoading = false;
                });
            } else {
                done();
            }
        }
    })
}
const generateDialogueLoading = ref(false);
const handleGenerateDialogue = () => {
    if (generateDialogueLoading.value) return;
    generateDialogueLoading.value = true;
    $http.post('/app/shortplay/api/Generate/storyboardDialogueVoice', {
        storyboard_id: currentStoryboard.value.id,
        dialogue_id: currentDialogue.value.id,
        drama_id: drama_id.value,
        prosody_volume: currentDialogue.value.prosody_volume,
        prosody_speed: currentDialogue.value.prosody_speed,
        emotion: currentDialogue.value.emotion,
        voice: currentDialogue.value.voice,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            currentDialogue.value.voice_state = true;
            ElMessage.success(res.msg);
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('生成旁白失败');
    }).finally(() => {
        generateDialogueLoading.value = false;
    })
}

const batchGenerateDialogueList = ref<any[]>([]);
const BatchGenerateDialogue = async () => {
    const loading = ElLoadingService();
    const res: any = await $http.get('/app/shortplay/api/StoryboardDialogue/index', { params: { drama_id: drama_id.value, episode_id: episode_id.value } });
    let voice_state = 0, no_voice = 0, voice_audio = 0;
    if (res.code === ResponseCode.SUCCESS) {
        const len = res.data.length;
        for (let i = 0; i < len; i++) {
            const item = res.data[i];
            if (item.audio) {
                voice_audio++;
            } else if (item.voice_state) {
                voice_state++;
            } else if (!item.voice) {
                no_voice++;
            } else {
                batchGenerateDialogueList.value.push(item);
            }
        }
        loading.close();
    } else {
        loading.close();
        ElMessage.error(res.msg);
        return;
    }
    if (batchGenerateDialogueList.value.length === 0) {
        ElMessage.info('本集分镜已全部生成对话配音');
        return;
    }
    const contents = [
        h('span', {
            class: 'h10',
        }, `本次将生成`),
        h('span', {
            class: 'h10 text-success',
        }, batchGenerateDialogueList.value.length),
        h('span', {
            class: 'h10',
        }, '条对话配音。'),
    ];
    contents.push(
        h('span', {
            class: 'h10',
        }, '生成中'),
        h('span', {
            class: 'h10 text-success',
        }, voice_state),
        h('span', {
            class: 'h10',
        }, '条。'),
    );
    contents.push(
        h('span', {
            class: 'h10',
        }, '无音色'),
        h('span', {
            class: 'h10 text-success',
        }, no_voice),
        h('span', {
            class: 'h10',
        }, '条。'),
    );
    contents.push(
        h('span', {
            class: 'h10',
        }, '已生成'),
        h('span', {
            class: 'h10 text-success',
        }, voice_audio),
        h('span', {
            class: 'h10',
        }, '条。'),
    );
    contents.push(
        h('span', {
            class: 'h10',
        }, '是否继续？'),
    );
    const options: ElMessageBoxOptions = {
        title: '确定批量生成对话配音吗？',
        message: () => h('div', {
            class: 'flex grid-gap-2 flex-wrap',
        }, contents),
        confirmButtonText: '确定',
        confirmButtonClass: 'el-button--success',
        beforeClose: (action, instance, done) => {
            if (instance.confirmButtonLoading) return;
            if (action === 'confirm') {
                instance.confirmButtonLoading = true;
                Promise.all(batchGenerateDialogueList.value.map((item: any) => {
                    return $http.post('/app/shortplay/api/Generate/storyboardDialogueVoice', {
                        dialogue_id: item.id,
                        storyboard_id: item.storyboard_id,
                        drama_id: drama_id.value,
                    });
                })).then(() => {
                    done();
                }).catch(() => {
                    ElMessage.error('批量生成对话配音失败');
                }).finally(() => {
                    instance.confirmButtonLoading = false;
                });
            } else {
                done();
            }
        }
    };
    ElMessageBox(options).then(() => {
        getDialogues();
    }).catch(() => {
    });
}
const durationButtonRef = ref();
const narrationVoiceDialogRef = ref<any>();
const narrationModel = ref<any>();
const handleNarrationVoiceSuccess = (data: any) => {
    dramaInfo.value.voice = data;
    narrationModel.value = modelStore.get('storyboard_narration_voice', data.model_id);
    $http.post('/app/shortplay/api/Drama/voice', {
        drama_id: drama_id.value,
        voice: data
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            ElMessage.success(res.msg);
            getDramaInfo();
        } else {
            ElMessage.error(res.msg);
        }
    }).catch((error) => {
        console.error('handleVoiceSuccess error', error);
        ElMessage.error('设置旁白配音失败');
    })
}
const generateNarrationLoading = ref(false);
const handleGenerateNarration = () => {
    if (generateNarrationLoading.value) return;
    generateNarrationLoading.value = true;
    $http.post('/app/shortplay/api/Generate/storyboardNarrationVoice', {
        storyboard_id: currentStoryboard.value.id,
        drama_id: drama_id.value,
        prosody_volume: dramaInfo.value.prosody_volume,
        prosody_speed: dramaInfo.value.prosody_speed,
        narration: currentStoryboard.value.narration,
        voice: dramaInfo.value.voice,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            dramaInfo.value.narration_state = true;
            ElMessage.success(res.msg);
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error('生成旁白失败');
    }).finally(() => {
        generateNarrationLoading.value = false;
    })
}
const batchGenerateNarrationList = ref<any[]>([]);
const BatchGenerateNarration = () => {
    if (!dramaInfo.value.voice) {
        ElMessage.info('当前剧本尚未选择旁白音色，请先选择');
        activeName.value = 'narration';
        return narrationVoiceDialogRef.value?.open({ modelScene: 'storyboard_narration_voice', voice: dramaInfo.value.voice });
    }
    batchGenerateNarrationList.value = storyboardList.value.filter((item: any) => item.narration && !item.narration_audio && !item.narration_state);
    if (batchGenerateNarrationList.value.length === 0) {
        ElMessage.info('本集分镜已全部生成旁白');
        return;
    }
    const contents = [
        h('span', {
            class: 'h10',
        }, `本次将生成`),
        h('span', {
            class: 'h10 text-success',
        }, batchGenerateNarrationList.value.length),
        h('span', {
            class: 'h10',
        }, '条旁白，是否继续？'),
    ];
    const options: ElMessageBoxOptions = {
        title: '确定批量生成旁白吗？',
        message: () => h('div', {
            class: 'flex grid-gap-2',
        }, contents),
        confirmButtonText: '确定',
        confirmButtonClass: 'el-button--success',
        beforeClose: (action, instance, done) => {
            if (instance.confirmButtonLoading) return;
            if (action === 'confirm') {
                instance.confirmButtonLoading = true;
                Promise.all(batchGenerateNarrationList.value.map((item: any) => {
                    return $http.post('/app/shortplay/api/Generate/storyboardNarrationVoice', {
                        storyboard_id: item.id,
                        drama_id: drama_id.value,
                    });
                })).then(() => {
                    done();
                }).catch(() => {
                    ElMessage.error('批量生成旁白失败');
                }).finally(() => {
                    instance.confirmButtonLoading = false;
                });
            } else {
                done();
            }
        }
    };
    ElMessageBox(options).then(() => {
        getStoryboardList();
    }).catch(() => {
    });
}
const speedFormatTooltip = (value: number) => {
    if (value === 1) {
        return '正常';
    }
    return `${value}x倍速`;
}
const volumeFormatTooltip = (value: number) => {
    if (value === 0) {
        return '静音';
    }
    if (value === 100) {
        return '最大';
    }
    if (value === 50) {
        return '正常';
    }
    if (value < 50) {
        return `-${value}%`;
    }
    return `+${value}%`;
}
const handleTabChange = (tab: TabPaneName) => {
    if (tab === 'dialogue' && !dialogues.value.length) {
        getDialogues();
    }
}
const cvsWrapEl = ref<any>(null);
const cvsWrapElWrapper = ref<any>(null);
const AVCanvas = useAVCanvas(cvsWrapEl, cvsWrapElWrapper);

const handlePlay = () => {
    if (AVCanvas.isPlaying.value) {
        AVCanvas.pause();
    } else {
        AVCanvas.play();
    }
}
AVCanvas.onSwitchToNextClip((currentTrackResource: TrackResourceInterface) => {
    currentStoryboard.value = storyboardList.value.find(i => i.id === currentTrackResource.id);
    currentStoryboardForm.value.storyboard_id = currentStoryboard.value.id;
    currentStoryboardForm.value.title = currentStoryboard.value.title;
    currentStoryboardForm.value.description = currentStoryboard.value.description;
    currentStoryboardForm.value.image_prompt = currentStoryboard.value.image_prompt;
    currentStoryboardForm.value.video_prompt = currentStoryboard.value.video_prompt;
    currentStoryboardForm.value.first_image = currentStoryboard.value.image;
    currentStoryboardForm.value.storyboard_location = currentStoryboard.value.storyboard_location;
    currentStoryboardForm.value.storyboard_space = currentStoryboard.value.storyboard_space;
    currentStoryboardForm.value.storyboard_time = currentStoryboard.value.storyboard_time;
    currentStoryboardForm.value.storyboard_weather = currentStoryboard.value.storyboard_weather;
    currentStoryboardForm.value.model_id = currentStoryboard.value.model_id;
    currentStoryboardForm.value.duration = currentStoryboard.value.duration;
    currentStoryboardForm.value.narration = currentStoryboard.value.narration;
    taskSearch.alias_id = currentStoryboard.value.id;
    getTaskList();
});
const handlePlayAudio = (audio: string) => {
    if (!audio) return;
    const audioElement = new Audio(audio);
    audioElement.play();
}

const xlLoading = useLoading({
    title: '正在合成',
    tips: '请勿退出页面，否则合成会中断',
    list: [
        {
            title: '获取分镜中...'
        },
        {
            title: '选择保存位置...'
        },
        {
            title: '正在准备素材...'
        },
        {
            title: '正在解析视频素材...'
        },
        {
            title: '正在解析对话素材...'
        },
        {
            title: '正在解析对话音频素材...'
        },
        {
            title: '正在解析旁白素材...'
        },
        {
            title: '正在解析旁白音频素材...'
        },
        {
            title: '正在合成中...'
        },
        {
            title: '正在上传视频...'
        },
    ],
    showCancelButton: true,
    cancelButtonText: '取消合成',
    cancelButtonClick: () => {
        video.cancel();
        xlLoading.close();
    }
});
const video = useCompsite({
    drama_id: drama_id.value,
    episode_id: episode_id.value,
    output: drama_id.value + '_' + episode_id.value + '.mp4',
});
video.on(COMPSITE_EVENTS.SAVE_FILE, (state?: any) => {
    if (state === true) {
        xlLoading.xlLoadingRef.value?.setProgress(10);
    } else if (state === false) {
        xlLoading.close();
    } else {
        xlLoading.xlLoadingRef.value?.setCurrentIndex(1);
    }
})
video.on(COMPSITE_EVENTS.PARSE_RESOURCE, (p: number) => {
    xlLoading.xlLoadingRef.value?.setCurrentIndex(2);
    const progress = 15 + (p * 15 / 100);
    xlLoading.xlLoadingRef.value?.setProgress(progress);
})
video.on(COMPSITE_EVENTS.VIDEO, (p: number) => {
    xlLoading.xlLoadingRef.value?.setCurrentIndex(3);
    const progress = 30 + (p * 10 / 100);
    xlLoading.xlLoadingRef.value?.setProgress(progress);
})
video.on(COMPSITE_EVENTS.DIALOGUES, (p: number) => {
    xlLoading.xlLoadingRef.value?.setCurrentIndex(4);
    const progress = 40 + (p * 5 / 100);
    xlLoading.xlLoadingRef.value?.setProgress(progress);
})
video.on(COMPSITE_EVENTS.DIALOGUES_AUDIO, (p: number) => {
    xlLoading.xlLoadingRef.value?.setCurrentIndex(5);
    const progress = 45 + (p * 5 / 100);
    xlLoading.xlLoadingRef.value?.setProgress(progress);
})
video.on(COMPSITE_EVENTS.NARRATIONS, (p: number) => {
    xlLoading.xlLoadingRef.value?.setCurrentIndex(6);
    const progress = 50 + (p * 5 / 100);
    xlLoading.xlLoadingRef.value?.setProgress(progress);
})
video.on(COMPSITE_EVENTS.NARRATIONS_AUDIO, (p: number) => {
    xlLoading.xlLoadingRef.value?.setCurrentIndex(7);
    const progress = 50 + (p * 5 / 100);
    xlLoading.xlLoadingRef.value?.setProgress(progress);
})
video.on(COMPSITE_EVENTS.PROGRESS, (p: number) => {
    xlLoading.xlLoadingRef.value?.setCurrentIndex(8);
    const progress = 55 + (p * 25 / 100);
    xlLoading.xlLoadingRef.value?.setProgress(progress);
})
video.on(COMPSITE_EVENTS.UPLOAD_VIDEO, (p: number) => {
    xlLoading.xlLoadingRef.value?.setCurrentIndex(9);
    const progress = 80 + (p * 20 / 100);
    xlLoading.xlLoadingRef.value?.setProgress(progress);
})
video.on(COMPSITE_EVENTS.COMPLETE, (state: boolean) => {
    if (state === true) {
        xlLoading.close();
        ElMessage.success('合成成功');
    } else {
        xlLoading.close();
        ElMessage.error('合成失败');
    }
})
const compsite = async () => {
    const s = await xlLoading.open();
    if (!s) {
        return;
    }
    xlLoading.xlLoadingRef.value?.setCurrentIndex(0);
    const res: any = await $http.get('/app/shortplay/api/Storyboard/index', { params: StoryboardSearch });
    if (res.code === ResponseCode.SUCCESS) {
        if (video.cancelRef.value) {
            return;
        }
        xlLoading.xlLoadingRef.value?.setProgress(5);
        video.synthesis(res.data);
    } else {
        xlLoading.close();
        ElMessage.error(res.msg);
    }
}
const downloadPackage = () => {
    ElMessage.info('打包下载功能暂未开放，敬请期待');
    console.log('downloadPackage');
}
onMounted(() => {
    getStoryboardList();
    getDramaInfo();
    addListener();
})
onUnmounted(() => {
    console.log('storyboards unmounted');
    unsubscribeAll();
    AVCanvas.destroy();
})
defineExpose({
    BatchImage: BatchGenerateImage,
    BatchVideo: BatchGenerateVideo,
    BatchAudio: BatchGenerateDialogue,
    BatchSFX: () => {
        ElMessage.info('音效生成功能暂未开放，敬请期待');
    },
    BatchNarration: BatchGenerateNarration,
    compsite: compsite,
    downloadPackage: downloadPackage

})
</script>
<template>
    <div class="flex flex-column draw-module">
        <div class="flex-1 flex grid-gap-10 overflow-hidden">
            <div class="flex-1 flex flex-column grid-gap-10 overflow-hidden">
                <div class="flex grid-gap-2 flex-center" style="height: 40px;">
                    <span>{{ currentStoryboard?.sceneFind?.title }}</span>
                    <span class="text-success">#{{ currentStoryboard?.sort }}</span>
                    <div class="flex-1"></div>
                    <template v-if="currentStoryboardForm.storyboard_id && activeName === 'image'">
                        <el-upload ref="uploadImageRef" :data="{ dir_name: 'storyboard/image', dir_title: '分镜图' }"
                            :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                            :headers="$http.getHeaders()" accept="image/jpeg,image/png" :limit="1" type="cover"
                            :disabled="currentStoryboardUploadLoading"
                            :before-upload="() => { currentStoryboardUploadLoading = true; return true; }"
                            :on-success="handleUploadSuccess" :show-file-list="false"
                            :on-error="() => { currentStoryboardUploadLoading = false; handleUploadError() }">
                            <el-button size="small" bg text icon="UploadFilled"
                                :loading="currentStoryboardUploadLoading">
                                <span>本地上传</span>
                            </el-button>
                        </el-upload>
                    </template>
                    <template v-if="currentStoryboardForm.storyboard_id && activeName === 'video'">
                        <el-upload ref="uploadImageRef" :data="{ dir_name: 'storyboard/video', dir_title: '分镜视频' }"
                            :action="$http.getCompleteUrl('app/shortplay/api/Uploads/upload')"
                            :headers="$http.getHeaders()" accept="video/mp4,video/webm" :limit="1" type="cover"
                            :disabled="currentStoryboardUploadLoading"
                            :before-upload="() => { currentStoryboardUploadLoading = true; return true; }"
                            :on-success="handleUploadSuccess" :show-file-list="false"
                            :on-error="() => { currentStoryboardUploadLoading = false; handleUploadError() }">
                            <el-button size="small" bg text icon="UploadFilled"
                                :loading="currentStoryboardUploadLoading">
                                <span>本地上传</span>
                            </el-button>
                        </el-upload>
                    </template>
                </div>
                <div class="flex-1 flex overflow-hidden">
                    <div class="flex-1 preview-image overflow-hidden position-relative" ref="cvsWrapElWrapper">
                        <canvas class="w-100 h-100" ref="cvsWrapEl"></canvas>
                        <div class="position-absolute bottom-0 left-0 right-0 flex z-index">
                            <el-icon size="30" @click="handlePlay" class="pointer">
                                <VideoPlay v-if="!AVCanvas.isPlaying.value" />
                                <VideoPause v-else />
                            </el-icon>
                        </div>
                        <div v-if="currentTask"
                            class="w-100 h-100 overflow-hidden position-absolute z-index-10 top-0 left-0">
                            <template v-if="currentTask.scene === 'storyboard_image'">
                                <el-avatar :src="currentTask.result.image_path" fit="contain" shape="square"
                                    class="task-item-avatar bg-mosaic"></el-avatar>
                            </template>
                            <template v-if="currentTask.scene === 'storyboard_video'">
                                <video :src="currentTask.result.video_path" controls class="task-item-avatar" autoplay
                                    muted></video>
                            </template>
                            <div class="position-absolute top-1 right-1">
                                <el-button bg text @click="handleReplaceStoryboard(currentTask)">
                                    <el-icon>
                                        <IconReplaceSvg />
                                    </el-icon>
                                    <span>替换</span>
                                </el-button>
                                <el-button bg text tag="a"
                                    :href="currentTask.result[currentTask.scene === 'storyboard_image' ? 'image_path' : 'video_path']"
                                    target="_blank" download>
                                    <el-icon>
                                        <Download />
                                    </el-icon>
                                    <span>下载</span>
                                </el-button>
                                <el-button bg text @click="currentTask = null">
                                    <el-icon>
                                        <Close />
                                    </el-icon>
                                    <span>关闭</span>
                                </el-button>
                            </div>
                        </div>
                    </div>
                    <el-scrollbar class="task-list-scrollbar">
                        <div class="flex flex-column grid-gap-4 p-4 task-list" v-if="taskList.length > 0">
                            <div class="task-item" v-for="item in taskList" :key="item.id"
                                :class="{ 'active': (currentStoryboard.use_material_type === 'image' && item.result.image_path === currentStoryboard.image) || (currentStoryboard.use_material_type === 'video' && item.result.video_path === currentStoryboard.video) }">
                                <el-avatar :src="item.status === 'success' ? item.result.image_path : ''" fit="contain"
                                    shape="square" class="task-item-avatar">
                                    <el-icon v-if="item.status != 'success'" size="20" color="var(--el-color-info)">
                                        <Loading class="circular" />
                                    </el-icon>
                                    <el-icon v-else-if="item.scene === 'storyboard_image'" size="30">
                                        <IconImageSvg />
                                    </el-icon>
                                    <el-icon v-else-if="item.scene === 'storyboard_video'" size="30">
                                        <IconVideoSvg />
                                    </el-icon>
                                </el-avatar>
                                <div class="position-absolute top-0 left-0 p-2"
                                    v-if="item.status === 'success' && item.result.image_path">
                                    <el-icon v-if="item.scene === 'storyboard_image'" size="16">
                                        <IconImageSvg />
                                    </el-icon>
                                    <el-icon v-if="item.scene === 'storyboard_video'" size="16">
                                        <IconVideoSvg />
                                    </el-icon>
                                </div>
                                <div class="flex flex-center grid-gap-2 task-item-replace pointer"
                                    v-if="item.status === 'success' && ((currentStoryboard.use_material_type === 'image' && item.result.image_path !== currentStoryboard.image) || (currentStoryboard.use_material_type === 'video' && item.result.video_path !== currentStoryboard.video))"
                                    @click="currentTask = item">
                                </div>
                            </div>
                        </div>
                    </el-scrollbar>
                </div>

                <div class="montage-storyboard rounded-4 border">
                    <el-scrollbar ref="videoScrollbarRef" class="montage-storyboard-video montage-storyboard-scrollbar"
                        x-scroll :y-scroll="false" wrap-class="montage-storyboard-video-wrap">
                        <div class="montage-storyboard-list">
                            <div class="montage-storyboard-list-item rounded-4" v-for="item in storyboardList"
                                :key="item.id" :class="{ 'active': item.id === currentStoryboard?.id }"
                                @click="handleCurrentStoryboard(item);">
                                <div class="flex montage-storyboard-list-item-title grid-gap-2">
                                    <div class="flex flex-center grid-gap-2">
                                        <el-icon class="icon-button"
                                            @click="handleChangeStoryboard(item, item.sort - 1)"
                                            :disabled="item.sort === 1">
                                            <ArrowLeftBold />
                                        </el-icon>
                                        <el-icon class="icon-button"
                                            @click="handleChangeStoryboard(item, item.sort + 1)"
                                            :disabled="item.sort === storyboardList.length">
                                            <ArrowRightBold />
                                        </el-icon>
                                    </div>
                                    <span class="h10 flex-1">场景{{ item.scene_id }} - #{{ item.sort }}</span>
                                    <el-popconfirm title="确定删除该分镜吗？" placement="bottom-end" confirm-button-type="danger"
                                        :teleported="false" width="fit-content" @confirm="handleDeleteStoryboard(item)">
                                        <template #reference>
                                            <el-icon class="icon-button hover-show">
                                                <Delete />
                                            </el-icon>
                                        </template>
                                    </el-popconfirm>
                                </div>
                                <el-avatar class="montage-storyboard-list-item-image bg-mosaic" :src="item.image"
                                    :fit="['9:16', '16:9'].includes(dramaInfo.aspect_ratio) ? 'contain' : 'cover'"
                                    v-loading="(item.image_state && item.image) || (item.video_state && item.image)"
                                    element-loading-text="生成中...">
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
                                <div class="montage-storyboard-list-item-toolbar flex-center">
                                    <span class="flex flex-center grid-gap-2 p-2 pointer"
                                        @click.stop="handleCurrentStoryboard(item); activeName = 'dialogue'">
                                        <el-icon>
                                            <Microphone />
                                        </el-icon>
                                        <span class="h10">配音</span>
                                    </span>
                                    <div class="flex-1"></div>
                                    <span class="h10">{{ formatDuration(item.duration) }}</span>
                                </div>
                                <el-popover placement="top" :teleported="true" popper-class="episode-popover">
                                    <template #reference>
                                        <el-icon class="montage-storyboard-list-item-plus"
                                            :class="{ 'active': currentStoryboard?.id === item.id }">
                                            <Plus />
                                        </el-icon>
                                    </template>
                                    <div class="flex flex-column grid-gap-4">
                                        <!-- <span class="flex flex-center grid-gap-2 p-2 pointer">
                                            <el-icon>
                                                <IconTransitionSvg />
                                            </el-icon>
                                            <span class="h10">添加转场</span>
                                        </span> -->
                                        <span class="flex flex-center grid-gap-2 p-2 pointer"
                                            @click.stop="handleCopyStoryboard(item)">
                                            <el-icon>
                                                <IconTransitionSvg />
                                            </el-icon>
                                            <span class="h10">复制分镜</span>
                                        </span>
                                        <span class="flex flex-center grid-gap-2 p-2 pointer"
                                            @click.stop="handleInsertEmptyStoryboard(item)">
                                            <el-icon>
                                                <IconStoryboardSvg />
                                            </el-icon>
                                            <span class="h10">添加分镜</span>
                                        </span>
                                    </div>
                                </el-popover>
                            </div>
                        </div>
                        <div class="bg-overlay rounded-4 p-4">
                            背景音乐
                        </div>
                    </el-scrollbar>
                </div>
            </div>
            <div class="storyboard-form-wrapper bg-overlay border rounded-4">
                <el-tabs v-model="activeName" class="storyboard-form-tabs" @tab-change="handleTabChange">
                    <el-tab-pane name="image">
                        <template #label>
                            <el-icon size="16">
                                <IconImageSvg />
                            </el-icon>
                            <span>分镜图</span>
                        </template>
                        <div v-if="currentStoryboardForm.storyboard_id"
                            class="storyboard-form flex flex-column grid-gap-4 p-4" v-loading="dialoguesLoading">
                            <div class="flex flex-column grid-gap-2">
                                <span>分镜#{{ currentStoryboard.sort }} 描述</span>
                                <span class="h10 text-info">{{ currentStoryboard.description }}</span>
                            </div>
                            <div class="flex flex-column grid-gap-2">
                                <span>首帧提示词</span>
                                <div class="bg rounded-4 p-4 border">
                                    <el-input v-model="currentStoryboardForm.image_prompt" placeholder="请输入首帧提示词"
                                        size="small" class="storyboard-form-textarea" type="textarea"
                                        :autosize="{ minRows: 6, maxRows: 20 }" />
                                    <div class="flex flex-y-center grid-gap-2">
                                        <div class="bg-overlay rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover"
                                            ref="modelButtonRef" title="选择使用AI生成图">
                                            <template v-if="model.id">
                                                <el-avatar :src="model.icon" :alt="model.name" shape="square"
                                                    :size="16"></el-avatar>
                                                <span class="h10 text-ellipsis-1" style="max-width: 60px;">{{
                                                    model.name
                                                    }}</span>
                                                <el-icon size="16" class="pointer" @click.stop="handleModelSelect()">
                                                    <Close />
                                                </el-icon>
                                            </template>
                                            <template v-else>
                                                <el-icon size="16">
                                                    <IconModelSvg />
                                                </el-icon>
                                            </template>
                                        </div>
                                        <div class="flex-1"></div>
                                        <div class="rounded-round p-3 flex flex-center grid-gap-2 pointer"
                                            style="background-color: #FFFFFF;color:#141414;"
                                            @click="handleGenerateImage">
                                            <el-icon size="20">
                                                <Loading class="circular"
                                                    v-if="generateImageLoading || currentStoryboard.image_state" />
                                                <Top v-else />
                                            </el-icon>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="flex grid-gap-2">
                                <div class="flex flex-column grid-gap-2">
                                    <span>场景</span>
                                    <el-popover placement="bottom" :teleported="false" popper-class="episode-popover"
                                        width="fit-content">
                                        <template #reference>
                                            <el-avatar :src="currentStoryboard.sceneFind?.image" fit="contain"
                                                :size="100" shape="square"></el-avatar>
                                        </template>
                                        <div class="grid-columns-8 grid-gap-4">
                                            <div class="grid-column-2" v-for="scene in sceneList" :key="scene.id">
                                                <el-avatar :src="scene.image" fit="contain" :size="100" shape="square"
                                                    class="pointer" @click="handleSceneSelect(scene)">
                                                    {{ scene.title }}
                                                </el-avatar>
                                            </div>
                                        </div>
                                    </el-popover>
                                </div>
                                <div class="flex flex-column grid-gap-2">
                                    <span>引用分镜</span>
                                    <div class="flex grid-gap-2 flex-wrap">
                                        <div v-for="(s, index) in quoteStoryboards" :key="s.id" class="actor-item">
                                            <el-avatar :src="s.image" fit="contain" :size="100"
                                                shape="square"></el-avatar>
                                            <el-icon class="actor-close" @click="handleDeleteQuoteStoryboard(index)">
                                                <Close />
                                            </el-icon>
                                        </div>
                                        <el-avatar fit="contain" :size="100" shape="square" class="pointer"
                                            ref="storyboardButtonRef">
                                            <el-icon size="26">
                                                <Plus />
                                            </el-icon>
                                        </el-avatar>
                                    </div>
                                </div>
                            </div>
                            <div class="flex flex-column grid-gap-2">
                                <span>出镜演员</span>
                                <div class="flex grid-gap-2 flex-wrap">
                                    <div v-for="actor in actorsList" :key="actor.id" class="actor-item">
                                        <el-avatar :src="actor.headimg" fit="contain" :size="100" shape="square"
                                            :title="actor.name" :alt="actor.name" class="pointer bg-mosaic"
                                            @click="handlePreviewImage(actorsList.map((i: any) => i.headimg), actor.headimg)">
                                            <div class="flex flex-column h10 grid-gap-2">
                                                <span>{{ actor.name }}</span>
                                                <span class="pointer text-warning"
                                                    v-if="actor.status_enum?.value == 'pending'">{{
                                                        actor.status_enum?.label }}</span>
                                                <span class="pointer text-primary"
                                                    v-else-if="actor.status_enum?.value != 'generated'">{{
                                                        actor.status_enum?.label }}</span>
                                            </div>
                                        </el-avatar>
                                        <el-icon class="actor-close" @click="handleDeleteActor(actor)"
                                            v-if="!actor.character_look_state">
                                            <Close />
                                        </el-icon>
                                        <el-icon class="actor-character-look" @click="handleCharacterLook(actor)"
                                            v-if="actor.status_enum?.value === 'generated'"
                                            :class="{ 'actor-character-look-selected': actor.character_look_id }">
                                            <IconClothesSvg v-if="!actor.character_look_state" />
                                            <Loading class="circular" v-else />
                                        </el-icon>
                                    </div>
                                    <el-avatar fit="contain" :size="100" shape="square" class="pointer"
                                        ref="actorButtonRef">
                                        <el-icon size="26">
                                            <Plus />
                                        </el-icon>
                                    </el-avatar>
                                </div>
                            </div>
                            <div class="flex flex-column grid-gap-2">
                                <span>出镜物品</span>
                                <div class="flex grid-gap-2 flex-wrap">
                                    <div v-for="prop in currentStoryboard.props" :key="prop.id" class="actor-item">
                                        <el-avatar :src="prop.prop.image" fit="contain" :size="100" shape="square"
                                            :title="prop.prop.name" :alt="prop.prop.name" class="pointer bg-mosaic"
                                            @click="handlePreviewImage(currentStoryboard.props.map((i: any) => i.prop.image), prop.prop.image)">
                                            <div class="flex flex-column h10 grid-gap-2">
                                                <span>{{ prop.prop.name }}</span>
                                                <span class="pointer text-warning"
                                                    v-if="prop.prop.status_enum.value == 'pending'">{{
                                                        prop.prop.status_enum.label }}</span>
                                                <span class="pointer text-primary"
                                                    v-else-if="prop.prop.status_enum.value != 'generated'">{{
                                                        prop.prop.status_enum.label }}</span>
                                            </div>
                                        </el-avatar>
                                        <el-icon class="actor-close" @click="handleDeleteProp(prop)">
                                            <Close />
                                        </el-icon>
                                    </div>
                                    <el-avatar fit="contain" :size="100" shape="square" class="pointer"
                                        ref="propButtonRef">
                                        <el-icon size="26">
                                            <Plus />
                                        </el-icon>
                                    </el-avatar>
                                </div>
                            </div>
                            <el-popover ref="modelPopoverRef" popper-class="model-popover" :virtual-ref="modelButtonRef"
                                virtual-triggering placement="bottom" width="min(100vw,380px)" trigger="click">
                                <xl-models v-model="currentStoryboardForm.model_id" @select="handleModelSelect" no-init
                                    scene="storyboard_image" />
                            </el-popover>
                            <el-popover ref="actorPopoverRef" :virtual-ref="actorButtonRef" virtual-triggering
                                placement="bottom-start" width="min(100vw,880px)" trigger="click">
                                <xl-actor @select="handleActorSelect"
                                    :types="[{ label: '本集', value: 'episode' }, { label: '本剧', value: 'drama' }]"
                                    :query="{ drama_id: drama_id, episode_id: episode_id }" />
                            </el-popover>
                            <el-popover ref="propPopoverRef" :virtual-ref="propButtonRef" virtual-triggering
                                placement="bottom-start" width="min(100vw,880px)" trigger="click">
                                <xl-prop @select="handlePropSelect"
                                    :types="[{ label: '本集', value: 'episode' }, { label: '本剧', value: 'drama' }]"
                                    :query="{ drama_id: drama_id, episode_id: episode_id }" />
                            </el-popover>
                            <el-popover ref="storyboardPopoverRef" :virtual-ref="storyboardButtonRef" virtual-triggering
                                placement="bottom-start" width="min(100vw,880px)" trigger="click"
                                @show="storyboardRef?.getStoryboardList()">
                                <xl-storyboard ref="storyboardRef" @select="handleQuoteStoryboardSelect"
                                    :query="{ drama_id: drama_id, episode_id: episode_id }" />
                            </el-popover>
                            <xl-character-look ref="characterLookRef" @select="handleCharacterLookSelect"
                                :query="{ drama_id: drama_id, episode_id: episode_id }" />
                        </div>
                    </el-tab-pane>
                    <el-tab-pane name="video">
                        <template #label>
                            <el-icon size="16">
                                <IconVideoSvg />
                            </el-icon>
                            <span>分镜视频</span>
                        </template>

                        <div v-if="currentStoryboardForm.storyboard_id"
                            class="storyboard-form flex flex-column grid-gap-4 p-4">
                            <div class="flex flex-column grid-gap-2 flex-y-flex-start">
                                <span>分镜#{{ currentStoryboard.sort }} 描述</span>
                                <span class="h10 text-info">{{ currentStoryboard.description }}</span>
                                <div class="flex flex-center grid-gap-2 mt-4">
                                    <el-avatar :src="currentStoryboardForm.first_image" fit="contain" :size="100"
                                        class="pointer" shape="square" ref="firstImageButtonRef" />
                                    <el-icon color="var(--el-color-info)">
                                        <DArrowRight />
                                    </el-icon>
                                    <el-avatar :src="currentStoryboardForm.last_image" fit="contain" :size="100"
                                        shape="square" class="pointer" ref="lastImageButtonRef">
                                        <div class="flex flex-column flex-center grid-gap-2">
                                            <el-icon color="var(--el-text-color-primary)" size="16">
                                                <Plus />
                                            </el-icon>
                                            <span class="h10 text-text-primary">尾帧</span>
                                        </div>
                                    </el-avatar>
                                </div>
                            </div>
                            <div class="flex flex-column grid-gap-2">
                                <span>视频提示词</span>
                                <div class="bg rounded-4 p-4 border">
                                    <el-input v-model="currentStoryboardForm.video_prompt" placeholder="请输入视频提示词"
                                        size="small" class="storyboard-form-textarea" type="textarea"
                                        :autosize="{ minRows: 6, maxRows: 20 }" />
                                    <div class="flex flex-y-center grid-gap-2">
                                        <div class="bg-overlay rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover"
                                            ref="videoModelButtonRef" title="选择使用AI生成视频">
                                            <template v-if="videoModel.id">
                                                <el-avatar :src="videoModel.icon" :alt="videoModel.name" shape="square"
                                                    :size="16"></el-avatar>
                                                <span class="h10 text-ellipsis-1" style="max-width: 60px;">{{
                                                    videoModel.name
                                                    }}</span>
                                                <el-icon size="16" class="pointer"
                                                    @click.stop="handleVideoModelSelect()">
                                                    <Close />
                                                </el-icon>
                                            </template>
                                            <template v-else>
                                                <el-icon size="16">
                                                    <IconModelSvg />
                                                </el-icon>
                                            </template>
                                        </div>
                                        <div class="bg-overlay rounded-round p-3 flex flex-center grid-gap-2 pointer hover-bg-hover"
                                            ref="durationButtonRef" title="选择视频时长">
                                            <el-icon size="16">
                                                <Clock />
                                            </el-icon>
                                            <span class="h10 text-ellipsis-1" style="max-width: 60px;">{{
                                                Math.floor(currentStoryboardForm.duration / 1000) }}s</span>
                                        </div>
                                        <div class="flex-1"></div>
                                        <div class="rounded-round p-3 flex flex-center grid-gap-2 pointer"
                                            style="background-color: #FFFFFF;color:#141414;"
                                            @click="handleGenerateVideo">
                                            <el-icon size="20">
                                                <Loading class="circular"
                                                    v-if="generateVideoLoading || currentStoryboard.video_state" />
                                                <Top v-else />
                                            </el-icon>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <!-- <div class="flex flex-column grid-gap-2">
                                <span>反向提示词</span>
                                <div class="bg rounded-4 p-4 border">
                                    <el-input v-model="currentStoryboardForm.video_negative_prompt" placeholder="反向提示词"
                                        size="small" class="storyboard-form-textarea" type="textarea"
                                        :autosize="{ minRows: 6, maxRows: 20 }" />
                                </div>
                            </div> -->
                            <el-popover ref="videoModelPopoverRef" popper-class="model-popover"
                                :virtual-ref="videoModelButtonRef" virtual-triggering placement="bottom"
                                width="min(100vw,380px)" trigger="click">
                                <xl-models v-model="currentStoryboardForm.video_model_id"
                                    @select="handleVideoModelSelect" no-init scene="storyboard_video" />
                            </el-popover>
                            <el-popover popper-class="episode-popover" :virtual-ref="durationButtonRef"
                                virtual-triggering placement="bottom" width="fit-content">
                                <div class="flex flex-column grid-gap-4 text-center">
                                    <span class="pointer hover-bg-hover rounded-round p-2"
                                        @click="currentStoryboardForm.duration = 5000">5s</span>
                                    <span class="pointer hover-bg-hover rounded-round p-2"
                                        @click="currentStoryboardForm.duration = 10000">10s</span>
                                    <span class="pointer hover-bg-hover rounded-round p-2"
                                        @click="currentStoryboardForm.duration = 15000">15s</span>
                                </div>
                            </el-popover>
                            <el-popover ref="firstImagePopoverRef" :virtual-ref="firstImageButtonRef" virtual-triggering
                                placement="bottom-start" width="min(100vw,880px)" trigger="click"
                                @show="firstImageStoryboardRef?.getStoryboardList()">
                                <xl-storyboard ref="firstImageStoryboardRef" @select="handleFirstImageSelect"
                                    :query="{ drama_id: drama_id, episode_id: episode_id }" />
                            </el-popover>
                            <el-popover ref="lastImagePopoverRef" :virtual-ref="lastImageButtonRef" virtual-triggering
                                placement="bottom-start" width="min(100vw,880px)" trigger="click"
                                @show="lastImageStoryboardRef?.getStoryboardList()">
                                <xl-storyboard ref="lastImageStoryboardRef" @select="handleLastImageSelect"
                                    :query="{ drama_id: drama_id, episode_id: episode_id }" />
                            </el-popover>
                        </div>
                    </el-tab-pane>
                    <el-tab-pane name="dialogue">
                        <template #label>
                            <el-icon size="16">
                                <IconDubbingSvg />
                            </el-icon>
                            <span>对话配音</span>
                        </template>

                        <div v-if="currentStoryboardForm.storyboard_id"
                            class="storyboard-form flex flex-column grid-gap-4 p-4">
                            <div class="flex flex-column grid-gap-2" v-if="dialogues?.length > 0">
                                <div class="flex flex-center grid-gap-4 text-info pointer" v-for="dialogue in dialogues"
                                    :key="dialogue.id" @click="handleCurrentDialogue(dialogue)">
                                    <el-icon size="16"
                                        :color="currentDialogue?.id === dialogue.id ? 'var(--el-color-success)' : 'var(--el-color-info)'">
                                        <Loading class="circular" v-if="dialogue.voice_state" />
                                        <Check class="border rounded-round" v-else
                                            :class="{ 'border-success text-success': currentDialogue?.id === dialogue.id }" />
                                    </el-icon>
                                    <span class="flex-1 border h10 p-2 rounded-2 text-wrap"
                                        :class="{ 'border-success text-success': currentDialogue?.id === dialogue.id }">
                                        {{ dialogue.actor.name }}{{ dialogue.inner_monologue ? '(内心OS)' : '' }}:{{
                                            dialogue.content }}
                                    </span>
                                </div>
                            </div>
                            <el-empty v-else description="暂无对话">
                                <el-button type="success" size="large" bg text @click.stop="handleAddDialogue()">
                                    <span>新增对话</span>
                                </el-button>
                            </el-empty>

                            <template v-if="currentDialogue?.id">
                                <div class="flex flex-column grid-gap-2">
                                    <span>台词</span>
                                    <div class="bg rounded-4 p-4 border">
                                        <el-input v-model="currentDialogue.content" placeholder="台词" size="small"
                                            class="storyboard-form-textarea" type="textarea" :maxlength="200"
                                            show-word-limit :autosize="{ minRows: 6, maxRows: 20 }" />
                                        <div class="flex flex-y-center grid-gap-2">
                                            <div class="flex flex-center grid-gap-2 pointer"
                                                :class="[currentDialogue.audio ? 'text-success' : 'text-info']"
                                                @click="handlePlayAudio(currentDialogue.audio)">
                                                <el-icon>
                                                    <Loading class="circular" v-if="currentDialogue.voice_state" />
                                                    <Headset v-else />
                                                </el-icon>
                                                <span class="h10">播放</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="flex flex-column grid-gap-2">
                                    <span>音色情绪</span>
                                    <div class="bg rounded-4 p-4 border">
                                        <template v-if="currentDialogue.voice">
                                            <div class="flex flex-center grid-gap-2">
                                                <el-avatar :src="currentDialogue.voice.headimg" fit="contain" :size="40"
                                                    shape="square">{{ truncate(currentDialogue.voice.name, 1)
                                                    }}</el-avatar>
                                                <div class="flex-1 flex flex-column grid-gap-2">
                                                    <span v-if="currentDialogue.voice.name">{{ currentDialogue.voice.name }}</span>
                                                    <span v-else>未命名</span>
                                                    <div class="flex grid-gap-2" v-if="currentDialogue.voice.gender_enum && currentDialogue.voice.age_enum">
                                                        <span class="bg-overlay h10 rounded-2 py-1 px-2" v-if="currentDialogue.voice.gender_enum?.label">{{
                                                            currentDialogue.voice.gender_enum?.label }}</span>
                                                        <span class="bg-overlay h10 rounded-2 py-1 px-2" v-if="currentDialogue.voice.age_enum?.label">{{
                                                            currentDialogue.voice.age_enum?.label }}</span>
                                                    </div>
                                                </div>
                                                <el-icon color="var(--el-color-info)" size="24" class="pointer" @click="dialogueVoiceDialogRef?.open({
                                                    modelScene: 'dialogue_voice',
                                                    voice: currentDialogue.voice
                                                })">
                                                    <IconSelectSvg />
                                                </el-icon>
                                            </div>
                                            <div class="flex grid-gap-10">
                                                <span style="width: 18px;"></span>
                                                <template v-if="currentDialogue.voice.emotions_enum?.length > 0">
                                                    <el-popover popper-class="episode-popover" placement="bottom"
                                                        width="fit-content">
                                                        <template #reference>
                                                            <div
                                                                class="flex-1 flex flex-center mt-6 pointer grid-gap-2">
                                                                <span>情绪：</span>
                                                                <span class="flex-1 text-info">{{
                                                                    currentDialogue.voice.selected_emotion?.label
                                                                    }}</span>
                                                                <el-icon>
                                                                    <ArrowDown />
                                                                </el-icon>
                                                            </div>

                                                        </template>
                                                        <div class="flex flex-column grid-gap-4">
                                                            <span class="pointer hover-bg-hover rounded-4 p-2"
                                                                v-for="emotion in currentDialogue.voice.emotions_enum"
                                                                :key="emotion.value"
                                                                @click="currentDialogue.voice.selected_emotion = emotion; handleDialogueVoiceSuccess(currentDialogue.voice, { apply_scope: currentDialogue.voice_level })">{{
                                                                    emotion.label }}</span>
                                                        </div>
                                                    </el-popover>
                                                </template>
                                                <template v-if="currentDialogue.voice.emotions_enum?.length > 0">
                                                    <el-popover popper-class="episode-popover" placement="bottom"
                                                        width="fit-content">
                                                        <template #reference>
                                                            <div
                                                                class="flex-1 flex flex-center mt-6 pointer grid-gap-2">
                                                                <span>语言：</span>
                                                                <span class="flex-1 text-info">{{
                                                                    currentDialogue.voice.selected_language?.label
                                                                    }}</span>
                                                                <el-icon>
                                                                    <ArrowDown />
                                                                </el-icon>
                                                            </div>

                                                        </template>
                                                        <div class="flex flex-column grid-gap-4">
                                                            <span class="pointer hover-bg-hover rounded-4 p-2"
                                                                v-for="lang in currentDialogue.voice.language_enum"
                                                                :key="lang.value"
                                                                @click="currentDialogue.voice.selected_language = lang; handleDialogueVoiceSuccess(currentDialogue.voice, { apply_scope: currentDialogue.voice_level })">{{
                                                                    lang.label }}</span>
                                                        </div>
                                                    </el-popover>
                                                </template>
                                            </div>
                                        </template>
                                        <template v-else>
                                            <div class="flex flex-center grid-gap-2">
                                                <el-avatar fit="contain" :size="40" shape="square"></el-avatar>
                                                <div class="flex-1 flex flex-column grid-gap-2">
                                                    <span class="text-info">选择音色</span>
                                                </div>
                                                <el-icon color="var(--el-color-info)" size="24" class="pointer" @click="dialogueVoiceDialogRef?.open({
                                                    modelScene: 'dialogue_voice',
                                                    voice: currentDialogue.voice
                                                })">
                                                    <IconSelectSvg />
                                                </el-icon>
                                            </div>
                                        </template>
                                    </div>
                                </div>
                                <div class="flex flex-column grid-gap-2">
                                    <span>音量</span>
                                    <div class="px-4 pb-4 flex flex-center grid-gap-4">
                                        <el-slider v-model="currentDialogue.prosody_volume" :step="1" :min="0"
                                            :max="100" class="storyboard-form-slider flex-1"
                                            :format-tooltip="volumeFormatTooltip"
                                            :marks="{ 0: '静音', 100: '最大', 50: '正常' }" />
                                        <span class="h10 text-info text-nowrap text-right" style="width: 60px;">{{
                                            volumeFormatTooltip(currentDialogue.prosody_volume) }}</span>
                                    </div>
                                </div>
                                <div class="flex flex-column grid-gap-2">
                                    <span>语速</span>
                                    <div class="px-4 flex flex-center grid-gap-10">
                                        <el-slider v-model="currentDialogue.prosody_speed" :step="0.1" show-stops
                                            :min="0.5" :max="2" :format-tooltip="speedFormatTooltip"
                                            class="storyboard-form-slider" />
                                        <span class="h10 text-info text-nowrap text-right" style="width: 60px;">{{
                                            speedFormatTooltip(currentDialogue.prosody_speed) }}</span>
                                    </div>
                                </div>
                                <div class="flex-1"></div>
                                <div class="flex">
                                    <el-popover popper-class="episode-popover" placement="bottom" width="fit-content">
                                        <template #reference>
                                            <div class="flex flex-center pointer px-4">
                                                <el-icon>
                                                    <More />
                                                </el-icon>
                                            </div>
                                        </template>
                                        <div class="flex flex-column grid-gap-4">
                                            <span class="pointer hover-bg-hover rounded-4 p-2"
                                                @click="handleAddDialogue()">新增对话</span>
                                            <span class="pointer hover-bg-hover rounded-4 p-2"
                                                @click="handleEditDialogue()">编辑当前对话</span>
                                            <span class="pointer hover-bg-hover rounded-4 p-2"
                                                @click="handleDeleteDialogue()">删除当前对话</span>
                                            <span class="pointer hover-bg-hover rounded-4 p-2"
                                                :class="{ 'text-info': currentDialogue.voice_level === 'storyboard', 'pointer': currentDialogue.voice_level !== 'storyboard' }"
                                                @click="handleDialogueVoiceSuccess(currentDialogue.voice, { apply_scope: 'storyboard' })">
                                                <span
                                                    v-if="currentDialogue.voice_level === 'storyboard'">音色已应用到当前分镜</span>
                                                <span v-else>将所选音色应用到当前分镜</span>
                                            </span>
                                            <span class="pointer hover-bg-hover rounded-4 p-2"
                                                @click="handleDialogueVoiceSuccess(currentDialogue.voice, { apply_scope: 'scene' })">将所选音色应用到当前场景</span>
                                            <span class="hover-bg-hover rounded-4 p-2"
                                                :class="{ 'text-info': currentDialogue.voice_level === 'episode', 'pointer': currentDialogue.voice_level !== 'episode' }"
                                                @click="handleDialogueVoiceSuccess(currentDialogue.voice, { apply_scope: 'episode' })">
                                                <span v-if="currentDialogue.voice_level === 'episode'">音色已应用到当前分集</span>
                                                <span v-else>将所选音色应用到当前分集</span>
                                            </span>
                                            <span class="pointer hover-bg-hover rounded-4 p-2"
                                                :class="{ 'text-info': currentDialogue.voice_level === 'drama', 'pointer': currentDialogue.voice_level !== 'drama' }"
                                                @click="handleDialogueVoiceSuccess(currentDialogue.voice, { apply_scope: 'drama' })">
                                                <span v-if="currentDialogue.voice_level === 'drama'">音色已应用到当前剧本</span>
                                                <span v-else>将所选音色应用到当前剧本</span>
                                            </span>
                                            <span class="hover-bg-hover rounded-4 p-2 text-info"
                                                v-if="currentDialogue.voice_level === 'actor'">将所选音色应用到当前角色</span>
                                        </div>
                                    </el-popover>
                                    <el-button type="success" size="large" class="flex-1"
                                        @click="handleGenerateDialogue"
                                        :loading="generateDialogueLoading || !!currentDialogue.voice_state">
                                        <span>确认修改</span>
                                        <span class="ml-1" v-if="dialoguePoints != '免费'">{{ dialoguePoints }}</span>
                                        <span v-if="dialoguePoints != '免费'">积分/次</span>
                                    </el-button>
                                </div>
                            </template>
                            <xl-voice ref="dialogueVoiceDialogRef" @success="handleDialogueVoiceSuccess" />
                            <xl-dialogue-create ref="dialogueCreateRef" @success="handleDialogueCreateSuccess" />
                        </div>
                    </el-tab-pane>
                    <el-tab-pane name="narration">
                        <template #label>
                            <el-icon size="16">
                                <IconDubbingSvg />
                            </el-icon>
                            <span>旁白配音</span>
                        </template>


                        <div v-if="currentStoryboardForm.storyboard_id"
                            class="storyboard-form flex flex-column grid-gap-4 p-4">

                            <div class="flex flex-column grid-gap-2">
                                <span>旁白台词</span>
                                <div class="bg rounded-4 p-4 border">
                                    <el-input v-model="currentStoryboardForm.narration" placeholder="旁白台词" size="small"
                                        class="storyboard-form-textarea" type="textarea" :maxlength="200"
                                        show-word-limit :autosize="{ minRows: 6, maxRows: 20 }" />
                                    <div class="flex flex-y-center grid-gap-2">
                                        <div class="flex flex-center grid-gap-2 pointer"
                                            :class="[currentStoryboard.narration_audio ? 'text-success' : 'text-info']"
                                            @click="handlePlayAudio(currentStoryboard.narration_audio)">
                                            <el-icon>
                                                <Loading class="circular" v-if="currentStoryboard.narration_state" />
                                                <Headset v-else />
                                            </el-icon>
                                            <span class="h10">播放</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="flex flex-column grid-gap-2">
                                <span>音色情绪</span>
                                <div class="bg rounded-4 p-4 border">
                                    <template v-if="dramaInfo.voice">
                                        <div class="flex flex-center grid-gap-2">
                                            <el-avatar :src="dramaInfo.voice.headimg" fit="contain" :size="40"
                                                shape="square">{{ truncate(dramaInfo.voice.name, 1) }}</el-avatar>
                                            <div class="flex-1 flex flex-column grid-gap-2">
                                                <span v-if="dramaInfo.voice.name">{{ dramaInfo.voice.name }}</span>
                                                <span v-else>未命名</span>
                                                <div class="flex grid-gap-2" v-if="dramaInfo.voice.gender_enum && dramaInfo.voice.age_enum">
                                                    <span class="bg-overlay h10 rounded-2 py-1 px-2" v-if="dramaInfo.voice.gender_enum?.label">{{
                                                        dramaInfo.voice.gender_enum?.label }}</span>
                                                    <span class="bg-overlay h10 rounded-2 py-1 px-2" v-if="dramaInfo.voice.age_enum?.label">{{
                                                        dramaInfo.voice.age_enum?.label }}</span>
                                                </div>
                                            </div>
                                            <el-icon color="var(--el-color-info)" size="24" class="pointer" @click="narrationVoiceDialogRef?.open({
                                                modelScene: 'storyboard_narration_voice',
                                                voice: dramaInfo.voice
                                            })">
                                                <IconSelectSvg />
                                            </el-icon>
                                        </div>
                                        <div class="flex grid-gap-10">
                                            <span style="width: 18px;"></span>
                                            <template v-if="dramaInfo.voice.emotions_enum?.length > 0">
                                                <el-popover popper-class="episode-popover" placement="bottom"
                                                    width="fit-content">
                                                    <template #reference>
                                                        <div class="flex-1 flex flex-center mt-6 pointer grid-gap-2">
                                                            <span>情绪：</span>
                                                            <span class="flex-1 text-info">{{
                                                                dramaInfo.voice.selected_emotion?.label }}</span>
                                                            <el-icon>
                                                                <ArrowDown />
                                                            </el-icon>
                                                        </div>

                                                    </template>
                                                    <div class="flex flex-column grid-gap-4">
                                                        <span class="pointer hover-bg-hover rounded-4 p-2"
                                                            v-for="emotion in dramaInfo.voice.emotions_enum"
                                                            :key="emotion.value"
                                                            @click="dramaInfo.voice.selected_emotion = emotion; handleNarrationVoiceSuccess(dramaInfo.voice)">{{
                                                                emotion.label }}</span>
                                                    </div>
                                                </el-popover>
                                            </template>
                                            <template v-if="dramaInfo.voice.emotions_enum?.length > 0">
                                                <el-popover popper-class="episode-popover" placement="bottom"
                                                    width="fit-content">
                                                    <template #reference>
                                                        <div class="flex-1 flex flex-center mt-6 pointer grid-gap-2">
                                                            <span>语言：</span>
                                                            <span class="flex-1 text-info">{{
                                                                dramaInfo.voice.selected_language?.label }}</span>
                                                            <el-icon>
                                                                <ArrowDown />
                                                            </el-icon>
                                                        </div>

                                                    </template>
                                                    <div class="flex flex-column grid-gap-4">
                                                        <span class="pointer hover-bg-hover rounded-4 p-2"
                                                            v-for="lang in dramaInfo.voice.language_enum"
                                                            :key="lang.value"
                                                            @click="dramaInfo.voice.selected_language = lang; handleNarrationVoiceSuccess(dramaInfo.voice)">{{
                                                                lang.label }}</span>
                                                    </div>
                                                </el-popover>
                                            </template>
                                        </div>
                                    </template>
                                    <template v-else>
                                        <div class="flex flex-center grid-gap-2">
                                            <el-avatar fit="contain" :size="40" shape="square"></el-avatar>
                                            <div class="flex-1 flex flex-column grid-gap-2">
                                                <span class="text-info">选择音色</span>
                                            </div>
                                            <el-icon color="var(--el-color-info)" size="24" class="pointer" @click="narrationVoiceDialogRef?.open({
                                                modelScene: 'storyboard_narration_voice',
                                                voice: dramaInfo.voice
                                            })">
                                                <IconSelectSvg />
                                            </el-icon>
                                        </div>
                                    </template>
                                </div>
                            </div>
                            <div class="flex flex-column grid-gap-2">
                                <span>音量</span>
                                <div class="px-4 pb-4 flex flex-center grid-gap-4">
                                    <el-slider v-model="dramaInfo.prosody_volume" :step="1" :min="0" :max="100"
                                        class="storyboard-form-slider flex-1" :format-tooltip="volumeFormatTooltip"
                                        :marks="{ 0: '静音', 100: '最大', 50: '正常' }" />
                                    <span class="h10 text-info text-nowrap text-right" style="width: 60px;">{{
                                        volumeFormatTooltip(dramaInfo.prosody_volume) }}</span>
                                </div>
                            </div>
                            <div class="flex flex-column grid-gap-2">
                                <span>语速</span>
                                <div class="px-4 flex flex-center grid-gap-10">
                                    <el-slider v-model="dramaInfo.prosody_speed" :step="0.1" show-stops :min="0.5"
                                        :max="2" :format-tooltip="speedFormatTooltip" class="storyboard-form-slider" />
                                    <span class="h10 text-info text-nowrap text-right" style="width: 60px;">{{
                                        speedFormatTooltip(dramaInfo.prosody_speed) }}</span>
                                </div>
                            </div>
                            <div class="flex-1"></div>
                            <el-button type="success" size="large" @click="handleGenerateNarration"
                                :loading="generateNarrationLoading || !!currentStoryboard.narration_state">
                                <span>确认修改</span>
                                <span class="ml-1" v-if="narrationPoints != '免费'">{{ narrationPoints }}</span>
                                <span v-if="narrationPoints != '免费'">积分/次</span>
                            </el-button>
                            <xl-voice ref="narrationVoiceDialogRef" @success="handleNarrationVoiceSuccess" />
                        </div>
                    </el-tab-pane>
                </el-tabs>
            </div>
        </div>
        <el-dialog v-model="batchGenerateDialogVisible" class="generate-storyboard-dialog" draggable width="800px">
            <template #header>
                <span class="font-weight-600">批量生成分镜</span>
            </template>
            <xl-models title="模型" v-model="currentStoryboardForm.model_id" @select="handleModelSelect" no-init
                class="flex-1 bg-overlay rounded-4 p-4" scene="storyboard_image" />
            <template #footer>
                <el-button type="info" @click="batchGenerateDialogVisible = false"
                    :disabled="batchGenerateLoading">取消</el-button>
                <div class="flex-1"></div>
                <el-button type="success" icon="Check" @click="submitBatchGenerateImage"
                    :disabled="!currentStoryboardForm.model_id" :loading="batchGenerateLoading">生成</el-button>
            </template>
        </el-dialog>
        <el-dialog v-model="batchGenerateVideoDialogVisible" class="generate-storyboard-dialog" draggable width="800px">
            <template #header>
                <span class="font-weight-600">批量生成视频</span>
            </template>
            <xl-models title="模型" v-model="currentStoryboardForm.video_model_id" @select="handleVideoModelSelect"
                no-init class="flex-1 bg-overlay rounded-4 p-4" scene="storyboard_video" />
            <template #footer>
                <el-button type="info" @click="batchGenerateVideoDialogVisible = false"
                    :disabled="batchGenerateVideoLoading">取消</el-button>
                <div class="flex-1"></div>
                <el-button type="success" icon="Check" @click="submitBatchGenerateVideo"
                    :disabled="!currentStoryboardForm.video_model_id"
                    :loading="batchGenerateVideoLoading">生成</el-button>
            </template>
        </el-dialog>
        <el-image-viewer v-if="previewImageVisible" :url-list="imageList" show-progress :initial-index="initialIndex"
            @close="previewImageVisible = false">
        </el-image-viewer>
    </div>
</template>
<style lang="scss" scoped>
.draw-module {
    height: calc(100vh - var(--xl-header-height));
    margin: 0 auto;
    padding: 20px;
    overflow: hidden;

    .preview-image {
        flex: 1;
        max-width: 1440px;
        margin: 0 auto;
        height: 100%;
        --el-avatar-bg-color: var(--el-bg-color);

        .input-upload {
            :deep(.el-upload-dragger) {
                border: none;
            }
        }
    }

    .storyboard-form-wrapper {
        width: 450px;
        height: 100%;
        overflow: hidden;
    }

    .storyboard-item {
        height: 260px;
        position: relative;
        overflow: hidden;
        box-shadow: inset 0 0 0px 2px transparent;

        &:hover {
            background-color: var(--el-fill-color-dark);

            .storyboard-delete {
                opacity: 1;
            }
        }

        &.active {
            box-shadow: inset 0 0 0px 2px var(--el-color-success);
        }

        .storyboard-avatar {
            height: 260px;
            width: 100%;
            border-radius: 0px;
        }

        .storyboard-status {
            position: absolute;
            top: 0;
            right: 0;
            width: 100%;
            padding: 10px;
            justify-content: flex-start;
            align-items: flex-start;
            z-index: 1;
        }

        .storyboard-info {
            position: absolute;
            bottom: 0px;
            left: 0;
            width: 100%;
            padding: 10px;
            justify-content: flex-start;
            align-items: flex-start;
            z-index: 1;
        }


        .storyboard-tag,
        .storyboard-name {
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

        .storyboard-delete {
            width: 28px;
            height: 28px;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }


        .storyboard-name {
            padding: 4px 8px;
            border-radius: 20px;
        }

        .storyboard-action {
            height: 50px;
            width: 100%;
        }
    }

    .storyboard-form-tabs {
        --el-tabs-header-height: 50px;
        height: 100%;

        :deep(.el-tabs__nav) {
            float: none;

            .el-tabs__active-bar {
                background-color: var(--el-color-success);
            }

            .el-tabs__item {
                flex: 1;
                align-items: center;
                gap: 4px;
                padding: 0;
                font-size: 12px;

                &.is-active {
                    color: var(--el-color-success);
                }

                &:hover {
                    color: var(--el-color-success);
                }
            }
        }

        :deep(.el-tab-pane) {
            height: 100%;
        }
    }

    .storyboard-form {
        height: 100%;

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

            :deep(.el-input__count) {
                bottom: -15px;
                right: 0px;
            }
        }

        &-slider {
            --el-slider-button-size: 10px;
            --el-slider-main-bg-color: var(--el-color-success);

            :deep(.el-slider__marks) {
                .el-slider__marks-text {
                    font-size: 12px;
                }
            }
        }
    }

    .task-list {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        width: 124px;
        align-items: flex-end;
    }

    .task-list-scrollbar {
        width: 124px;
    }

    .task-item {
        position: relative;
        width: 80px;
        height: 80px;

        &-avatar {
            width: 100%;
            height: 100%;
        }

        .task-item-replace {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(0, 0, 0, 0.5);
            padding: 5px 10px;
            border-radius: var(--el-avatar-border-radius);
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0.6;
            transition: opacity 0.3s ease-in-out;
        }

        &.active {
            width: 100px;
        }

        &:hover {
            width: 100px;

            .task-item-replace {
                opacity: 0;
            }
        }
    }

    .actor-item {
        position: relative;
        width: 100px;
        height: 100px;
        --el-border-radius-base: 8px;

        .actor-close {
            position: absolute;
            right: 0px;
            top: 0px;
            height: 15px;
            width: 15px;
            background-color: rgba(0, 0, 0, 0.75);
            color: #FFFFFF;
            font-size: 12px;
            border-top-right-radius: var(--el-border-radius-base);
            border-bottom-left-radius: var(--el-border-radius-base);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 1000;
            opacity: 0.5;

            &:hover {
                opacity: 1;
            }
        }

        .actor-character-look {
            position: absolute;
            left: 5px;
            bottom: 5px;
            height: 20px;
            width: 20px;
            background: rgba(0, 0, 0, 0.5);
            color: #FFFFFF;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 1000;
            transition: transform 0.3s ease-in-out;

            &.actor-character-look-selected {
                background: linear-gradient(to left, #79FFFF 0%, #0DF283 100%);
                color: var(--el-bg-color);
            }

            &:hover {
                transform: scale(1.3);
            }

        }
    }
}

.montage-storyboard {
    --montage-storyboard-height: 240px;
    --montage-storyboard-toolbar-height: 80px;
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
            width: fit-content;
            height: 100%;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
    }

    &-list {
        height: calc(100% - 53px);
        display: flex;
        gap: 4px;
    }

    &-list-item {
        flex-shrink: 0;
        width: calc(calc(var(--montage-storyboard-height) - var(--montage-storyboard-toolbar-height) - 10px) / 0.7);
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
            background-color: rgba(0, 0, 0, 0.08);
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
            z-index: 1000;
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