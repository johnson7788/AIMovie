<script setup lang="ts">
import { ref, reactive } from 'vue';
import IconBatchSvg from '@/svg/icon/icon-batch.vue';
import { useRefs, useUserStore, useWebConfigStore } from '@/stores';
import router from '@/routers';
import { useRoute } from 'vue-router';
const route = useRoute();
const webConfigStore = useWebConfigStore();
const { WEBCONFIG } = useRefs(webConfigStore);
const userStore = useUserStore();
const { USERINFO } = useRefs(userStore);
const dramaInfo = ref<any>({});
const handleUpdateDrama = (drama: any) => {
    dramaInfo.value = drama;
}
const font = reactive({
    color: 'rgba(255, 255, 255, 0.02)',
    fontSize: 16,
    fontWeight: 600,
    fontFamily: 'Arial, sans-serif',
})
const action = ref(route.name as string || 'generate-drama');
watch(action, (newVal) => {
    router.push({ name: newVal, params: { ...route.params } });
});
watch(() => route.path, () => {
    action.value = route.name as string;
});
const generateRef = ref();
</script>
<template>
    <div class="control-layouts">
        <div class="control-layouts-header">
            <div class="flex-1">
                <div class="control-layouts-header-logo">
                    <el-icon class="rounded-4 pointer" size="24" :title="$t('generate.backToEpisodes')"
                        @click="$router.push(`/works/${dramaInfo.id}`)"
                        style="width: 40px; height: 40px; background-color: var(--el-fill-color-dark);">
                        <Back />
                    </el-icon>
                    <el-avatar :src="dramaInfo.cover" fit="contain" :size="40" shape="square" class="bg-overlay" />
                    <div class="flex flex-column">
                        <span class="control-layouts-header-logo-text">{{ dramaInfo.title }}</span>
                        <span class="h10 text-secondary">{{ $t('generate.totalEpisodes', { num: dramaInfo.episode_num }) }}</span>
                    </div>
                </div>
            </div>
            <div class="flex-1 flex flex-center">
                <el-segmented v-model="action"
                    :options="[{ label: $t('generate.scriptAdjust'), value: 'generate-drama' }, { label: $t('generate.actorManage'), value: 'generate-actors' }, { label: $t('generate.propManage'), value: 'generate-props' }, { label: $t('generate.sceneDraw'), value: 'generate-scene' }, { label: $t('generate.storyboardView'), value: 'generate-storyboard' }]"
                    class="tabs-segmented border" />
            </div>
            <div class="flex-1 flex flex-x-flex-end flex-y-center">
                <x-header-tools :show-menu="action === 'generate-storyboard' ? ['helper'] : []" />
                <template v-if="action === 'generate-storyboard'">
                    <el-popover placement="bottom-end" width="fit-content" popper-class="episode-popover">
                        <template #reference>
                            <el-button bg text>
                                <el-icon>
                                    <IconBatchSvg />
                                </el-icon>
                                <span>{{ $t('generate.batchGen') }}</span>
                            </el-button>
                        </template>
                        <div class="flex flex-column grid-gap-2">
                            <div class="p-4 hover-bg-overlay pointer rounded-4" @click="generateRef?.BatchImage?.()">
                                {{ $t('generate.batchGenImage') }}</div>
                            <div class="p-4 hover-bg-overlay pointer rounded-4" @click="generateRef?.BatchVideo?.()">
                                {{ $t('generate.batchGenVideo') }}</div>
                            <div class="p-4 hover-bg-overlay pointer rounded-4" @click="generateRef?.BatchAudio?.()">
                                {{ $t('generate.batchGenVoice') }}</div>
                            <div class="p-4 hover-bg-overlay pointer rounded-4"
                                @click="generateRef?.BatchNarration?.()">
                                {{ $t('generate.batchGenNarration') }}</div>
                            <!-- <div class="p-4 hover-bg-overlay pointer rounded-4" @click="generateRef?.BatchSFX?.()"> 批量生成音效</div> -->
                        </div>
                    </el-popover>
                    <el-button type="success" bg text @click="generateRef?.downloadPackage?.()">
                        <el-icon>
                            <Download />
                        </el-icon>
                        <span>{{ $t('generate.packDownload') }}</span>
                    </el-button>
                    <el-button color="#FFFFFF" @click="generateRef?.compsite?.()">
                        <el-icon>
                            <Download />
                        </el-icon>
                        <span>{{ $t('generate.exportVideo') }}</span>
                    </el-button>
                </template>
            </div>
        </div>
        <el-watermark :font="font" :content="[WEBCONFIG?.web_name, USERINFO?.nickname, USERINFO?.mobile]">
            <router-view v-slot="{ Component }">
                <component ref="generateRef" :is="Component" @update:drama="handleUpdateDrama" />
            </router-view>
        </el-watermark>
    </div>
</template>
<style scoped lang="scss">
.control-layouts {
    --xl-header-height: 72px;
    padding: var(--xl-header-height) 0 0 0;
    transition: padding 0.3s ease-in-out;

    &-header {
        width: 100%;
        height: var(--xl-header-height);
        background-color: rgba(var(--el-bg-color-rgb-r), var(--el-bg-color-rgb-g), var(--el-bg-color-rgb-b), 0.35);
        backdrop-filter: blur(20px);
        position: fixed;
        top: 0;
        left: 0;
        z-index: 10;
        // box-shadow: 0 0 0 2px var(--el-border-color);
        padding: 0 20px;
        display: flex;
        align-items: center;
        gap: 20px;

        &-logo {
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: start;
            gap: 10px;

            &-img {
                width: 30px;
                height: 30px;
            }

            &-text {
                font-size: 16px;
                font-weight: 500;
            }
        }
    }

    .tabs-segmented {
        --el-border-radius-base: 6px;
        --el-segmented-bg-color: var(--el-bg-color-overlay);
        --el-segmented-padding: 4px;
        --el-segmented-item-selected-bg-color: #FFFFFF;
        --el-segmented-item-selected-color: var(--el-bg-color);
        font-weight: 600;

        :deep(.el-segmented__item) {
            padding: 8px 0;
            width: 120px;
        }

        :deep(.el-segmented__group) {
            gap: 10px;
        }
    }
}
</style>