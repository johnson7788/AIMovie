<script setup lang="ts">
import { ref, provide, watch, nextTick, onMounted, onBeforeUnmount } from 'vue';

const props = withDefaults(defineProps<{
    modelValue: string | number
    dotWidth?: number,
    color?: string,
}>(), {
    modelValue: '',
    dotWidth: 20,
    color: 'var(--el-color-success)'
});

const emit = defineEmits<{
    (e: 'update:modelValue', value: string | number): void;
    (e: 'change', value: string | number): void;
}>();

const activeTab = ref(props.modelValue);
const tabs = ref<(string | number)[]>([]);
const tabRefs = new Map<string | number, HTMLElement | null>();
const dotLeft = ref(0);
const dotWidth = ref(props.dotWidth);
const containerRef = ref<HTMLElement | null>(null);
let frameId: number | null = null;
watch(activeTab, (value) => {
    emit('change', value);
})
const setActiveTab = (value: string | number) => {
    if (activeTab.value === value) {
        return;
    }

    activeTab.value = value;
    emit('update:modelValue', value);
    nextTick(updateIndicator);
};

const updateIndicator = (el?: HTMLElement | null) => {
    if (typeof window === 'undefined') {
        return;
    }

    const target = el ?? tabRefs.get(activeTab.value) ?? null;
    if (!target) {
        return;
    }

    const { offsetWidth, offsetLeft } = target;

    if (offsetWidth === 0) {
        if (frameId !== null) {
            window.cancelAnimationFrame(frameId);
        }
        frameId = window.requestAnimationFrame(() => {
            frameId = null;
            updateIndicator(target);
        });
        return;
    }

    dotLeft.value = offsetLeft + offsetWidth / 2 - dotWidth.value / 2;
};

const registerTab = (value: string | number, el: HTMLElement | null) => {
    if (!tabs.value.includes(value)) {
        tabs.value.push(value);
    }
    tabRefs.set(value, el);

    if (value === activeTab.value) {
        nextTick(() => updateIndicator(el));
    }
};

const unregisterTab = (value: string | number) => {
    const index = tabs.value.indexOf(value);
    if (index !== -1) {
        tabs.value.splice(index, 1);
    }

    tabRefs.delete(value);
    if (activeTab.value === value) {
        const nextValue = tabs.value[0];
        if (nextValue !== undefined) {
            activeTab.value = nextValue;
            // emit('update:modelValue', nextValue);
            nextTick(updateIndicator);
        }
    }
};

watch(
    () => props.modelValue,
    (value) => {
        if (activeTab.value !== value) {
            activeTab.value = value;
            nextTick(updateIndicator);
        }
    }
);

onMounted(() => {
    nextTick(updateIndicator);
});

onBeforeUnmount(() => {
    if (frameId !== null) {
        window.cancelAnimationFrame(frameId);
        frameId = null;
    }
});

provide('tabs', tabs);
provide('activeTab', activeTab);
provide('setActiveTab', setActiveTab);
provide('registerTab', registerTab);
provide('unregisterTab', unregisterTab);
provide('updateIndicator', updateIndicator);
</script>
<template>
    <div class="xl-tabs" :style="{
        '--xl-tabs-dot-left': `${dotLeft}px`,
        '--xl-tabs-dot-width': `${dotWidth}px`,
        '--xl-tabs-selected-color': color,
        '--xl-tabs-dot-bg-color': color,
    }" ref="containerRef">
        <slot :activeTab="activeTab"></slot>
    </div>
</template>
<style lang="scss" scoped>
.xl-tabs {
    // --xl-tabs-selected-color: var(--el-color-success);
    // --xl-tabs-dot-bg-color: var(--el-color-success);
    --xl-tabs-dot-width: 20px;
    --xl-tabs-dot-height: 2px;
    display: flex;
    gap: 10px;
    position: relative;
    overflow: hidden;

    &::after {
        content: "";
        position: absolute;
        bottom: 0;
        left: 0;
        width: var(--xl-tabs-dot-width);
        height: var(--xl-tabs-dot-height);
        background-color: var(--xl-tabs-dot-bg-color);
        border-radius: var(--xl-tabs-dot-height);
        transform: translateX(var(--xl-tabs-dot-left, 0px));
        transition: transform 0.3s ease-in-out, width 0.3s ease-in-out;
    }
}
</style>