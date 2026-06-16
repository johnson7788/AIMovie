<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const props = defineProps<{
    modelValue: string;
}>();
const emit = defineEmits(['update:modelValue']);
const handleSelect = (resolution: string) => {
    emit('update:modelValue', resolution);
}

const resolutionList = ref([
    { value: '480p', label: '480P' },
    { value: '720p', label: '720P' },
    { value: '1080p', label: '1080P' },
]);
</script>
<template>
    <el-popover :show-arrow="false" trigger="click" placement="bottom-start" width="fit-content" popper-class="model-popover">
        <template #reference>
            <slot>
                <div class="flex flex-center grid-gap-2 input-button input-button-selected px-6">
                    <span>{{ $t('resolution.label') }}</span>
                    <span class="h10 font-weight-600 text-episode-sum">{{ props.modelValue.toUpperCase() }}</span>
                </div>
            </slot>
        </template>
        <span class="h10">{{ $t('resolution.selectLabel') }}</span>
        <div class="grid-columns-3 grid-gap-4 text-center mt-4">
            <div v-for="item in resolutionList" :key="item.value"
                class="grid-column-2 btn rounded-4 p-4"
                :class="{ 'active': props.modelValue === item.value }"
                @click.stop="handleSelect(item.value)">
                <span class="font-weight-600">{{ item.label }}</span>
            </div>
        </div>
    </el-popover>
</template>
<style scoped lang="scss">
.text-episode-sum {
    height: 34px;
    line-height: 34px;
}

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
</style>
