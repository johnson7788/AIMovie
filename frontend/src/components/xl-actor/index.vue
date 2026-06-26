<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { truncate, normalizeApiList } from '@/common/functions';
import { $http } from '@/common/http';
import { useRefs, useWebConfigStore } from '@/stores';
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus';
const { t } = useI18n()
const props = withDefaults(defineProps<{
    query?: any
    types?: any[]
}>(), {
    query: () => ({}),
    types: () => ([]),
});
const webConfigStore = useWebConfigStore();
const { WEBCONFIG } = useRefs(webConfigStore);
const emit = defineEmits(['select']);
const ActorSearch = reactive({
    type: 'all',
    name: '',
    species_type: '',
    gender: '',
    age: '',
})
const actorList = ref<any[]>([]);
const loading = ref(false);
const getActorList = () => {
    loading.value = true;
    actorList.value = [];
    $http.get('/app/shortplay/api/Actor/index', {
        params: {
            ...ActorSearch,
            ...props.query,
        }
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            actorList.value = normalizeApiList(res.data);
        }
    }).finally(() => {
        loading.value = false;
    })
}
const handleActorItemClick = (item: any) => {
    emit('select', item);
}
const actorCreateRef = ref<any>(null);

// --- Pixabay search ---
const pixabayDialogVisible = ref(false);
const pixabaySearch = reactive({
    q: '',
    image_type: 'photo',
    page: 1,
});
const pixabayResults = ref<any[]>([]);
const pixabayLoading = ref(false);
const pixabayTotal = ref(0);

const searchPixabay = (loadMore = false) => {
    if (!pixabaySearch.q.trim()) return;
    if (!loadMore) {
        pixabaySearch.page = 1;
        pixabayResults.value = [];
    }
    pixabayLoading.value = true;
    $http.get('/app/shortplay/api/Pixabay/search', {
        params: {
            q: pixabaySearch.q,
            image_type: pixabaySearch.image_type,
            per_page: 20,
            page: pixabaySearch.page,
        }
    }).then((res: any) => {
        if (res.code === ResponseCode.SUCCESS) {
            const data = res.data;
            pixabayTotal.value = data.totalHits || 0;
            if (loadMore) {
                pixabayResults.value.push(...(data.hits || []));
            } else {
                pixabayResults.value = data.hits || [];
            }
        }
    }).catch(() => {
        ElMessage.error('搜索图片失败');
    }).finally(() => {
        pixabayLoading.value = false;
    });
}

const loadMorePixabay = () => {
    pixabaySearch.page += 1;
    searchPixabay(true);
}

const handlePixabaySelect = (item: any) => {
    pixabayDialogVisible.value = false;
    actorCreateRef.value?.open?.(null, props.query?.drama_id, props.query?.episode_id, item.webformat);
}

