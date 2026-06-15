<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const emit = defineEmits(['success']);
const createSceneAction = ref<'form' | 'scene'>('form');
const createSceneForm = reactive({
    id: '',
    title: '',
    scene_space: '',
    scene_location: '',
    scene_time: '',
    scene_weather: '',
    description: '',
    atmosphere: '',
    drama_id: '',
    episode_id: '',
});
const createSceneFormRules = {
    title: [{ required: true, message: '', trigger: 'blur' }],
    scene_space: [{ required: true, message: '', trigger: 'blur' }],
    scene_location: [{ required: true, message: '', trigger: 'blur' }],
    scene_time: [{ required: true, message: '', trigger: 'blur' }],
    scene_weather: [{ required: true, message: '', trigger: 'blur' }],
    description: [{ required: true, message: '', trigger: 'blur' }],
};
const createSceneFormLoading = ref(false);
const episodes = ref<any[]>([]);
const selectedEpisodeId = ref('');
const getEpisodes = () => {
    $http.get('/app/shortplay/api/DramaEpisode/episodes', {
        params: {
            drama_id: createSceneForm.drama_id,
        }
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            episodes.value = res.data;
            selectedEpisodeId.value = episodes.value[0]?.id || '';
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error(t('scene.getEpisodesFail'));
    })
}
const handleSelectScene = (item: any) => {
    if (createSceneFormLoading.value) return;
    createSceneFormLoading.value = true;
    $http.post('/app/shortplay/api/Scene/copyScene', {
        episode_id: createSceneForm.episode_id,
        drama_id: createSceneForm.drama_id,
        scene_id: item.id,
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            emit('success', res.data);
            createSceneDialogVisible.value = false;
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error(t('scene.addSceneFail'));
    }).finally(() => {
        createSceneFormLoading.value = false;
    });
}
const createSceneDialogVisible = ref(false);
const createSceneFormRef = ref<any>(null);
const cancelCreateScene = () => {
    createSceneFormRef.value?.resetFields();
    createSceneDialogVisible.value = false;
    createSceneForm.id = '';
    createSceneForm.title = '';
    createSceneForm.scene_location = '';
    createSceneForm.scene_space = '';
    createSceneForm.scene_time = '';
    createSceneForm.scene_weather = '';
    createSceneForm.description = '';
    createSceneForm.atmosphere = '';
    createSceneForm.drama_id = '';
    createSceneForm.episode_id = '';
}
const handleCreateScene = () => {
    if (createSceneFormLoading.value) return;
    createSceneFormLoading.value = true;
    $http.post('/app/shortplay/api/Scene/update', createSceneForm).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            emit('success', res.data);
            cancelCreateScene();
        } else {
            ElMessage.error(res.msg);
        }
    }).catch(() => {
        ElMessage.error(t('scene.addSceneFail'));
    }).finally(() => {
        createSceneFormLoading.value = false;
    });
}
const openCreateScene = (options: any) => {
    if (options.scene) {
        createSceneForm.id = options.scene.id;
        createSceneForm.title = options.scene.title;
        createSceneForm.scene_location = options.scene.scene_location;
        createSceneForm.scene_space = options.scene.scene_space;
        createSceneForm.scene_time = options.scene.scene_time;
        createSceneForm.scene_weather = options.scene.scene_weather;
        createSceneForm.description = options.scene.description;
        createSceneForm.atmosphere = options.scene.atmosphere;
    }
    createSceneForm.drama_id = options.drama_id;
    createSceneForm.episode_id = options.episode_id;
    // Update validation messages with current locale
    createSceneFormRules.title[0].message = t('scene.inputSceneName');
    createSceneFormRules.scene_space[0].message = t('scene.inputInteriorExterior');
    createSceneFormRules.scene_location[0].message = t('scene.inputLocation');
    createSceneFormRules.scene_time[0].message = t('scene.inputTime');
    createSceneFormRules.scene_weather[0].message = t('scene.inputWeather');
    createSceneFormRules.description[0].message = t('scene.inputDesc');
    getEpisodes();
    createSceneDialogVisible.value = true;
}
defineExpose({
    open: openCreateScene
})
</script>
<template>
    <div>
        <el-dialog v-model="createSceneDialogVisible" class="generate-scene-dialog" draggable>
            <template #header>
                <span class="font-weight-600" v-if="createSceneForm.id">{{ t('scene.editScene') }}</span>
                <span class="font-weight-600" v-else>{{ t('scene.addScene') }}</span>
            </template>
            <el-segmented v-model="createSceneAction" :disabled="createSceneFormLoading"
                :options="[{ label: t('scene.fillSceneInfo'), value: 'form' }, { label: t('scene.selectFromEpisode'), value: 'scene' }]"
                class="tabs-segmented border" v-if="!createSceneForm.id" />
            <el-form ref="createSceneFormRef" label-position="top" v-if="createSceneAction === 'form'"
                :disabled="createSceneFormLoading" :model="createSceneForm" :rules="createSceneFormRules">
                <el-form-item :label="t('scene.sceneName')" prop="title">
                    <el-input v-model="createSceneForm.title" :placeholder="t('scene.sceneNamePlaceholder')" class="scene-item-input" />
                </el-form-item>
                <el-form-item :label="t('scene.location')">
                    <div class="w-100 grid-columns-2 grid-gap-2">
                        <el-form-item prop="scene_space">
                            <el-input v-model="createSceneForm.scene_space" :placeholder="t('scene.interiorExterior')"
                                class="scene-item-input grid-column-1 w-100" />
                        </el-form-item>
                        <el-form-item prop="scene_location">
                            <el-input v-model="createSceneForm.scene_location" :placeholder="t('scene.location')"
                                class="scene-item-input grid-column-1" />
                        </el-form-item>
                        <el-form-item prop="scene_time">
                            <el-input v-model="createSceneForm.scene_time" :placeholder="t('scene.time')"
                                class="scene-item-input grid-column-1" />
                        </el-form-item>
                        <el-form-item prop="scene_weather">
                            <el-input v-model="createSceneForm.scene_weather" :placeholder="t('scene.weather')"
                                class="scene-item-input grid-column-1" />
                        </el-form-item>
                    </div>
                </el-form-item>
                <el-form-item :label="t('scene.desc')" prop="description">
                    <el-input v-model="createSceneForm.description" type="textarea"
                        :autosize="{ minRows: 1, maxRows: 10 }" :placeholder="t('scene.descPlaceholder')" class="scene-item-textarea" />
                </el-form-item>
            </el-form>
            <div v-if="createSceneAction === 'scene'" class="flex flex-center grid-gap-4">
                <el-scrollbar height="400px">
                    <div class="episode-tabs"
                        style="--el-anchor-active-color: var(--el-color-success);--el-anchor-marker-bg-color: var(--el-color-success);">
                        <span v-for="(item, index) in episodes" :key="item.id" @click="selectedEpisodeId = item.id"
                            class="episode-tabs-item" :class="{ 'is-active': item.id === selectedEpisodeId }">
                            #{{ index + 1 }} {{ item.title }}
                        </span>
                    </div>
                </el-scrollbar>
                <el-scrollbar height="400px" class="flex-1">
                    <div class="episode-tabs"
                        style="--el-anchor-active-color: var(--el-color-success);--el-anchor-marker-bg-color: var(--el-color-success);">
                        <span
                            v-for="item in episodes.find((item: any) => item.id === selectedEpisodeId)?.scenes"
                            :key="item.id" class="episode-tabs-item"
                            :class="{ 'is-active': item.id === selectedEpisodeId }" @click="handleSelectScene(item)">
                            #{{ item.id }} {{ item.title }}·{{ item.scene_location }}
                        </span>
                    </div>
                </el-scrollbar>
            </div>
            <template #footer>
                <div class="flex flex-center grid-gap-2" v-if="createSceneAction === 'form'">
                    <el-button type="info" @click="cancelCreateScene" :disabled="createSceneFormLoading">{{ t('common.cancel') }}</el-button>
                    <el-button type="success" @click="handleCreateScene" :disabled="createSceneFormLoading"
                        :loading="createSceneFormLoading">{{ t('common.submit') }}</el-button>
                </div>
            </template>
        </el-dialog>
    </div>
