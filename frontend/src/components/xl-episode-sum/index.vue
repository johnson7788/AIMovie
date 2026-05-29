<script setup lang="ts">

const props = defineProps<{
    modelValue: number;
    allowInput?: boolean;
}>();
const emit = defineEmits(['update:modelValue']);
const handleSelect = (value: number) => {
    emit('update:modelValue', value);
}
const episodeSumList = ref<number[]>([20, 40, 60, 80, 100, 150, 200, 300, 400, 500]);
const customValue = ref<number>();
const handleCustomInput = () => {
    if (customValue.value && customValue.value > 0) {
        emit('update:modelValue', customValue.value);
    }
}
</script>
<template>
    <el-popover trigger="click" :show-arrow="false" placement="bottom-start" width="fit-content" popper-class="model-popover">
        <template #reference>
            <slot>
                <div class="flex flex-center grid-gap-2 input-button input-button-selected px-6">
                    <span v-if="props.modelValue > 0">全</span>
                    <span class="h10 font-weight-600 text-episode-sum">{{ props.modelValue > 0 ? props.modelValue : '自动' }}</span>
                    <span v-if="props.modelValue > 0">集</span>
                </div>
            </slot>
        </template>
        <span class="h10">选择集数</span>
        <div class="grid-columns-4 grid-gap-4 text-center mt-4">
            <div class="grid-column-2 btn rounded-4 p-4" v-for="item in episodeSumList" :key="item"
                :class="{ 'active': props.modelValue === item }" @click.stop="handleSelect(item)">
                <span class="font-weight-600">{{ item }}</span>
            </div>
        </div>
        <div v-if="allowInput" class="custom-input-area mt-4 pt-3" style="border-top: 1px solid rgba(255,255,255,0.1);">
            <span class="h10">自定义集数</span>
            <div class="flex grid-gap-2 mt-2">
                <input
                    v-model.number="customValue"
                    type="number"
                    min="1"
                    placeholder="输入集数"
                    class="custom-episode-input"
                    @keyup.enter="handleCustomInput"
                />
                <button class="btn rounded-4 px-6" @click.stop="handleCustomInput">确定</button>
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
        background: rgba(255, 255, 255, 0.16);
    }

    &.active {
        background: rgba(255, 255, 255, 0.16);
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
    border: 1px solid rgba(255, 255, 255, 0.15);
    background: rgba(255, 255, 255, 0.06);
    color: #fff;
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;
    &:focus {
        border-color: rgba(255, 255, 255, 0.35);
    }
    &::placeholder {
        color: rgba(255, 255, 255, 0.3);
    }
}
</style>