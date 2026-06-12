<script setup lang="ts">

interface DurationOption {
    value: number;
    label: string;
}

const props = withDefaults(defineProps<{
    modelValue: number;
    variant?: 'default' | 'drama';
}>(), {
    variant: 'default',
});

const emit = defineEmits(['update:modelValue']);

const defaultOptions: DurationOption[] = [
    { value: 60, label: '60秒' },
    { value: 90, label: '90秒' },
    { value: 120, label: '120秒' },
    { value: 150, label: '150秒' },
    { value: 180, label: '180秒' },
    { value: 210, label: '210秒' },
    { value: 240, label: '240秒' },
    { value: 270, label: '270秒' },
    { value: 300, label: '300秒' },
];

const dramaOptions: DurationOption[] = [
    { value: 15, label: '15秒' },
    { value: 30, label: '30秒' },
    { value: 60, label: '60秒' },
    { value: 180, label: '3分钟' },
    { value: 600, label: '10分钟' },
];

const durationOptions = computed(() => {
    return props.variant === 'drama' ? dramaOptions : defaultOptions;
});

const selectedLabel = computed(() => {
    const matched = durationOptions.value.find(item => item.value === props.modelValue);
    if (matched) return matched.label;
    return `${props.modelValue}秒`;
});

const handleSelect = (value: number) => {
    emit('update:modelValue', value);
};
</script>
<template>
    <el-popover trigger="click" :show-arrow="false" placement="bottom-start" width="fit-content" popper-class="model-popover">
        <template #reference>
            <slot>
                <div class="flex flex-center grid-gap-2  input-button input-button-selected px-6 ">
                    <span>每集时长</span>
                    <span class="h10 font-weight-600 text-episode-sum">{{ selectedLabel }}</span>
                </div>
            </slot>
        </template>
        <span class="h10">选择每集时长</span>
        <div class="grid-columns-4 grid-gap-4 text-center mt-4">
            <div class="grid-column-2 btn rounded-4 p-4" v-for="item in durationOptions" :key="item.value" :class="{'active': props.modelValue === item.value}"
                @click.stop="handleSelect(item.value)">
                <span class="font-weight-600">{{ item.label }}</span>
            </div>
        </div>
    </el-popover>
</template>
<style scoped lang="scss">
.btn {
    backdrop-filter: blur(10px);
    overflow: hidden;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
    border-radius: 20px;
    padding-top: 2px;
    padding-bottom: 2px;
    &:hover {
        background: rgba(255, 255, 255, 0.06);
    }
    &.active {
        background: rgba(255, 255, 255, 0.1);
    }
}

.text-episode-sum {
    height: 34px;
    line-height: 34px;
}
</style>
