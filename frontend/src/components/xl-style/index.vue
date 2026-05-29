<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { truncate } from '@/common/functions';
import { $http } from '@/common/http';
import { useRefs, useWebConfigStore } from '@/stores';
const props = withDefaults(defineProps<{
    modelValue: string | number
}>(), {
    modelValue: '',
});
const webConfigStore = useWebConfigStore();
const { WEBCONFIG } = useRefs(webConfigStore);
const emit = defineEmits(['select', 'update:modelValue']);
const StyleSearch = reactive({
    classify: 'all',
    name: '',
})
const styleList = ref<any[]>([]);
const loading = ref(false);
const getStyleList = () => {
    loading.value = true;
    styleList.value = [];
    $http.get('/app/shortplay/api/Style/index', { params: StyleSearch }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            styleList.value = res.data;
        }
    }).finally(() => {
        loading.value = false;
    })
}
const handleStyleItemClick = (item: any) => {
    emit('update:modelValue', item.id);
    emit('select', item);
}
onMounted(() => {
    getStyleList();
})
</script>
<template>
    <div class="flex flex-column grid-gap-4" style="--el-color-primary:var(--el-color-success);">
        <el-form class="flex flex-center grid-gap-4" @submit.prevent="getStyleList">
            <el-form-item class="mb-0">
                <xl-tabs v-model="StyleSearch.classify" class="text-info" @change="getStyleList">
                    <xl-tabs-item value="all">全部</xl-tabs-item>
                    <xl-tabs-item v-for="value in WEBCONFIG?.enum?.style_classify" :key="value.value"
                        :value="value.value">{{ value.label }}</xl-tabs-item>
                </xl-tabs>
            </el-form-item>
            <div class="flex-1"></div>
            <el-form-item class="mb-0">
                <el-input v-model="StyleSearch.name" placeholder="搜索风格" clearable @change="getStyleList">
                    <template #suffix>
                        <el-icon>
                            <Search />
                        </el-icon>
                    </template>
                </el-input>
            </el-form-item>
        </el-form>
        <el-scrollbar height="300px" v-loading="loading">
            <div class="grid-columns-10 grid-gap-3">
                <div class="grid-column-2 input-button rounded-4 border-2 border-solid flex flex-center grid-gap-2 style-item"
                    :class="{ 'style-item-selected': props.modelValue === item.id }" v-for="item in styleList"
                    @click="handleStyleItemClick(item)">
                    <el-image :src="item.image" class="style-image" fit="cover">
                        {{ truncate(item.name, 1) }}
                    </el-image>
                    <div class="style-name">
                        <span>{{ item.name }}</span>
                    </div>
                    <el-icon size="20" color="var(--el-color-success)" class="style-item-selected-icon">
                        <SuccessFilled />
                    </el-icon>
                </div>
            </div>
        </el-scrollbar>
    </div>
</template>
<style lang="scss" scoped>
.style-item {
    cursor: pointer;
    height: 150px;
    position: relative;
    overflow: hidden;
    border-color: transparent;

    &:hover {
        border-color: var(--el-fill-color-dark);
    }

    &.style-item-selected {
        border-color: var(--el-color-success);

        &:hover {
            border-color: var(--el-color-success);
        }

        .style-item-selected-icon {
            opacity: 1;
        }
    }

    .style-image {
        width: 100%;
        height: 100%;
    }

    .style-name {
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        background: linear-gradient(180deg, rgba(0, 0, 0, 0.00) 0%, rgba(0, 0, 0, 0.50) 100%);
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 10px;
    }

    .style-item-selected-icon {
        position: absolute;
        top: 5px;
        right: 5px;
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
        background-color: var(--el-bg-color);
        border-radius: 999px;
    }
}
.el-input {
    --el-input-border-radius: 20px;
}
</style>