onMounted(() => {
    getActorList();
})
</script>
<template>
    <div class="flex flex-column grid-gap-4" style="--el-color-primary:var(--el-color-success);">
        <el-form class="flex flex-center grid-gap-4" @submit.prevent="getActorList">
            <el-form-item class="mb-0">
                <xl-tabs v-model="ActorSearch.type" class="text-info" @change="getActorList">
                    <xl-tabs-item value="all">{{ $t('common.all') }}</xl-tabs-item>
                    <xl-tabs-item value="public">{{ $t('common.public') }}</xl-tabs-item>
                    <xl-tabs-item value="personal">{{ $t('common.personal') }}</xl-tabs-item>
                    <xl-tabs-item v-for="item in props.types" :key="item.value" :value="item.value">
                        {{ item.label }}
                    </xl-tabs-item>
                </xl-tabs>
            </el-form-item>
            <div class="flex-1"></div>
            <el-form-item class="mb-0">
                <el-input v-model="ActorSearch.name" :placeholder="t('actor.search')" clearable @change="getActorList">
                    <template #suffix>
                        <el-icon>
                            <Search />
                        </el-icon>
                    </template>
                </el-input>
            </el-form-item>
            <el-form-item class="mb-0" style="width: 80px;">
                <el-select v-model="ActorSearch.species_type" :placeholder="t('actor.species')" clearable :teleported="false"
                    @change="getActorList">
                    <el-option v-for="item in WEBCONFIG?.enum?.actor_species_type" :key="item.value" :label="item.label"
                        :value="item.value" />
                </el-select>
            </el-form-item>
            <el-form-item class="mb-0" style="width: 80px;">
                <el-select v-model="ActorSearch.gender" :placeholder="t('actor.gender')" clearable :teleported="false"
                    @change="getActorList">
                    <el-option v-for="item in WEBCONFIG?.enum?.actor_gender" :key="item.value" :label="item.label"
                        :value="item.value" />
                </el-select>
            </el-form-item>
            <el-form-item class="mb-0" style="width: 80px;">
                <el-select v-model="ActorSearch.age" :placeholder="t('actor.age')" clearable :teleported="false"
                    @change="getActorList">
                    <el-option v-for="item in WEBCONFIG?.enum?.actor_age" :key="item.value" :label="item.label"
                        :value="item.value" />
                </el-select>
            </el-form-item>
            <el-form-item class="mb-0">
                <el-button type="primary" @click="pixabayDialogVisible = true">
                    <el-icon style="margin-right: 4px;"><PictureFilled /></el-icon>
                    搜索图片
                </el-button>
            </el-form-item>
        </el-form>
        <el-scrollbar height="300px" v-loading="loading">
            <div class="grid-columns-8 grid-gap-4">
                <div class="grid-column-2 rounded-4 p-4 border-1 border-dashed  actor-item flex flex-center grid-gap-4 "
                    @click="actorCreateRef?.open?.(null, props.query?.drama_id, props.query?.episode_id)"
                    v-if="ActorSearch.type !== 'public'">
                    <el-icon class="rounded-4" size="20"
                        style="height: 40px; width: 40px;background-color: var(--el-mask-color-extra-light);">
                        <Plus />
                    </el-icon>
                    <span>{{ $t('actor.addActor') }}</span>
                </div>
                <div class="grid-column-2 rounded-4 p-4   flex flex-center grid-gap-2 actor-item actor-item-b"
                    v-for="item in actorList" @click="handleActorItemClick(item)">
                    <el-avatar :src="item.headimg" :size="40">
                        {{ truncate(item.name, 1) }}
                    </el-avatar>
                    <div class="flex-1 flex flex-column grid-gap-2">
                        <span>{{ item.name }}</span>
                        <div class="flex grid-gap-2">
                            <span class="bg h10 rounded-2 py-1 px-2">{{ item.species_type_enum?.label }}</span>
                            <span class="bg h10 rounded-2 py-1 px-2">{{ item.gender_enum?.label }}</span>
                            <span class="bg h10 rounded-2 py-1 px-2">{{ item.age_enum?.label }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </el-scrollbar>
        <xl-actor-create ref="actorCreateRef" @success="getActorList" append-to-body />

        <!-- Pixabay Search Dialog -->
        <el-dialog v-model="pixabayDialogVisible" title="搜索图片 (Pixabay)" width="720px" append-to-body destroy-on-close>
            <div class="flex flex-column grid-gap-4">
                <div class="flex grid-gap-4">
                    <el-input v-model="pixabaySearch.q" placeholder="输入关键词搜索图片..." clearable
                        @keyup.enter="searchPixabay()" style="flex: 1;">
                        <template #suffix>
                            <el-icon class="pointer" @click="searchPixabay()"><Search /></el-icon>
                        </template>
                    </el-input>
                    <el-select v-model="pixabaySearch.image_type" style="width: 120px;" :teleported="false"
                        @change="searchPixabay()">
                        <el-option label="照片" value="photo" />
                        <el-option label="插画" value="illustration" />
                        <el-option label="矢量" value="vector" />
                        <el-option label="全部" value="all" />
                    </el-select>
                    <el-button type="primary" @click="searchPixabay()" :loading="pixabayLoading">搜索</el-button>
                </div>
                <div v-if="pixabayTotal > 0" class="text-secondary" style="font-size: 12px;">
                    找到 {{ pixabayTotal }} 张图片
                </div>
                <el-scrollbar height="400px" v-loading="pixabayLoading">
                    <div v-if="pixabayResults.length > 0" class="pixabay-grid">
                        <div v-for="item in pixabayResults" :key="item.id"
                            class="pixabay-item" @click="handlePixabaySelect(item)">
                            <el-image :src="item.preview" fit="cover" lazy class="pixabay-img" />
                            <div class="pixabay-info">
                                <span class="pixabay-author">{{ item.author }}</span>
                                <span class="pixabay-tags">{{ item.tags }}</span>
                            </div>
                        </div>
                    </div>
                    <el-empty v-else-if="!pixabayLoading" description="输入关键词开始搜索" />
                </el-scrollbar>
                <div v-if="pixabayResults.length > 0 && pixabayResults.length < pixabayTotal"
                    class="flex flex-center">
                    <el-button @click="loadMorePixabay()" :loading="pixabayLoading">加载更多</el-button>
                </div>
            </div>
        </el-dialog>
    </div>
</template>
<style lang="scss" scoped>
.actor-item {
    cursor: pointer;
    height: 80px;
    border-color: var(--el-color-info);

    &:hover {
        background-color: rgba(255, 255, 255, 0.06);
    }

    .bg {
        background-color: rgba(255, 255, 255, 0.06);
    }

    &-b {
        border: 1px solid rgba(255, 255, 255, 0.06);
    }
}

.el-input {
    --el-input-border-radius: 20px;
}

.el-select {
    --el-border-radius-base: 20px;
}

.pixabay-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}

.pixabay-item {
    cursor: pointer;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.08);
    transition: border-color 0.2s, transform 0.15s;

    &:hover {
        border-color: var(--el-color-primary);
        transform: translateY(-2px);
    }
}

.pixabay-img {
    width: 100%;
    height: 120px;
    display: block;
}

.pixabay-info {
    padding: 6px 8px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 11px;
}

.pixabay-author {
    font-weight: 500;
    color: var(--el-text-color-primary);
}

.pixabay-tags {
    color: var(--el-text-color-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>
