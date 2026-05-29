<script setup lang="ts">
import { $http } from '@/common/http';
import { ResponseCode } from '@/common/const';
const props = defineProps<{
    modelValue: string;
}>();
const emit = defineEmits(['update:modelValue']);
const handleSelect = (aspectRatio: string) => {
    emit('update:modelValue', aspectRatio);
}
const showArrowDown = ref(false);

const modelList = ref<string[]>(['9:16', '16:9', '3:4', '4:3', '2:3', '3:2', '1:1']);

onMounted(() => {
    $http.get('/app/model/api/Voice/modelList').then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            modelList.value = res.data;
        }
    });
});
</script>
<template>
    <el-popover :show-arrow="false" trigger="click" placement="bottom-start" width="fit-content"
        popper-class="model-popover" @show="showArrowDown = false" @hide="showArrowDown = true">
        <template #reference>
            <slot>
                <div class="flex flex-center grid-gap-2 input-button input-button-selected   px-6">
                    <span class="icon-aspect-ratio" :view="props.modelValue"></span>
                    <span class="h10">{{ props.modelValue }}</span>
                    <el-icon v-if="showArrowDown">
                        <ArrowUpBold />
                    </el-icon>
                    <el-icon v-else>
                        <ArrowDownBold />
                    </el-icon>
                </div>
            </slot>
        </template>
        <!-- <span class="h10">选择比例</span> -->
        <el-scrollbar height="300px">
            <div class="grid-columns-2 grid-gap-4 text-center mt-4">
                <div v-for="item in modelList" :key="item"
                    class="grid-column-2 grid-gap-2 input-button rounded-4 p-2"
                    :class="{ 'input-button-selected': props.modelValue === item }" @click.stop="handleSelect(item)">
                    <span class="icon-aspect-ratio" :view="item"></span>
                    <span class="font-weight-600">{{ item }}</span>
                    <el-icon v-if="props.modelValue === item" class="ml-auto">
                        <Check />
                    </el-icon>
                </div>
            </div>
        </el-scrollbar>
    </el-popover>
</template>
<style scoped lang="scss">
</style>