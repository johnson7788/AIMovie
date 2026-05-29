<script setup lang="ts">
import { truncate } from '@/common/functions';
import { useModelStore } from '@/stores';
const modelStore = useModelStore();
const props = withDefaults(defineProps<{
    modelValue?: string | number
    scene: keyof ModelInterface
    noInit?: boolean
    scrollProps?: any
    title?: string
}>(), {
    modelValue: '',
    title: '选择模型',
    noInit: false,
    scrollProps: {
        height: '30vh',
    },
});
const emit = defineEmits(['select', 'update:modelValue']);
const ModelsSearch = reactive({
    classify: 'all',
    name: '',
})
const MODELS = ref<ModelInterface[keyof ModelInterface]>([]);
const getModelsList = () => {
    MODELS.value = modelStore.get(props.scene);
    if (!props.noInit && MODELS.value.length) {
        handleModelsItemClick(MODELS.value[0]);
    }
}

const handleModelsItemClick = (item: any) => {
    emit('update:modelValue', item.id);
    emit('select', item);
}
onMounted(() => {
    getModelsList();
})
</script>
<template>
    <div class="flex flex-column grid-gap-4" style="--el-color-primary:var(--el-color-success);">
        <el-form class="flex flex-center grid-gap-4" @submit.prevent="() => { }">
            <span>{{ props.title }}</span>
            <div class="flex-1"></div>
            <el-form-item class="mb-0">
                <el-input v-model="ModelsSearch.name" placeholder="搜索模型" clearable>
                    <template #suffix>
                        <el-icon>
                            <Search />
                        </el-icon>
                    </template>
                </el-input>
            </el-form-item>
        </el-form>
        <el-scrollbar v-bind="scrollProps">
            <div class="flex flex-column grid-gap-4">
                <div class="flex input-button rounded-4  grid-gap-2 model-item"
                    :class="{ 'model-item-selected model-item-active': props.modelValue === item.id }"
                    v-for="item in MODELS.filter((item: any) => item.name.includes(ModelsSearch.name))"
                    @click="handleModelsItemClick(item)">
                    <el-image :src="item.icon" class="model-image rounded-4">
                        {{ truncate(item.name, 1) }}
                    </el-image>
                    <div class="flex-1 flex flex-column flex-y-flex-start grid-gap-2">
                        <span class="font-weight-600">{{ item.name }}</span>
                        <span class="text-secondary h10 text-ellipsis-3">{{ item.description }}</span>
                    </div>
                    <el-icon size="16" color="var(--el-color-white)" class="model-item-selected-icon">
                        <Select />
                    </el-icon>
                </div>
            </div>
        </el-scrollbar>
    </div>
</template>
<style lang="scss" scoped>
.model-item {
    cursor: pointer;
    position: relative;
    overflow: hidden;
    background: rgba(0, 0, 0, 0.2);
    padding: 10px;
    line-height: normal;

    &:hover {
        background: rgba(0, 0, 0, 0.1);
    }

    &-active {
        background: rgba(255, 255, 255, 0.1);
    }

    &.model-item-selected {
        .model-item-selected-icon {
            opacity: 1;
        }
    }

    .model-image {
        width: 60px;
        height: 60px;
    }

    .model-item-selected-icon {
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
        // background-color: var(--el-bg-color);
        // border-radius: 999px;
        justify-self: center;
        align-self: center;
    }
}
</style>