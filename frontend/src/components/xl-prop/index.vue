<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { truncate } from '@/common/functions';
import { $http } from '@/common/http';
const props = withDefaults(defineProps<{
    query?: any
    types?: any[]
}>(), {
    query: () => ({}),
    types: () => ([]),
});
const emit = defineEmits(['select']);
const PropSearch = reactive({
    type: 'all',
    name: '',
    ...props.query,
})
const propList = ref<any[]>([]);
const loading = ref(false);
const getPropList = () => {
    loading.value = true;
    propList.value = [];
    $http.get('/app/shortplay/api/Prop/index', { params: PropSearch }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            propList.value = res.data;
        }
    }).finally(() => {
        loading.value = false;
    })
}
const handlePropItemClick = (item: any) => {
    emit('select', item);
}
const propCreateRef = ref<any>(null);
onMounted(() => {
    getPropList();
})
</script>
<template>
    <div class="flex flex-column grid-gap-4" style="--el-color-primary:var(--el-color-success);">
        <el-form class="flex flex-center grid-gap-4" @submit.prevent="getPropList">
            <el-form-item class="mb-0">
                <xl-tabs v-model="PropSearch.type" class="text-info" @change="getPropList">
                    <xl-tabs-item value="all">全部</xl-tabs-item>
                    <xl-tabs-item value="personal">个人</xl-tabs-item>
                    <xl-tabs-item v-for="item in props.types" :key="item.value" :value="item.value">
                        {{ item.label }}
                    </xl-tabs-item>
                </xl-tabs>
            </el-form-item>
            <div class="flex-1"></div>
            <el-form-item class="mb-0">
                <el-input v-model="PropSearch.name" placeholder="搜索物品" clearable @change="getPropList">
                    <template #suffix>
                        <el-icon>
                            <Search />
                        </el-icon>
                    </template>
                </el-input>
            </el-form-item>
        </el-form>
        <el-scrollbar height="40vh" v-loading="loading">
            <div class="grid-columns-8 grid-gap-4">
                <div class="grid-column-2 rounded-4 p-4 border-2 border-dotted prop-item flex flex-center grid-gap-4 prop-item"
                    @click="propCreateRef?.open?.(null, props.query?.drama_id, props.query?.episode_id)"
                    v-if="PropSearch.type !== 'public'">
                    <el-icon class="rounded-4" size="20"
                        style="height: 40px; width: 40px;background-color: var(--el-fill-color-dark);">
                        <Plus />
                    </el-icon>
                    <span>添加物品</span>
                </div>
                <div class="grid-column-2 rounded-4 p-4 border-2 border-solid flex flex-center grid-gap-2 prop-item"
                    v-for="item in propList" @click="handlePropItemClick(item)">
                    <el-avatar :src="item.image" :size="40">
                        {{ truncate(item.name, 1) }}
                    </el-avatar>
                    <div class="flex-1 flex flex-column grid-gap-2">
                        <span>{{ item.name }}</span>
                    </div>
                </div>
            </div>
        </el-scrollbar>
        <xl-prop-create ref="propCreateRef" @success="getPropList" />
    </div>
</template>
<style lang="scss" scoped>
.prop-item {
    cursor: pointer;
    height: 80px;

    &:hover {
        background-color: var(--el-fill-color-dark);
    }
}
</style>