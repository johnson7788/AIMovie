<script setup lang="ts">

const props = defineProps<{
    modelValue: number;
}>();
const emit = defineEmits(['update:modelValue']);
const handleSelect = (value: number) => {
    emit('update:modelValue', value);
}
const episodeSumList = ref<number[]>([60, 90, 120, 150, 180, 210, 240, 270, 300]);
</script>
<template>
    <el-popover trigger="click" :show-arrow="false" placement="bottom-start" width="fit-content" popper-class="model-popover">
        <template #reference>
            <slot>
                <div class="flex flex-center grid-gap-2  input-button input-button-selected px-6 ">
                    <span>每集时长</span>
                    <span class="h10 font-weight-600 text-episode-sum">{{ props.modelValue }}</span>
                    <span>秒</span>
                </div>
            </slot>
        </template>
        <span class="h10">选择每集时长</span>
        <div class="grid-columns-4 grid-gap-4 text-center mt-4">
            <div class="grid-column-2 btn rounded-4 p-4" v-for="item in episodeSumList" :key="item" :class="{'active': props.modelValue === item}"
                @click.stop="handleSelect(item)">
                <span class="font-weight-600">{{ item }}秒</span>
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
        background: rgba(255,255,255,0.08);
    }
    &.active {
        background: rgba(255, 255, 255, 0.16);
    }
}

.text-episode-sum {
    height: 34px;
    line-height: 34px;
}
</style>