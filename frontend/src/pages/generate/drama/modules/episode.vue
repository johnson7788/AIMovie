<script lang="ts" setup>
const props = withDefaults(defineProps<{
    modelValue: string | number
    drama_id: string | number
    episode_id: string | number
    episodeList: any[]
    loading: any
    loadingText: string
}>(), {
    modelValue: '',
    drama_id: '',
    episode_id: '',
    episodeList: () => [],
    loading: false,
    loadingText: '加载中...',
});
const emit = defineEmits(['update:modelValue']);
const episodeList = ref<any[]>(props.episodeList);
const handleClick = (item: any) => {
    emit('update:modelValue', item.id);
}
</script>
<template>
    <el-scrollbar class="p-4" ref="tabsRef" v-loading="!!loading" :element-loading-text="loadingText">
        <div class="episode-tabs"
            style="--el-anchor-active-color: var(--el-color-success);--el-anchor-marker-bg-color: var(--el-color-success);">
            <span v-for="(item, index) in episodeList" :key="item.id" @click="handleClick(item)"
                class="episode-tabs-item" :class="{ 'is-active': item.id === modelValue }">
                #{{ index + 1 }} {{ item.title }}
            </span>
        </div>
    </el-scrollbar>
</template>
<style lang="scss" scoped>
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
        background: #272727;
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