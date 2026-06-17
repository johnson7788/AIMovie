<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

interface DurationOption {
    value: number;
    label: string;
}

const props = defineProps<{
    modelValue: number;
}>();

const emit = defineEmits(['update:modelValue']);

const durationOptions = computed<DurationOption[]>(() => [
    { value: 5, label: `5${t('episode.second')}` },
    { value: 10, label: `10${t('episode.second')}` },
    { value: 15, label: `15${t('episode.second')}` },
    { value: 30, label: `30${t('episode.second')}` },
    { value: 60, label: `60${t('episode.second')}` },
    { value: 120, label: t('episode.minute2') },
]);

const selectedLabel = computed(() => {
    const matched = durationOptions.value.find(item => item.value === props.modelValue);
    if (matched) return matched.label;
    return `${props.modelValue}${t('episode.second')}`;
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
                    <span>{{ $t('episode.durationShort') }}</span>
                    <span class="h10 font-weight-600 text-episode-sum">{{ selectedLabel }}</span>
                </div>
            </slot>
        </template>
        <span class="h10">{{ $t('episode.selectDurationShort') }}</span>
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
