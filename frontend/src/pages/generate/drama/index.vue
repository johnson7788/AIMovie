<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus';
import router from '@/routers';
import { useRoute } from 'vue-router';
import { $http } from '@/common/http';
import { ResponseCode } from '@/common/const';
import Episode from '@/pages/generate/drama/modules/episode.vue';
import Scene from '@/pages/generate/drama/modules/scene.vue';
import Storyboard from '@/pages/generate/drama/modules/storyboard.vue';
import IconNextStepSvg from '@/svg/icon/icon-next-step.vue';
import IconBatchSvg from '@/svg/icon/icon-batch.vue';
import { useStorage } from '@/composables/useStorage';
import { useUserStore, useRefs } from '@/stores';
import { usePush } from '@/composables/usePush';
const userStore = useUserStore();
const { USERINFO } = useRefs(userStore);
const emit = defineEmits(['update:drama']);
const route = useRoute()
const drama_id = ref<string | number>(route.params.drama_id as string | number)
const episode_id = ref<string | number>(route.params.episode_id as string | number)
const episodeInfo = ref<any>({});
const sceneList = ref<any[]>([]);
const storyboardList = ref<any[]>([])
const currentEpisodeId = ref(episode_id.value);
const currentSceneId = ref();
const currentStoryboardId = ref();
const dramaInfo = ref<any>({});
watch(currentEpisodeId, (newVal) => {
    currentSceneId.value = undefined;
    currentStoryboardId.value = undefined;
    router.push(`/generate/drama/${drama_id.value}/${newVal}`);
});
watch(() => route.path, () => {
    drama_id.value = route.params.drama_id as string | number;
    episode_id.value = route.params.episode_id as string | number;
    currentEpisodeId.value = episode_id.value;
    getEpisodeInfo();
});
watch(drama_id, (_newVal, oldVal) => {
    if (oldVal) {
        unsubscribe('private-generatescenestoryboard-' + oldVal);
    }
    addListener();
});
const sceneRef = ref<any>(null);
const storyboardRef = ref<any>(null);
const loading = ref(false);
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
const getEpisodeInfo = () => {
    if (!drama_id.value || !episode_id.value || loading.value) return;
    loading.value = true;
    $http.get('/app/shortplay/api/Works/episode', {
        params: {
            drama_id: drama_id.value,
            episode_id: episode_id.value,
        }
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            sceneList.value = res.data.scenes.map((item: any) => ({
                ...item,
                component: 'view',
                saveLoading: false
            }));
            storyboardList.value = res.data.storyboards.map((item: any) => ({
                ...item,
                component: 'view',
                saveLoading: false
            }));
            delete res.data.scenes;
            delete res.data.storyboards;
            episodeInfo.value = res.data;
        } else {
            ElMessage.error(res.msg);
        }
    })
        .finally(() => {
            loading.value = false;
        });
}
const nextStep = () => {
    router.push(`/generate/actors/${drama_id.value}/${episode_id.value}`)
}
const handleClearScene = () => {
    ElMessageBox.confirm('提示', {
        title: '提示',
        message: '确定清空本集场景吗？',
        beforeClose(action, instance, done) {
            if (action === 'confirm') {
                instance.confirmButtonLoading = true;
                instance.cancelButtonLoading = true;
                $http.post('/app/shortplay/api/Scene/deleteScene', {
                    drama_id: drama_id.value,
                    episode_id: episode_id.value,
                }).then((res: any) => {
                    if (res.code === ResponseCode.SUCCESS) {
                        ElMessage.success(res.msg);
                        getEpisodeInfo();
                        done();
                    } else {
                        ElMessage.error(res.msg);
                    }
                }).catch(() => {
                    ElMessage.error('清空场景失败');
                }).finally(() => {
                    instance.cancelButtonLoading = true;
                    instance.confirmButtonLoading = false;
                })
            } else {
                done();
            }
        },
    }).then(() => {
    })
}
const handleClearStoryboard = () => {
    ElMessageBox.confirm('提示', {
        title: '提示',
        message: '确定清空本集分镜吗？',
        beforeClose(action, instance, done) {
            if (action === 'confirm') {
                instance.confirmButtonLoading = true;
                instance.cancelButtonLoading = true;
                $http.post('/app/shortplay/api/Storyboard/deleteStoryboard', {
                    drama_id: drama_id.value,
                    episode_id: episode_id.value,
                }).then((res: any) => {
                    if (res.code === ResponseCode.SUCCESS) {
                        ElMessage.success(res.msg);
                        getEpisodeInfo();
                        done();
                    } else {
                        ElMessage.error(res.msg);
                    }
                }).catch(() => {
                    ElMessage.error('清空场景失败');
                }).finally(() => {
                    instance.cancelButtonLoading = true;
                    instance.confirmButtonLoading = false;
                })
            } else {
                done();
            }
        },
    }).then(() => {
    })
}
const splitterForm = reactive({
    episode: 400,
    scene: 550
});
const storage = useStorage()
watch(splitterForm, (newVal) => {
    storage.set('splitterForm', newVal);
});
const splitterFormData = storage.get('splitterForm') as any;
if (splitterFormData) {
    splitterForm.episode = splitterFormData.episode;
    splitterForm.scene = splitterFormData.scene;
}

