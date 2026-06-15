<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { $http } from '@/common/http';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
const props = withDefaults(defineProps<{
    query?: any
    types?: any[]
}>(), {
    query: () => ({}),
    types: () => ([]),
});
const emit = defineEmits(['select']);
const StoryboardSearch = reactive({
    type: 'episode',
    description: '',
    ...props.query,
})
const storyboardList = ref<any[]>([]);
const loading = ref(false);
const getStoryboardList = () => {
    loading.value = true;
    storyboardList.value = [];
    $http.get('/app/shortplay/api/Storyboard/index', { params: StoryboardSearch }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            storyboardList.value = res.data;
        }
    }).finally(() => {
        loading.value = false;
    })
}
const handleStoryboardItemClick = (item: any) => {
    if (!item.image) return ElMessage.info(t('storyboard.noImage'));
    emit('select', item);
}
defineExpose({
    getStoryboardList,
})
</script>
<template>
    <div class="flex flex-column grid-gap-4" style="--el-color-primary:var(--el-color-success);">
        <el-form class="flex flex-center grid-gap-4" @submit.prevent="getStoryboardList">
            <el-form-item class="mb-0">
                <xl-tabs v-model="StoryboardSearch.type" class="text-info" @change="getStoryboardList">
                    <xl-tabs-item value="episode">{{ $t('storyboard.thisEpisode') }}</xl-tabs-item>
                    <xl-tabs-item value="all">{{ $t('common.all') }}</xl-tabs-item>
                </xl-tabs>
            </el-form-item>
            <div class="flex-1"></div>
            <el-form-item class="mb-0">
                <el-input v-model="StoryboardSearch.description" :placeholder="t('storyboard.search')" clearable
                    @change="getStoryboardList">
                    <template #suffix>
                        <el-icon>
                            <Search />
                        </el-icon>
                    </template>
                </el-input>
            </el-form-item>
        </el-form>
        <el-scrollbar height="40vh" v-loading="loading" v-if="storyboardList.length > 0 || loading">
            <div class="grid-columns-8 grid-gap-4">
                <div class="grid-column-2 rounded-4 border-2 border-solid flex flex-column grid-gap-2 storyboard-item"
                    v-for="item in storyboardList" @click="handleStoryboardItemClick(item)">
                    <div class="p-2">
                        <span class="h10">场景{{ item.scene_id }} - #{{ item.sort }}</span>
                    </div>
                    <el-avatar :src="item.image" :size="40" shape="square" fit="contain"
                        class="storyboard-item-image bg-mosaic" />
                </div>
            </div>
        </el-scrollbar>
        <el-empty v-else :description="$t('storyboard.noStoryboard')"></el-empty>
    </div>
</template>
<style lang="scss" scoped>
.storyboard-item {
    cursor: pointer;

    &:hover {
        background-color: var(--el-fill-color-dark);
    }

    &-image {
        width: 100%;
        height: 200px;
    }
}
</style>