</template>
<style lang="scss" scoped>
.scene-item-textarea {
    width: 100%;
    --el-input-bg-color: var(--el-bg-color-overlay);
    --el-input-border-color: var(--el-bg-color-overlay);
    --el-input-border-radius: 6px;
    --el-input-focus-border-color: var(--el-bg-color-overlay);
    --el-input-text-color: var(--el-text-color-primary);
    --el-input-placeholder-color: var(--el-text-color-placeholder);
    --el-input-focus-text-color: var(--el-text-color-primary);
    --el-input-focus-placeholder-color: var(--el-text-color-placeholder);
    --el-input-focus-border-color: var(--el-bg-color-overlay);
    --el-input-hover-border-color: var(--el-bg-color-overlay);

    :deep(.el-textarea__inner) {
        resize: none;
        padding: 10px;
    }
}

.scene-item-input {
    --el-input-bg-color: var(--el-bg-color-overlay);
    --el-input-border-color: var(--el-bg-color-overlay);
    --el-input-border-radius: 6px;
    --el-input-focus-border-color: var(--el-bg-color-overlay);
    --el-input-text-color: var(--el-text-color-primary);
    --el-input-placeholder-color: var(--el-text-color-placeholder);
    --el-input-focus-text-color: var(--el-text-color-primary);
    --el-input-focus-placeholder-color: var(--el-text-color-placeholder);
    --el-input-focus-border-color: var(--el-bg-color-overlay);
    --el-input-hover-border-color: var(--el-bg-color-overlay);

    :deep(.el-textarea__inner) {
        resize: none;
        padding: 10px;
    }
}

.scene-item-select {
    width: 180px;
    --el-select-bg-color: var(--el-bg-color-overlay);
    --el-select-input-focus-border-color: var(--el-color-success);
}

.episode-tabs {
    display: flex;
    flex-direction: column;
    gap: 10px;
    --el-anchor-bg-color: transparent;
    --el-anchor-padding-indent: 0;
    --el-anchor-line-height: 50px;

    :deep(.el-anchor__list) {
        gap: 10px;
        padding-bottom: 0;
    }

    :deep(.el-anchor__marker) {
        top: 0;
        bottom: 0;
        height: var(--el-anchor-line-height);
        border-radius: 6px;
    }

    .episode-tabs-item {
        flex-shrink: 0;
        cursor: pointer;
        padding-left: 0;
        background: var(--el-fill-color);
        border-radius: 6px;
        border-radius: 6px;
        font-weight: 600;
        padding: 10px;
        z-index: 1;
        color: var(--el-text-color-secondary);

        &.is-active {
            color: var(--el-bg-color);
            background: var(--el-color-success);
        }
    }
}
</style>
