<script setup lang="ts">
import Edit from '@/pages/voice/modules/edit.vue'
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { truncate } from '@/common/functions';
import router from '@/routers';
const voiceList = ref<any[]>([]);
const loading = ref(false);
const getVoiceList = () => {
    voiceList.value = [];
    loading.value = true;
    $http.get('/app/shortplay/api/Voice/list', {
        params: {
            action: 'self'
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
/* const handlePlayAudio = (audio: any) => {
    if (!audio) return;
    const audioElement = new Audio(audio);
    audioElement.play();
} */
const editVoiceRef = ref<any>(null);
const selectedVoice = ref<any>();
const handleVoiceItemClick = (item: any) => {
    selectedVoice.value = item;
    editVoiceRef.value?.open(item.id);
}
onMounted(() => {
    getVoiceList();
})
</script>
<template>
    <div class="voice-page">
        <div class="grid-columns-8 grid-gap-4" v-if="voiceList.length > 0">
            <div class="grid-column-1 rounded-4 p-4  flex flex-column grid-gap-4 actor-item actor-item-b flex-center"
                @click="router.push('/voice/create')">
                <el-icon size="40" color="var(--el-color-info)" class="rounded-4 border border-2 border-info p-2">
                    <Plus />
                </el-icon>
                <div class="flex flex-column grid-gap-2">
                    <span>创建音色</span>
                </div>
            </div>
            <div class="grid-column-1 rounded-4 p-4  flex flex-column grid-gap-4 actor-item actor-item-b flex-center"
                v-for="item in voiceList" :key="item.id" @click="handleVoiceItemClick(item)"
                :class="{ 'actor-item-selected': selectedVoice?.voice_id === item.voice_id }">
                <el-avatar :src="item.headimg" :size="60">
                    {{ truncate(item.name, 1) }}
                </el-avatar>
                <div class="flex flex-column grid-gap-2 flex-center">
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
        </div>
        <el-empty v-else description="暂无音色数据">
            <el-button type="success" size="large" bg text @click.stop="router.push('/voice/create')"> 创建音色 </el-button>
        </el-empty>
        <Edit ref="editVoiceRef" @update="getVoiceList" />
    </div>
</template>
<style lang="scss" scoped>
.actor-item {
    height: 180px;
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