const { subscribe, unsubscribe, unsubscribeAll } = usePush();
const addListener = () => {
    if (drama_id.value) {
        subscribe('private-generatescenestoryboard-' + drama_id.value, (res: any) => {
            console.log('channels complete info message', res);
            if (res.episode_id === episode_id.value) {
                getEpisodeInfo();
            }
        });
        subscribe('private-generatesceneimage-' + USERINFO.value?.user, (res: any) => {
            console.log('channels complete info message', res);
            sceneList.value.forEach((item: any) => {
                if (item.id === res.id) {
                    item.image = res.image;
                    item.image_state = 0;
                }
            });
        });
    }
}
onMounted(() => {
    getEpisodeInfo();
    getDramaInfo();
    addListener();
})
onUnmounted(() => {
    unsubscribeAll();
})
</script>

<template>
    <div class="flex flex-column draw-module">
        <div class="flex-1 flex flex-column rounded-6 border flex-center overflow-hidden">
            <el-splitter class="flex-1 w-100 overflow-hidden" style="--el-border-color-light:transparent">
                <el-splitter-panel v-model:size="splitterForm.episode" :min="100"
                    class="overflow-hidden flex flex-column">
                    <span class="font-weight-600 p-4">#续集列表</span>
                    <episode v-model="currentEpisodeId" :episode-list="dramaInfo.episodes" :drama_id="drama_id"
                        :episode_id="episode_id" v-if="dramaInfo.episodes?.length > 0" :loading="loading"
                        loading-text="加载中..." />
                </el-splitter-panel>
                <el-splitter-panel v-model:size="splitterForm.scene" :min="100"
                    class="overflow-hidden flex flex-column position-relative">
                    <div class="flex flex-center pr-4">
                        <span class="font-weight-600 p-4">#场景</span>
                        <div class="flex-1"></div>
                        <div class="flex flex-center grid-gap-2">
                            <el-button type="danger" icon="Delete" size="small" bg text
                                @click="handleClearScene()">一键清空本集场景</el-button>
                            <el-button type="success" icon="Plus" size="small" bg text
                                @click="sceneRef?.openCreateScene?.()">新增</el-button>
                        </div>
                    </div>
                    <scene ref="sceneRef" v-model="currentSceneId" v-model:scene="sceneList" :drama_id="drama_id"
                        :episode_id="currentEpisodeId" :episode-info="episodeInfo" />
                </el-splitter-panel>
                <el-splitter-panel class="overflow-hidden flex flex-column position-relative" :min="100">
                    <div class="flex flex-center pr-4">
                        <span class="font-weight-600 p-4">#分镜</span>
                        <div class="flex-1"></div>
                        <div class="flex flex-center grid-gap-2">
                            <el-button type="danger" bg text size="small" @click="handleClearStoryboard()"
                                v-if="storyboardList.length > 0">一键清空分镜</el-button>
                            <el-button type="success" icon="Plus" size="small" bg text v-if="sceneList.length > 0"
                                @click="storyboardRef?.openCreateStoryboard?.()">新增</el-button>
                        </div>
                    </div>
                    <storyboard ref="storyboardRef" v-model="currentStoryboardId" v-model:storyboard="storyboardList"
                        :scene="sceneList" :drama_id="drama_id" :episode_id="currentEpisodeId"
                        v-model:current-scene-id="currentSceneId" :episode-info="episodeInfo" />
                </el-splitter-panel>
            </el-splitter>
        </div>
        <div class="p-4 w-100 flex grid-gap-4 flex-center">
            <el-button type="success" size="large" @click="sceneRef?.openGenerateSceneDialog?.()" :loading="!!episodeInfo.init_scene_state"
                v-if="sceneList.length <= 0" :icon="IconBatchSvg">
                <span>初始化场景</span>
            </el-button>
            <el-button type="success" size="large" @click="storyboardRef?.openGenerateStoryboard?.()" :loading="!!episodeInfo.init_storyboard_state"
                :disabled="storyboardList.length <= 0" :icon="IconBatchSvg">
                <span>批量生成分镜</span>
            </el-button>
            <el-button type="success" size="large" @click="nextStep">
                <span>下一步</span>
                <el-icon size="16" class="ml-2">
                    <IconNextStepSvg />
                </el-icon>
            </el-button>
        </div>
    </div>
</template>
<style lang="scss" scoped>
.draw-module {
    height: calc(100vh - var(--xl-header-height));
    margin: 0 auto;
    padding: 20px;
    overflow: hidden;
}
</style>