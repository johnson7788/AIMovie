<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { truncate } from '@/common/functions';
const voiceForm = ref<any>({
    model_id: '',
    voice_id: '',
    voice_channel: 'yidevs',
});
watch(() => voiceForm.value.voice_channel, (newVal, oldVal) => {
    console.log(newVal, oldVal);
});
const voiceDialogVisible = ref(false);
const emit = defineEmits(['success']);
const modelScene = ref('');
const openVoiceDialog = (options: any) => {
    modelScene.value = options.modelScene;
    if (options.voice) {
        selectedVoice.value = options.voice;
        voiceForm.value.voice_id = options.voice.voice_id;
        voiceForm.value.voice_channel = options.voice.voice_channel;
        voiceForm.value.model_id = options.voice.model_id;
    }
    nextTick(() => {
        voiceDialogVisible.value = true;
    });
}
const closeVoiceDialog = () => {
    voiceForm.value = {
        model_id: '',
        voice_id: '',
        voice_channel: 'yidevs',
    };
    voiceDialogVisible.value = false;
}
const voiceList = ref<any[]>([]);
const loading = ref(false);
const getVoiceList = () => {
    voiceList.value = [];
    if (!voiceForm.value.model_id || !voiceForm.value.voice_channel) return;
    loading.value = true;
    $http.get('/app/shortplay/api/Voice/list', {
        params: {
            model_id: voiceForm.value.model_id,
            action: voiceForm.value.voice_channel,
            scene: modelScene.value,
            status:'success'
        }
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            voiceList.value = res.data;
        }
    }).catch(() => {
        ElMessage.error('获取配音列表失败');
    }).finally(() => {
        loading.value = false;
    });
}
const handleModelSelect = (model: any) => {
    voiceForm.value.model_id = model.id;
    voiceForm.value.voice_id = '';
    getVoiceList();
}
const handlePlayAudio = (audio: any) => {
    if (!audio) return;
    const audioElement = new Audio(audio);
    audioElement.play();
}
const selectedVoice = ref<any>();
const handleVoiceItemClick = (item: any) => {
    selectedVoice.value = item;
    voiceForm.value.voice_id = item.voice_id;
}
const submitVoiceDialogLoading = ref(false);
const submitVoiceDialog = () => {
    emit('success', { ...selectedVoice.value, voice_channel: voiceForm.value.voice_channel, model_id: voiceForm.value.model_id });
    closeVoiceDialog();
}
const handleBeforeClose = () => {
    if (submitVoiceDialogLoading.value) return;
    closeVoiceDialog();
}
defineExpose({
    open: openVoiceDialog,
    close: closeVoiceDialog
})
</script>
<template>
    <div class="voice-page">
        <el-dialog v-model="voiceDialogVisible" class="generate-scene-dialog" draggable :close-on-press-escape="false"
            append-to-body destroy-on-close :close-on-click-modal="false" :before-close="handleBeforeClose"
            width="min(100%,1000px)">
            <template #header>
                <span class="font-weight-600">配音</span>
            </template>
            <div class="flex grid-gap-4">
                <div class="flex flex-column grid-gap-4" style="width: 300px;">
                    <xl-models v-model="voiceForm.model_id" :scene="modelScene" :scrollProps="{ height: '320px' }"
                        @select="handleModelSelect" />
                </div>
                <div class="flex-1 flex flex-column grid-gap-4">
                    <xl-tabs v-model="voiceForm.voice_channel" class="text-info" @change="getVoiceList">
                        <xl-tabs-item value="yidevs" class="pb-2">公共音色</xl-tabs-item>
                        <xl-tabs-item value="self" class="pb-2">我的音色</xl-tabs-item>
                    </xl-tabs>
                    <el-scrollbar v-loading="loading" height="max(450px,50vh)">
                        <div class="grid-columns-3 grid-gap-4" v-if="voiceList.length > 0">
                            <div class="grid-column-1 rounded-4 p-4  flex flex-column grid-gap-4 actor-item actor-item-b"
                                v-for="item in voiceList" :key="item.id" @click="handleVoiceItemClick(item)"
                                :class="{ 'actor-item-selected': selectedVoice?.voice_id === item.voice_id }">
                                <div class="w-100 flex grid-gap-2 flex-center">
                                    <el-avatar :src="item.headimg" :size="60" shape="square">
                                        {{ truncate(item.name, 1) }}
                                    </el-avatar>
                                    <div class="flex-1 flex flex-column grid-gap-2">
                                        <span v-if="item.name">{{ item.name }}</span>
                                        <span v-else>未命名</span>
                                        <div class="flex grid-gap-2" v-if="item.gender_enum && item.age_enum">
                                            <span class="bg h10 rounded-2 py-1 px-2" v-if="item.gender_enum?.label">{{
                                                item.gender_enum?.label
                                            }}</span>
                                            <span class="bg h10 rounded-2 py-1 px-2" v-if="item.age_enum?.label">{{
                                                item.age_enum?.label }}</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="flex-1 flex flex-column grid-gap-2"
                                    v-if="voiceForm.voice_channel === 'yidevs'">
                                    <span>支持语言：</span>
                                    <div class="flex grid-gap-2 flex-wrap">
                                        <span v-for="lang in item.language_enum" :key="lang.value"
                                            class="bg h10 rounded-2 py-1 px-2 flex grid-gap-2 flex-center"
                                            @click.stop="handlePlayAudio(item.audios?.[lang.value])">
                                            <el-icon v-if="item.audios?.[lang.value]">
                                                <Headset />
                                            </el-icon>
                                            <span>{{ lang.label }}</span>
                                        </span>
                                    </div>
                                    <span>支持情绪：</span>
                                    <div class="flex grid-gap-2 flex-wrap" v-if="item.emotions_enum.length > 0">
                                        <span v-for="emotion in item.emotions_enum" :key="emotion.value"
                                            class="bg h10 rounded-2 py-1 px-2">
                                            {{ emotion.label }}
                                        </span>
                                    </div>
                                    <span class="text-secondary h10" v-else>暂无支持情绪</span>
                                </div>
                            </div>
                        </div>
                        <el-empty v-else description="暂无音色数据" />
                    </el-scrollbar>
                </div>
            </div>
            <template #footer>
                <el-button bg text @click="closeVoiceDialog" :disabled="submitVoiceDialogLoading">取消</el-button>
                <div class="flex-1"></div>
                <el-button type="success" @click="submitVoiceDialog" :loading="submitVoiceDialogLoading">确定</el-button>
            </template>
        </el-dialog>
    </div>
</template>
<style lang="scss" scoped>
.actor-item {
    cursor: pointer;
    border-width: 1px;
    border-style: solid;
    border-color: rgba(255, 255, 255, 0.1);

    &:hover {
        background-color: rgba(255, 255, 255, 0.08);
    }

    .bg {
        background-color: rgba(255, 255, 255, 0.1);
    }

    &-selected {
        border-color: var(--el-color-success);
    }
}

.el-input {
    --el-input-border-radius: 20px;
}

.el-select {
    --el-border-radius-base: 20px;
}
</style>