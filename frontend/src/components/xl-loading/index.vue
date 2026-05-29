<script setup lang="ts">
const props = defineProps<{
    title?: string;
    tips?: string;
    list?: any[];
    auto?: boolean;
    showCancelButton?: boolean;
    showConfirmButton?: boolean;
    cancelButtonText?: string;
    confirmButtonText?: string;
    confirmButtonLoading?: boolean;
    confirmButtonDisabled?: boolean;
    confirmButtonClick?: () => void;
    cancelButtonClick?: () => void;
}>();
const currentTime = ref(0);
const currentIndex = ref(0);
const currentItem = ref<any>(null);
const progress = ref<string>('0.00');
let interval: any;
const setProgress = (p: number) => {
    progress.value = p.toFixed(2);
}
const setCurrentIndex = (index: number) => {
    currentIndex.value = index;
    currentItem.value = props.list?.[index];
}
const parseItem = () => {
    currentIndex.value = props.list?.findIndex(item => currentTime.value >= item.start && currentTime.value <= item.end) || 0;
    currentItem.value = props.list?.[currentIndex.value];
    const itemDuration = currentItem.value?.end - currentItem.value?.start;
    const itemProgress = (currentTime.value - currentItem.value?.start) / itemDuration || 0;
    progress.value = (props.list?.filter(item => currentTime.value > item.end).reduce((acc, curr) => acc + curr.progress, 0) + (itemProgress * currentItem.value?.progress) || 0).toFixed(2);
}
const autoProgress = () => {
    interval = setInterval(() => {
        currentTime.value += 0.05;
        parseItem();
    }, 50);
}
onMounted(() => {
    if (props.auto) {
        autoProgress();
    }
});
onUnmounted(() => {
    clearInterval(interval);
});
defineExpose({
    setProgress,
    setCurrentIndex
});
</script>
<template>
    <div class="xl-loading">
        <span v-if="props.title" class="title">{{ props.title }}</span>
        <span v-if="props.tips" class="tips text-info">{{ props.tips }}</span>
        <div class="progress-bar mt-10">
            <div class="progress-bar-inner flex flex-center px-4 grid-gap-1 h10">
                <span class="text-success">{{ currentIndex + 1 }}.</span>
                <span class="flex-1">{{ currentItem?.title }}</span>
                <span class="text-title font-weight-600">{{ progress }}%</span>
            </div>
        </div>
        <span v-if="props.list?.length">{{ currentIndex + 1 }}/{{ props.list?.length }}</span>
        <div class="flex grid-gap-10 ">
            <el-button bg text size="large" v-if="props.showCancelButton" @click="props.cancelButtonClick">{{
                props.cancelButtonText }}</el-button>
            <el-button type="success" size="large" v-if="props.showConfirmButton" @click="props.confirmButtonClick">{{
                props.confirmButtonText }}</el-button>
        </div>
    </div>
</template>
<style lang="scss" scoped>
.xl-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;

    .title {
        font-weight: 900;
        font-size: 36px;
        line-height: 55px;
        text-align: center;
        font-style: normal;
        text-transform: none;
        color: transparent;
        background-clip: text;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-image: linear-gradient(to left, #79FFFF 0%, #0DF283 100%);
    }

    .progress-bar {
        position: relative;
        --border-width: 2px;
        --width: 400px;
        --height: 50px;
        height: calc(var(--height) + var(--border-width) * 2);
        width: calc(var(--width) + var(--border-width) * 2);
        border-radius: 10px;
        overflow: hidden;

        &::after {
            content: "";
            position: absolute;
            width: calc(var(--width) + var(--border-width) * 2);
            height: calc(var(--width) + var(--border-width) * 2);
            top: calc(calc(calc(var(--width) - var(--height)) / 2) * -1);
            // inset: -100%;
            border-radius: inherit;
            /* 边框宽度 */

            /* 跑马灯亮边（小段亮光，其余透明） */
            background: linear-gradient(to right, #79FFFF, #0DF283, transparent, transparent, transparent);
            background-repeat: no-repeat;
            background-size: 100% 100%;
            // background-position: center 0px;
            transform-origin: center center;
            animation: spin 2.5s linear infinite;
        }

        &-inner {
            position: absolute;
            top: var(--border-width);
            left: var(--border-width);
            right: var(--border-width);
            bottom: var(--border-width);
            background-color: var(--el-bg-color-overlay);
            border-radius: 10px;
            z-index: 10;
        }
    }

    .text-title {
        color: transparent;
        background-clip: text;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-image: linear-gradient(to left, #79FFFF 0%, #0DF283 100%);
    }
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}
</style>
