<script setup lang="ts">
import { computed, inject, onMounted, onBeforeUnmount, watch, ref, nextTick, type Ref } from 'vue';

const props = defineProps({
    value: {
        type: [String, Number],
        required: true
    }
});

const activeTab = inject<Ref<string | number> | undefined>('activeTab', undefined);
const setActiveTab = inject<((value: string | number) => void) | undefined>('setActiveTab', undefined);
const registerTab = inject<((value: string | number, el: HTMLElement | null) => void) | undefined>('registerTab', undefined);
const unregisterTab = inject<((value: string | number) => void) | undefined>('unregisterTab', undefined);
const updateIndicator = inject<((el?: HTMLElement | null) => void) | undefined>('updateIndicator', undefined);

const itemRef = ref<HTMLElement | null>(null);

onMounted(() => {
    nextTick(() => registerTab?.(props.value, itemRef.value));
});

onBeforeUnmount(() => {
    unregisterTab?.(props.value);
});

const isActive = computed(() => activeTab?.value === props.value);

watch(isActive, (active) => {
    if (active) {
        nextTick(() => updateIndicator?.(itemRef.value));
    }
});

const handleClick = () => {
    setActiveTab?.(props.value);
};
</script>
<template>
    <div class="xl-tabs-item" :class="{ 'xl-tabs-item-selected': isActive }" @click="handleClick" ref="itemRef">
        <slot></slot>
    </div>
</template>
<style lang="scss" scoped>
.xl-tabs-item {
    min-width: 40px;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    text-ellipsis: 1;
    overflow: hidden;
    white-space: nowrap;

    &:hover {
        color: var(--xl-tabs-selected-color);
    }

    &.xl-tabs-item-selected {
        color: var(--xl-tabs-selected-color);
    }
}
</style>