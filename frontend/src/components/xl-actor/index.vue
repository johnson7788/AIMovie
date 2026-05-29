<script setup lang="ts">
import { ResponseCode } from '@/common/const';
import { truncate } from '@/common/functions';
import { $http } from '@/common/http';
import { useRefs, useWebConfigStore } from '@/stores';
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
            actorList.value = res.data;
        }
    }).finally(() => {
        loading.value = false;
    })
}
const handleActorItemClick = (item: any) => {
    emit('select', item);
}
const actorCreateRef = ref<any>(null);
onMounted(() => {
    getActorList();
})
</script>
<template>
    <div class="flex flex-column grid-gap-4" style="--el-color-primary:var(--el-color-success);">
        <el-form class="flex flex-center grid-gap-4" @submit.prevent="getActorList">
            <el-form-item class="mb-0">
                <xl-tabs v-model="ActorSearch.type" class="text-info" @change="getActorList">
                    <xl-tabs-item value="all">全部</xl-tabs-item>
                    <xl-tabs-item value="public">公共</xl-tabs-item>
                    <xl-tabs-item value="personal">个人</xl-tabs-item>
                    <xl-tabs-item v-for="item in props.types" :key="item.value" :value="item.value">
                        {{ item.label }}
                    </xl-tabs-item>
                </xl-tabs>
            </el-form-item>
            <div class="flex-1"></div>
            <el-form-item class="mb-0">
                <el-input v-model="ActorSearch.name" placeholder="搜索演员" clearable @change="getActorList">
                    <template #suffix>
                        <el-icon>
                            <Search />
                        </el-icon>
                    </template>
                </el-input>
            </el-form-item>
            <el-form-item class="mb-0" style="width: 80px;">
                <el-select v-model="ActorSearch.species_type" placeholder="物种" clearable :teleported="false"
                    @change="getActorList">
                    <el-option v-for="item in WEBCONFIG?.enum?.actor_species_type" :key="item.value" :label="item.label"
                        :value="item.value" />
                </el-select>
            </el-form-item>
            <el-form-item class="mb-0" style="width: 80px;">
                <el-select v-model="ActorSearch.gender" placeholder="性别" clearable :teleported="false"
                    @change="getActorList">
                    <el-option v-for="item in WEBCONFIG?.enum?.actor_gender" :key="item.value" :label="item.label"
                        :value="item.value" />
                </el-select>
            </el-form-item>
            <el-form-item class="mb-0" style="width: 80px;">
                <el-select v-model="ActorSearch.age" placeholder="年龄" clearable :teleported="false"
                    @change="getActorList">
                    <el-option v-for="item in WEBCONFIG?.enum?.actor_age" :key="item.value" :label="item.label"
                        :value="item.value" />
                </el-select>
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
                    <span>添加演员</span>
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
    </div>
</template>
<style lang="scss" scoped>
.actor-item {
    cursor: pointer;
    height: 80px;
    border-color: var(--el-color-info);

    &:hover {
        background-color: rgba(255, 255, 255, 0.08);
    }

    .bg {
        background-color: rgba(255, 255, 255, 0.1);
    }

    &-b {
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
}

.el-input {
    --el-input-border-radius: 20px;
}

.el-select {
    --el-border-radius-base: 20px;
}
</style>