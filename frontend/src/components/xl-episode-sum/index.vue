<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

interface EpisodeOption {
    value: number;
    label: string;
}

const props = withDefaults(defineProps<{
    modelValue: number;
    allowInput?: boolean;
    variant?: 'default' | 'drama';
}>(), {
    variant: 'default',
});

const emit = defineEmits(['update:modelValue']);

const defaultEpisodeValues = [20, 40, 60, 80, 100, 150, 200, 300, 400, 500];
const dramaEpisodeValues = [1, 5, ...defaultEpisodeValues];

const episodeOptions = computed<EpisodeOption[]>(() => {
    const values = props.variant === 'drama'
        ? dramaEpisodeValues
        : defaultEpisodeValues;
    return values.map(value => ({
        value,
        label: String(value),
    }));
});

const displayLabel = computed(() => {
    if (props.modelValue <= 0) return t('episode.auto');
    return String(props.modelValue);
});

const handleSelect = (value: number) => {
    emit('update:modelValue', value);
};

const customValue = ref<number>();
const handleCustomInput = () => {
    if (customValue.value && customValue.value > 0) {
        emit('update:modelValue', customValue.value);
    }
};
</script>
<template>
    <el-popover trigger="click" :show-arrow="false" placement="bottom-start" width="fit-content" popper-class="model-popover">
        <template #reference>
            <slot>
                <div class="flex flex-center grid-gap-2 input-button input-button-selected px-6">
                    <span v-if="props.modelValue > 0">{{ $t('episode.all') }}</span>
                    <span class="h10 font-weight-600 text-episode-sum">{{ displayLabel }}</span>
                    <span v-if="props.modelValue > 0">{{ $t('episode.unit') }}</span>
                </div>
            </slot>
        </template>
        <span class="h10">{{ $t('episode.selectSum') }}</span>
        <div class="grid-columns-4 grid-gap-4 text-center mt-4">
            <div class="grid-column-2 btn rounded-4 p-4" v-for="item in episodeOptions" :key="item.value"
                :class="{ 'active': props.modelValue === item.value }" @click.stop="handleSelect(item.value)">
                <span class="font-weight-600">{{ item.label }}</span>
            </div>
        </div>
        <div v-if="allowInput" class="custom-input-area mt-4 pt-3" style="border-top: 1px solid rgba(255, 255, 255, 0.06);">
            <span class="h10">{{ $t('episode.customSum') }}</span>
            <div class="flex grid-gap-2 mt-2">
                <input
                    v-model.number="customValue"
                    type="number"
                    min="1"
                    :placeholder="t('episode.inputSum')"
                    class="custom-episode-input"
                    @keyup.enter="handleCustomInput"
                />
                <button class="btn rounded-4 px-6" @click.stop="handleCustomInput">{{ $t('common.confirm') }}</button>
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
        background: rgba(255, 255, 255, 0.1);
    }

    &.active {
        background: rgba(255, 255, 255, 0.1);
    }
}

.text-episode-sum {
    height: 34px;
    line-height: 34px;
}

.custom-input-area {
    padding: 0 4px;
}

.custom-episode-input {
    width: 100%;
    padding: 6px 10px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.04);
    color: #fff;
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;
    &:focus {
        border-color: rgba(255, 255, 255, 0.18);
    }
    &::placeholder {
        color: rgba(255, 255, 255, 0.15);
    }
}
</style>
